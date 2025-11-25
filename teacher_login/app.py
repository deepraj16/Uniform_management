from fastapi import FastAPI, Request, Form, HTTPException
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
import pymysql
from datetime import datetime, date, timedelta
import os
from collections import defaultdict

app = FastAPI()

# Create necessary directories
os.makedirs("teacher_templates", exist_ok=True)
os.makedirs("static", exist_ok=True)

templates = Jinja2Templates(directory="teacher_templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# Database configuration
DB_CONFIG = {
    "host": "localhost",
    "user": "root",
    "password": "1234",
    "database": "attendance"
}

# Teacher credentials (hardcoded - not in database)
TEACHER_USERNAME = "teach26"
TEACHER_PASSWORD = "teach@123"

# Session storage
teacher_sessions = {}


def get_db_connection():
    """Create database connection"""
    return pymysql.connect(**DB_CONFIG)


def get_all_students():
    """Get all students from database"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        query = "SELECT id, student_name, username FROM students ORDER BY student_name"
        cursor.execute(query)
        students = cursor.fetchall()
        
        return [{"id": s[0], "name": s[1], "username": s[2]} for s in students]
        
    except Exception as e:
        print(f"Error fetching students: {e}")
        return []
    finally:
        cursor.close()
        connection.close()


def get_uniform_checks_today():
    """Get today's uniform checks"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        today = date.today()
        query = """
            SELECT 
                uc.student_id,
                uc.student_name,
                uc.check_time,
                uc.black_blazer_or_suit,
                uc.tie,
                uc.white_shirt,
                uc.id_card,
                uc.overall_compliance,
                uc.image_path
            FROM uniform_checks uc
            WHERE DATE(uc.check_time) = %s
            ORDER BY uc.check_time DESC
        """
        
        cursor.execute(query, (today,))
        checks = cursor.fetchall()
        
        results = []
        for check in checks:
            results.append({
                "student_id": check[0],
                "student_name": check[1],
                "check_time": check[2].strftime("%I:%M %p"),
                "black_blazer_or_suit": check[3],
                "tie": check[4],
                "white_shirt": check[5],
                "id_card": check[6],
                "overall_compliance": check[7],
                "image_path": check[8]
            })
        
        return results
        
    except Exception as e:
        print(f"Error fetching checks: {e}")
        return []
    finally:
        cursor.close()
        connection.close()


def get_statistics():
    """Get uniform compliance statistics"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        today = date.today()
        
        # Today's stats
        query_today = """
            SELECT 
                COUNT(*) as total_checks,
                SUM(overall_compliance) as compliant,
                COUNT(*) - SUM(overall_compliance) as non_compliant
            FROM uniform_checks
            WHERE DATE(check_time) = %s
        """
        cursor.execute(query_today, (today,))
        today_stats = cursor.fetchone()
        
        # Present students (who checked in today)
        query_present = """
            SELECT COUNT(DISTINCT student_id) 
            FROM uniform_checks 
            WHERE DATE(check_time) = %s
        """
        cursor.execute(query_present, (today,))
        present_count = cursor.fetchone()[0]
        
        # Total students
        cursor.execute("SELECT COUNT(*) FROM students")
        total_students = cursor.fetchone()[0]
        
        return {
            "total_students": total_students,
            "present_today": present_count,
            "absent_today": total_students - present_count,
            "total_checks": today_stats[0] or 0,
            "compliant": today_stats[1] or 0,
            "non_compliant": today_stats[2] or 0
        }
        
    except Exception as e:
        print(f"Error fetching statistics: {e}")
        return {
            "total_students": 0,
            "present_today": 0,
            "absent_today": 0,
            "total_checks": 0,
            "compliant": 0,
            "non_compliant": 0
        }
    finally:
        cursor.close()
        connection.close()


def get_student_history(student_id: int):
    """Get uniform check history for a specific student"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        query = """
            SELECT 
                check_time,
                black_blazer_or_suit,
                tie,
                white_shirt,
                id_card,
                overall_compliance,
                image_path
            FROM uniform_checks
            WHERE student_id = %s
            ORDER BY check_time DESC
            LIMIT 10
        """
        
        cursor.execute(query, (student_id,))
        checks = cursor.fetchall()
        
        results = []
        for check in checks:
            results.append({
                "check_time": check[0].strftime("%Y-%m-%d %I:%M %p"),
                "black_blazer_or_suit": check[1],
                "tie": check[2],
                "white_shirt": check[3],
                "id_card": check[4],
                "overall_compliance": check[5],
                "image_path": check[6]
            })
        
        return results
        
    except Exception as e:
        print(f"Error fetching student history: {e}")
        return []
    finally:
        cursor.close()
        connection.close()


def get_weekly_report():
    """Get weekly compliance report"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        # Last 7 days
        end_date = date.today()
        start_date = end_date - timedelta(days=6)
        
        query = """
            SELECT 
                DATE(check_time) as date,
                COUNT(*) as total_checks,
                SUM(overall_compliance) as compliant
            FROM uniform_checks
            WHERE DATE(check_time) BETWEEN %s AND %s
            GROUP BY DATE(check_time)
            ORDER BY date
        """
        
        cursor.execute(query, (start_date, end_date))
        data = cursor.fetchall()
        
        return [
            {
                "date": row[0].strftime("%b %d"),
                "total": row[1],
                "compliant": row[2] or 0,
                "non_compliant": row[1] - (row[2] or 0)
            }
            for row in data
        ]
        
    except Exception as e:
        print(f"Error fetching weekly report: {e}")
        return []
    finally:
        cursor.close()
        connection.close()


def get_absent_students():
    """Get students who haven't checked in today"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        today = date.today()
        
        query = """
            SELECT s.id, s.student_name, s.username
            FROM students s
            WHERE s.id NOT IN (
                SELECT DISTINCT student_id 
                FROM uniform_checks 
                WHERE DATE(check_time) = %s
            )
            ORDER BY s.student_name
        """
        
        cursor.execute(query, (today,))
        students = cursor.fetchall()
        
        return [{"id": s[0], "name": s[1], "username": s[2]} for s in students]
        
    except Exception as e:
        print(f"Error fetching absent students: {e}")
        return []
    finally:
        cursor.close()
        connection.close()


def get_non_compliant_students():
    """Get today's non-compliant students"""
    try:
        connection = get_db_connection()
        cursor = connection.cursor()
        
        today = date.today()
        
        query = """
            SELECT 
                student_name,
                check_time,
                black_blazer_or_suit,
                tie,
                white_shirt,
                id_card,
                image_path
            FROM uniform_checks
            WHERE DATE(check_time) = %s AND overall_compliance = 0
            ORDER BY check_time DESC
        """
        
        cursor.execute(query, (today,))
        checks = cursor.fetchall()
        
        results = []
        for check in checks:
            missing = []
            if not check[2]: missing.append("Blazer")
            if not check[3]: missing.append("Tie")
            if not check[4]: missing.append("Shirt")
            if not check[5]: missing.append("ID Card")
            
            results.append({
                "student_name": check[0],
                "check_time": check[1].strftime("%I:%M %p"),
                "missing_items": ", ".join(missing),
                "image_path": check[6]
            })
        
        return results
        
    except Exception as e:
        print(f"Error fetching non-compliant students: {e}")
        return []
    finally:
        cursor.close()
        connection.close()

@app.get("/",response_class=HTMLResponse)
@app.get("/teacher", response_class=HTMLResponse)
async def teacher_login(request: Request):
    """Display teacher login page"""
    return templates.TemplateResponse("teacher_login.html", {"request": request})


@app.post("/teacher/login")
async def teacher_login_post(username: str = Form(...), password: str = Form(...)):
    """Handle teacher login"""
    if username == TEACHER_USERNAME and password == TEACHER_PASSWORD:
        session_id = f"teacher_{datetime.now().timestamp()}"
        teacher_sessions[session_id] = {"username": username, "role": "teacher"}
        
        response = RedirectResponse(url=f"/teacher/dashboard?session={session_id}", status_code=303)
        return response
    else:
        return templates.TemplateResponse("teacher_login_error.html", {"request": None})


@app.get("/teacher/dashboard", response_class=HTMLResponse)
async def teacher_dashboard(request: Request, session: str):
    """Display teacher dashboard"""
    if session not in teacher_sessions:
        return RedirectResponse(url="/teacher")
    
    stats = get_statistics()
    checks = get_uniform_checks_today()
    students = get_all_students()
    
    return templates.TemplateResponse("teacher_dashboard.html", {
        "request": request,
        "session": session,
        "stats": stats,
        "checks": checks,
        "students": students,
        "current_date": date.today().strftime("%B %d, %Y")
    })


@app.get("/teacher/reports", response_class=HTMLResponse)
async def teacher_reports(request: Request, session: str):
    """Display reports page"""
    if session not in teacher_sessions:
        return RedirectResponse(url="/teacher")
    
    weekly_data = get_weekly_report()
    stats = get_statistics()
    
    return templates.TemplateResponse("teacher_reports.html", {
        "request": request,
        "session": session,
        "weekly_data": weekly_data,
        "stats": stats,
        "current_date": date.today().strftime("%B %d, %Y")
    })


@app.get("/teacher/attendance", response_class=HTMLResponse)
async def teacher_attendance(request: Request, session: str):
    """Display attendance page"""
    if session not in teacher_sessions:
        return RedirectResponse(url="/teacher")
    
    absent = get_absent_students()
    checks = get_uniform_checks_today()
    stats = get_statistics()
    
    return templates.TemplateResponse("teacher_attendance.html", {
        "request": request,
        "session": session,
        "absent_students": absent,
        "present_checks": checks,
        "stats": stats,
        "current_date": date.today().strftime("%B %d, %Y")
    })


@app.get("/teacher/violations", response_class=HTMLResponse)
async def teacher_violations(request: Request, session: str):
    """Display uniform violations page"""
    if session not in teacher_sessions:
        return RedirectResponse(url="/teacher")
    
    non_compliant = get_non_compliant_students()
    
    return templates.TemplateResponse("teacher_violations.html", {
        "request": request,
        "session": session,
        "violations": non_compliant,
        "current_date": date.today().strftime("%B %d, %Y")
    })


@app.get("/teacher/students", response_class=HTMLResponse)
async def teacher_students_list(request: Request, session: str):
    """Display all students page"""
    if session not in teacher_sessions:
        return RedirectResponse(url="/teacher")
    
    students = get_all_students()
    
    return templates.TemplateResponse("teacher_students.html", {
        "request": request,
        "session": session,
        "students": students
    })


@app.get("/teacher/about", response_class=HTMLResponse)
async def teacher_about(request: Request, session: str):
    """Display about/help page"""
    if session not in teacher_sessions:
        return RedirectResponse(url="/teacher")
    
    return templates.TemplateResponse("teacher_about.html", {
        "request": request,
        "session": session
    })


@app.get("/teacher/student/{student_id}")
async def get_student_details(student_id: int, session: str):
    """Get student uniform history"""
    if session not in teacher_sessions:
        raise HTTPException(status_code=401, detail="Unauthorized")
    
    history = get_student_history(student_id)
    return JSONResponse({"success": True, "history": history})


@app.get("/teacher/logout")
async def teacher_logout(session: str):
    """Logout teacher"""
    if session in teacher_sessions:
        del teacher_sessions[session]
    return RedirectResponse(url="/teacher")

