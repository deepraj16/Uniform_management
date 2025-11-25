from fastapi import FastAPI, Request, Form, UploadFile, File, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pymysql
import base64
from langchain_openai import ChatOpenAI
import json
from datetime import datetime
import os
import shutil
from pathlib import Path

app = FastAPI()

# Create necessary directories
os.makedirs("static/uploads", exist_ok=True)
os.makedirs("templates", exist_ok=True)

templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "1234",
    "database": "attendance"
}


# llm = ChatOpenAI(
#     model="qwen/qwen2.5-vl-32b-instruct:free",
#     temperature=0.1,
#     max_tokens=200,
#     base_url="https://openrouter.ai/api/v1",
#     api_key=API_KEY
# )

API_KEY = "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"

llm = ChatOpenAI(
    model="google/gemini-2.5-flash-image",  # Very reliable free option
    temperature=0.1,
    max_tokens=200,
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY
)

# Session storage (in production, use proper session management)
active_sessions = {}


def get_db_connection():
    """Create database connection"""
    return pymysql.connect(**DB_CONFIG)


def create_uniform_table():
    """Create uniform_checks table if not exists"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        query = """
        CREATE TABLE IF NOT EXISTS uniform_checks (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT,
            student_name VARCHAR(255),
            check_time DATETIME,
            black_blazer_or_suit BOOLEAN,
            tie BOOLEAN,
            white_shirt BOOLEAN,
            id_card BOOLEAN,
            overall_compliance BOOLEAN,
            image_path VARCHAR(500),
            FOREIGN KEY (student_id) REFERENCES students(id)
        )
        """
        
        cursor.execute(query)
        connection.commit()
        print("Table created successfully!")
        
    except Exception as e:
        print(f"Error creating table: {e}")
    finally:
        cursor.close()
        connection.close()


def verify_login(username: str, password: str):
    """Verify user credentials"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        query = "SELECT id, student_name FROM students WHERE username=%s AND password=%s"
        cursor.execute(query, (username, password))
        result = cursor.fetchone()
        
        if result:
            return {"id": result[0], "name": result[1]}
        return None
        
    except Exception as e:
        print(f"Login error: {e}")
        return None
    finally:
        cursor.close()
        connection.close()


def check_uniform_with_llm(image_path: str):
    """Check uniform using LLM - now includes beard detection"""
    try:
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode()
        
        # Updated prompt to include beard detection
        prompt = """Check if wearing: blazer or suit, tie, white shirt, ID card. Also check if person has a beard.
Respond ONLY in JSON:
{"black_blazer_or_suit": {"present": true/false}, "tie": {"present": true/false}, "white_shirt": {"present": true/false}, "id_card": {"present": true/false}, "beard": {"present": true/false}, "overall_compliance": true/false}"""

        response = llm.invoke([
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{image_b64}"
                        }
                    }
                ]
            }
        ])
        
        # Parse JSON response
        response_text = response.content
        start_idx = response_text.find('{')
        end_idx = response_text.rfind('}') + 1
        
        if start_idx != -1 and end_idx > start_idx:
            json_str = response_text[start_idx:end_idx]
            result = json.loads(json_str)
            return result
        else:
            return {"error": "Could not parse response"}
            
    except Exception as e:
        print(f"Error checking uniform: {e}")
        return {"error": str(e)}


def save_uniform_check(student_id: int, student_name: str, results: dict, image_path: str):
    """Save uniform check results to database (beard not included)"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        query = """
        INSERT INTO uniform_checks 
        (student_id, student_name, check_time, black_blazer_or_suit, tie, 
         white_shirt, id_card, overall_compliance, image_path)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
        """
        
        values = (
            student_id,
            student_name,
            datetime.now(),
            results.get("black_blazer_or_suit", {}).get("present", False),
            results.get("tie", {}).get("present", False),
            results.get("white_shirt", {}).get("present", False),
            results.get("id_card", {}).get("present", False),
            results.get("overall_compliance", False),
            image_path
        )
        
        cursor.execute(query, values)
        connection.commit()
        return True
        
    except Exception as e:
        print(f"Error saving check: {e}")
        return False
    finally:
        cursor.close()
        connection.close()


@app.on_event("startup")
async def startup_event():
    """Initialize database table on startup"""
    create_uniform_table()


@app.get("/", response_class=HTMLResponse)
async def login_page(request: Request):
    """Display login page"""
    return templates.TemplateResponse("login.html", {"request": request})


@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    """Handle login"""
    user = verify_login(username, password)
    
    if user:
        session_id = f"{user['id']}_{datetime.now().timestamp()}"
        active_sessions[session_id] = user
        
        response = RedirectResponse(url=f"/dashboard?session={session_id}", status_code=303)
        return response
    else:
        return HTMLResponse("""
            <html>
                <body>
                    <h2>Login Failed!</h2>
                    <p>Invalid username or password</p>
                    <a href="/">Try Again</a>
                </body>
            </html>
        """)


@app.get("/dashboard", response_class=HTMLResponse)
async def dashboard(request: Request, session: str):
    """Display dashboard with camera"""
    if session not in active_sessions:
        return RedirectResponse(url="/")
    
    user = active_sessions[session]
    return templates.TemplateResponse("dashboard.html", {
        "request": request,
        "user": user,
        "session": session
    })


@app.post("/check-uniform")
async def check_uniform(
    session: str = Form(...),
    image: UploadFile = File(...)
):
    """Process uniform check"""
    if session not in active_sessions:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user = active_sessions[session]
    
    # Save uploaded image
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"uniform_{user['id']}_{timestamp}.jpg"
    filepath = f"static/uploads/{filename}"
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
    
    # Check uniform with LLM (includes beard detection)
    results = check_uniform_with_llm(filepath)
    
    # Save to database (beard not saved)
    save_uniform_check(user['id'], user['name'], results, filepath)
    
    # Return results including beard detection for UI display
    return JSONResponse({
        "success": True,
        "results": results,
        "image_url": f"/static/uploads/{filename}"
    })


@app.get("/logout")
async def logout(session: str):
    """Logout user"""
    if session in active_sessions:
        del active_sessions[session]
    return RedirectResponse(url="/")


# Run with: uvicorn main:app --reload