from fastapi import FastAPI, Request, Form, Cookie
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
import pymysql
from typing import Optional

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# Hardcoded login credentials
TEACHER_USERNAME = "teach26"
TEACHER_PASSWORD = "teach@123"

# FreeDB Configuration (Correct & Working)
DB_CONFIG = {
    'host': 'sql.freedb.tech',
    'user': 'freedb_deepraj16',
    'password': 'E9Bmn%$f7S*tkyq',
    'database': 'freedb_student_grades',
    'port': 3306,
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# Connect to DB
def get_db():
    return pymysql.connect(**DB_CONFIG)

# FIXED init_db() for FreeDB (DO NOT CREATE DATABASE)
def init_db():
    """Create tables only (FreeDB does NOT allow creating databases)."""
    conn = pymysql.connect(**DB_CONFIG)
    cursor = conn.cursor()

    # Create students table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS students (
            id INT AUTO_INCREMENT PRIMARY KEY,
            name VARCHAR(100) NOT NULL,
            roll_number VARCHAR(50) UNIQUE NOT NULL,
            class VARCHAR(50) NOT NULL
        )
    """)

    # Create grades table
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS grades (
            id INT AUTO_INCREMENT PRIMARY KEY,
            student_id INT,
            subject VARCHAR(100) NOT NULL,
            marks INT NOT NULL,
            FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE
        )
    """)

    conn.commit()
    cursor.close()
    conn.close()


def calculate_grade(average):
    if average >= 90:
        return 'A+'
    elif average >= 80:
        return 'A'
    elif average >= 70:
        return 'B'
    elif average >= 60:
        return 'C'
    elif average >= 50:
        return 'D'
    else:
        return 'F'

@app.on_event("startup")
async def startup():
    init_db()

def check_auth(session_token: Optional[str] = None):
    return session_token == "authenticated"


@app.get("/", response_class=HTMLResponse)
async def home(request: Request, session: Optional[str] = Cookie(None)):
    if not check_auth(session):
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, error: Optional[str] = None):
    return templates.TemplateResponse("login.html", {
        "request": request,
        "error": error
    })


@app.post("/login")
async def login(username: str = Form(...), password: str = Form(...)):
    if username == TEACHER_USERNAME and password == TEACHER_PASSWORD:
        response = RedirectResponse(url="/", status_code=303)
        response.set_cookie(key="session", value="authenticated", httponly=True)
        return response
    else:
        return RedirectResponse(url="/login?error=invalid", status_code=303)


@app.get("/logout")
async def logout():
    response = RedirectResponse(url="/login", status_code=303)
    response.delete_cookie(key="session")
    return response


@app.get("/add-student", response_class=HTMLResponse)
async def add_student_form(request: Request, session: Optional[str] = Cookie(None)):
    if not check_auth(session):
        return RedirectResponse(url="/login", status_code=303)
    return templates.TemplateResponse("add_student.html", {"request": request})


@app.post("/add-student")
async def add_student(
    session: Optional[str] = Cookie(None),
    name: str = Form(...),
    roll_number: str = Form(...),
    class_name: str = Form(...)
):
    if not check_auth(session):
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db()
    cursor = conn.cursor()

    try:
        cursor.execute(
            "INSERT INTO students (name, roll_number, class) VALUES (%s, %s, %s)",
            (name, roll_number, class_name)
        )
        conn.commit()
    except pymysql.IntegrityError:
        return RedirectResponse(url="/add-student?error=duplicate", status_code=303)
    finally:
        cursor.close()
        conn.close()

    return RedirectResponse(url="/", status_code=303)


@app.get("/add-grades", response_class=HTMLResponse)
async def add_grades_form(request: Request, session: Optional[str] = Cookie(None)):
    if not check_auth(session):
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM students ORDER BY name")
    students = cursor.fetchall()
    cursor.close()
    conn.close()

    return templates.TemplateResponse("add_grades.html", {
        "request": request,
        "students": students
    })


@app.post("/add-grades")
async def add_grades(
    session: Optional[str] = Cookie(None),
    student_id: int = Form(...),
    subject: str = Form(...),
    marks: int = Form(...)
):
    if not check_auth(session):
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute(
        "INSERT INTO grades (student_id, subject, marks) VALUES (%s, %s, %s)",
        (student_id, subject, marks)
    )
    conn.commit()
    cursor.close()
    conn.close()

    return RedirectResponse(url="/add-grades", status_code=303)


@app.get("/view-reports", response_class=HTMLResponse)
async def view_reports(request: Request, session: Optional[str] = Cookie(None)):
    if not check_auth(session):
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT s.id, s.name, s.roll_number, s.class,
               COUNT(g.id) as subject_count,
               COALESCE(SUM(g.marks), 0) as total_marks,
               COALESCE(AVG(g.marks), 0) as average_marks
        FROM students s
        LEFT JOIN grades g ON s.id = g.student_id
        GROUP BY s.id, s.name, s.roll_number, s.class
        ORDER BY s.name
    """)

    students = cursor.fetchall()

    for student in students:
        student['grade'] = calculate_grade(student['average_marks'])
        student['average_marks'] = round(student['average_marks'], 2)

    cursor.close()
    conn.close()

    return templates.TemplateResponse("view_reports.html", {
        "request": request,
        "students": students
    })


@app.get("/student/{student_id}", response_class=HTMLResponse)
async def student_details(request: Request, student_id: int, session: Optional[str] = Cookie(None)):
    if not check_auth(session):
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db()
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM students WHERE id = %s", (student_id,))
    student = cursor.fetchone()

    cursor.execute(
        "SELECT * FROM grades WHERE student_id = %s ORDER BY subject",
        (student_id,)
    )
    grades = cursor.fetchall()

    if grades:
        total = sum(g['marks'] for g in grades)
        average = total / len(grades)
        grade = calculate_grade(average)
    else:
        total = 0
        average = 0
        grade = 'N/A'

    cursor.close()
    conn.close()

    return templates.TemplateResponse("student_details.html", {
        "request": request,
        "student": student,
        "grades": grades,
        "total": total,
        "average": round(average, 2),
        "grade": grade
    })


@app.get("/delete-student/{student_id}")
async def delete_student(student_id: int, session: Optional[str] = Cookie(None)):
    if not check_auth(session):
        return RedirectResponse(url="/login", status_code=303)

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM students WHERE id = %s", (student_id,))
    conn.commit()
    cursor.close()
    conn.close()

    return RedirectResponse(url="/view-reports", status_code=303)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
