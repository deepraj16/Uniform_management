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
os.makedirs("static/reference_images", exist_ok=True)
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

API_KEY = "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"

llm = ChatOpenAI(
    model="google/gemini-2.5-flash-image",
    temperature=0.1,
    max_tokens=200,
    base_url="https://openrouter.ai/api/v1",
    api_key=API_KEY
)

# User reference images mapping (username -> image filename in static/reference_images/)
USER_REFERENCE_IMAGES = {
    "shivraj26": "shiva.jpg",
    "shivani26": "shivani.jpg",
    "abhishek26": "adi.jpg",
    "deep26": "me.jpg"
}

# Session storage
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
            face_verified BOOLEAN,
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
        
        query = "SELECT id, student_name, username FROM students WHERE username=%s AND password=%s"
        cursor.execute(query, (username, password))
        result = cursor.fetchone()
        
        if result:
            return {"id": result[0], "name": result[1], "username": result[2]}
        return None
        
    except Exception as e:
        print(f"Login error: {e}")
        return None
    finally:
        cursor.close()
        connection.close()


def verify_face_with_llm(current_image_path: str, reference_image_path: str):
    """Verify if the two faces are the same person using LLM"""
    try:
        # Read both images
        with open(current_image_path, "rb") as f:
            current_img_b64 = base64.b64encode(f.read()).decode()
        
        with open(reference_image_path, "rb") as f:
            reference_img_b64 = base64.b64encode(f.read()).decode()
        
        prompt = """Compare these two images and determine if they show the same person.
Look at facial features, structure, and characteristics.
Respond ONLY in JSON format:
{"same_person": true/false, "confidence": "high/medium/low"}"""

        response = llm.invoke([
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{reference_img_b64}",
                            "detail": "high"
                        }
                    },
                    {"type": "text", "text": "Reference image above. Current image below:"},
                    {
                        "type": "image_url",
                        "image_url": {
                            "url": f"data:image/jpeg;base64,{current_img_b64}",
                            "detail": "high"
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
            return {"same_person": False, "confidence": "low", "error": "Could not parse response"}
            
    except Exception as e:
        print(f"Error verifying face: {e}")
        return {"same_person": False, "confidence": "low", "error": str(e)}


def check_uniform_with_llm(image_path: str):
    """Check uniform using LLM - includes beard detection"""
    try:
        with open(image_path, "rb") as f:
            image_b64 = base64.b64encode(f.read()).decode()
        
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


def save_uniform_check(student_id: int, student_name: str, results: dict, image_path: str, face_verified: bool):
    """Save uniform check results to database"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        query = """
        INSERT INTO uniform_checks 
        (student_id, student_name, check_time, black_blazer_or_suit, tie, 
         white_shirt, id_card, overall_compliance, image_path, face_verified)
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
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
            image_path,
            face_verified
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
    """Process uniform check with face verification"""
    if session not in active_sessions:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    user = active_sessions[session]
    username = user.get('username')
    
    # Save uploaded image
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"uniform_{user['id']}_{timestamp}.jpg"
    filepath = f"static/uploads/{filename}"
    
    with open(filepath, "wb") as buffer:
        shutil.copyfileobj(image.file, buffer)
    
    face_verified = False
    face_verification_result = None
    
    # Check if user has a reference image for face verification
    if username in USER_REFERENCE_IMAGES:
        reference_image = USER_REFERENCE_IMAGES[username]
        reference_path = f"static/reference_images/{reference_image}"
        
        # Check if reference image exists
        if os.path.exists(reference_path):
            print(f"Performing face verification for {username}")
            face_verification_result = verify_face_with_llm(filepath, reference_path)
            face_verified = face_verification_result.get("same_person", False)
            
            # If face verification fails, return error
            if not face_verified:
                return JSONResponse({
                    "success": False,
                    "error": "Face verification failed",
                    "message": "The person in the image does not match the registered user",
                    "face_verification": face_verification_result,
                    "image_url": f"/static/uploads/{filename}"
                })
        else:
            print(f"Reference image not found for {username} at {reference_path}")
            # User has entry but image missing - treat as no verification needed
            face_verified = True
    else:
        # User not in dict - skip face verification, proceed with uniform check
        print(f"No face verification required for {username}")
        face_verified = True
    
    # Check uniform with LLM (includes beard detection)
    results = check_uniform_with_llm(filepath)
    
    # Save to database with face verification status
    save_uniform_check(user['id'], user['name'], results, filepath, face_verified)
    
    # Return results including face verification info
    return JSONResponse({
        "success": True,
        "face_verified": face_verified,
        "face_verification_result": face_verification_result,
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