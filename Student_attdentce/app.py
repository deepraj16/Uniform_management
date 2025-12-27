from fastapi import FastAPI, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
from datetime import datetime, date
import pymysql
from pymysql.cursors import DictCursor

app = FastAPI()

# CORS configuration
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Database configuration
DB_CONFIG = {
    'host': 'localhost',
    'user': 'root',
    'password': '1234',
    'database': 'attendance',
    'charset': 'utf8mb4',
    'cursorclass': DictCursor
}

def get_db():
    try:
        conn = pymysql.connect(**DB_CONFIG)
        return conn
    except pymysql.Error as e:
        raise HTTPException(status_code=500, detail=f"Database connection error: {str(e)}")

# Models
class LoginRequest(BaseModel):
    username: str
    password: str

class AttendanceRecord(BaseModel):
    id: int
    student_id: int
    student_name: str
    check_time: datetime
    black_blazer_or_suit: bool
    tie: bool
    white_shirt: bool
    id_card: bool
    overall_compliance: bool
    image_path: Optional[str]

class StudentResponse(BaseModel):
    id: int
    student_name: str
    username: str

# Authentication endpoint
@app.post("/api/login")
async def login(credentials: LoginRequest):
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        query = "SELECT id, student_name, username FROM students WHERE username = %s AND password = %s"
        cursor.execute(query, (credentials.username, credentials.password))
        student = cursor.fetchone()
        
        if not student:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        return {
            "success": True,
            "student": student
        }
    finally:
        cursor.close()
        conn.close()

# Get today's attendance
@app.get("/api/attendance/today/{student_id}")
async def get_today_attendance(student_id: int):
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        query = """
            SELECT * FROM uniform_checks 
            WHERE student_id = %s 
            AND DATE(check_time) = CURDATE()
            ORDER BY check_time DESC
        """
        cursor.execute(query, (student_id,))
        records = cursor.fetchall()
        
        return {
            "success": True,
            "count": len(records),
            "records": records
        }
    finally:
        cursor.close()
        conn.close()

# Get monthly attendance
@app.get("/api/attendance/month/{student_id}")
async def get_monthly_attendance(student_id: int, year: int = None, month: int = None):
    conn = get_db()
    cursor = conn.cursor()
    
    if not year or not month:
        now = datetime.now()
        year = now.year
        month = now.month
    
    try:
        query = """
            SELECT * FROM uniform_checks 
            WHERE student_id = %s 
            AND YEAR(check_time) = %s 
            AND MONTH(check_time) = %s
            ORDER BY check_time DESC
        """
        cursor.execute(query, (student_id, year, month))
        records = cursor.fetchall()
        
        # Calculate statistics
        total_checks = len(records)
        compliant = sum(1 for r in records if r['overall_compliance'])
        non_compliant = total_checks - compliant
        
        # Calculate compliance rate for each item
        stats = {
            'total_checks': total_checks,
            'compliant': compliant,
            'non_compliant': non_compliant,
            'compliance_rate': round((compliant / total_checks * 100) if total_checks > 0 else 0, 2),
            'item_compliance': {
                'black_blazer': sum(1 for r in records if r['black_blazer_or_suit']),
                'tie': sum(1 for r in records if r['tie']),
                'white_shirt': sum(1 for r in records if r['white_shirt']),
                'id_card': sum(1 for r in records if r['id_card'])
            }
        }
        
        return {
            "success": True,
            "year": year,
            "month": month,
            "statistics": stats,
            "records": records
        }
    finally:
        cursor.close()
        conn.close()

# Get attendance summary
@app.get("/api/attendance/summary/{student_id}")
async def get_attendance_summary(student_id: int):
    conn = get_db()
    cursor = conn.cursor()
    
    try:
        # Overall statistics
        query = """
            SELECT 
                COUNT(*) as total_checks,
                SUM(overall_compliance) as total_compliant,
                SUM(black_blazer_or_suit) as blazer_count,
                SUM(tie) as tie_count,
                SUM(white_shirt) as shirt_count,
                SUM(id_card) as id_card_count
            FROM uniform_checks 
            WHERE student_id = %s
        """
        cursor.execute(query, (student_id,))
        summary = cursor.fetchone()
        
        return {
            "success": True,
            "summary": summary
        }
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)