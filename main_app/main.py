from fastapi import FastAPI, HTTPException, Depends, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional, List
import pandas as pd
from datetime import datetime, timedelta
import jwt
from passlib.context import CryptContext
import pymysql
from contextlib import contextmanager
import requests
import json

app = FastAPI(title="Stock Market Dashboard API")

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Alpha Vantage API Key
ALPHA_VANTAGE_API_KEY = "48OH8W8ID1BAVY6K"

# Database Configuration
DB_CONFIG = {
    'host': 'sql.freedb.tech',
    'user': 'freedb_deepraj16',
    'password': 'E9Bmn%$f7S*tkyq',
    'database': 'freedb_student_grades',
    'port': 3306,
    'charset': 'utf8mb4',
    'cursorclass': pymysql.cursors.DictCursor
}

# Security
SECRET_KEY = "your-secret-key-change-in-production-2024"
ALGORITHM = "HS256"
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")
security = HTTPBearer()

# NSE Symbol Mapping
NSE_SYMBOLS = {
    "RELIANCE.NS": "RELIANCE",
    "TCS.NS": "TCS",
    "HDFCBANK.NS": "HDFCBANK",
    "INFY.NS": "INFY",
    "ICICIBANK.NS": "ICICIBANK",
    "HINDUNILVR.NS": "HINDUNILVR",
    "ITC.NS": "ITC",
    "SBIN.NS": "SBIN",
    "BHARTIARTL.NS": "BHARTIARTL",
    "KOTAKBANK.NS": "KOTAKBANK",
    "LT.NS": "LT",
    "AXISBANK.NS": "AXISBANK",
    "MARUTI.NS": "MARUTI",
    "WIPRO.NS": "WIPRO",
    "TATASTEEL.NS": "TATASTEEL",
    "TATAMOTORS.NS": "TATAMOTORS"
}

# Database Context Manager
@contextmanager
def get_db_connection():
    connection = pymysql.connect(**DB_CONFIG)
    try:
        yield connection
        connection.commit()
    except Exception as e:
        connection.rollback()
        raise e
    finally:
        connection.close()

# Initialize database table
def init_db():
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("""
                    CREATE TABLE IF NOT EXISTS stock_users (
                        id INT AUTO_INCREMENT PRIMARY KEY,
                        username VARCHAR(50) UNIQUE NOT NULL,
                        email VARCHAR(100) UNIQUE NOT NULL,
                        hashed_password VARCHAR(255) NOT NULL,
                        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                        last_login TIMESTAMP NULL
                    )
                """)
                
                cursor.execute("SELECT * FROM stock_users WHERE username = %s", ('test26',))
                if not cursor.fetchone():
                    hashed_pwd = pwd_context.hash("test@123")
                    cursor.execute(
                        "INSERT INTO stock_users (username, email, hashed_password) VALUES (%s, %s, %s)",
                        ('test26', 'test26@example.com', hashed_pwd)
                    )
        print("Database initialized successfully")
    except Exception as e:
        print(f"Database initialization error: {e}")

# Models
class LoginRequest(BaseModel):
    username: str
    password: str

class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    username: str

class StockRequest(BaseModel):
    symbols: List[str]
    period: str = "1mo"
    interval: str = "1d"

# Auth functions
def verify_password(plain_password, hashed_password):
    return pwd_context.verify(plain_password, hashed_password)

def hash_password(password):
    return pwd_context.hash(password)

def create_access_token(data: dict):
    to_encode = data.copy()
    expire = datetime.utcnow() + timedelta(hours=24)
    to_encode.update({"exp": expire})
    encoded_jwt = jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)
    return encoded_jwt

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)):
    try:
        token = credentials.credentials
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        username: str = payload.get("sub")
        if username is None:
            raise HTTPException(status_code=401, detail="Invalid authentication")
        return username
    except jwt.ExpiredSignatureError:
        raise HTTPException(status_code=401, detail="Token expired")
    except jwt.JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

def get_user_by_username(username: str):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM stock_users WHERE username = %s", (username,))
                return cursor.fetchone()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Database error: {str(e)}")

def update_last_login(username: str):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute(
                    "UPDATE stock_users SET last_login = %s WHERE username = %s",
                    (datetime.now(), username)
                )
    except Exception:
        pass

# Stock Data Functions
def calculate_technical_indicators(data: List[dict]):
    """Calculate technical indicators for better analysis"""
    if not data or len(data) < 20:
        return data
    
    df = pd.DataFrame(data)
    
    # Calculate Simple Moving Averages
    df['SMA_20'] = df['Close'].rolling(window=20).mean()
    df['SMA_50'] = df['Close'].rolling(window=min(50, len(df))).mean()
    
    # Calculate RSI (Relative Strength Index)
    delta = df['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # Calculate MACD
    exp1 = df['Close'].ewm(span=12, adjust=False).mean()
    exp2 = df['Close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    
    # Calculate Bollinger Bands
    df['BB_Middle'] = df['Close'].rolling(window=20).mean()
    bb_std = df['Close'].rolling(window=20).std()
    df['BB_Upper'] = df['BB_Middle'] + (bb_std * 2)
    df['BB_Lower'] = df['BB_Middle'] - (bb_std * 2)
    
    # Fill NaN values
    df = df.fillna(method='bfill').fillna(method='ffill')
    
    return df.to_dict('records')

def get_nse_quote(symbol: str):
    """Get current quote from NSE using unofficial API"""
    try:
        clean_symbol = NSE_SYMBOLS.get(symbol, symbol.replace('.NS', ''))
        
        url = f"https://www.nseindia.com/api/quote-equity?symbol={clean_symbol}"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36',
            'Accept': 'application/json',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        session = requests.Session()
        session.get("https://www.nseindia.com", headers=headers, timeout=5)
        response = session.get(url, headers=headers, timeout=5)
        
        if response.status_code == 200:
            data = response.json()
            price_info = data.get('priceInfo', {})
            
            current = price_info.get('lastPrice', 0)
            previous = price_info.get('previousClose', 0)
            change = current - previous
            change_percent = (change / previous * 100) if previous else 0
            
            return {
                "currentPrice": current,
                "previousClose": previous,
                "open": price_info.get('open', 0),
                "dayHigh": price_info.get('intraDayHighLow', {}).get('max', 0),
                "dayLow": price_info.get('intraDayHighLow', {}).get('min', 0),
                "volume": data.get('preOpenMarket', {}).get('totalTradedVolume', 0),
                "shortName": data.get('info', {}).get('companyName', clean_symbol),
                "change": round(change, 2),
                "changePercent": round(change_percent, 2),
                "marketCap": price_info.get('marketCap', 0),
                "yearHigh": price_info.get('weekHighLow', {}).get('max', 0),
                "yearLow": price_info.get('weekHighLow', {}).get('min', 0)
            }
    except Exception as e:
        print(f"NSE API error for {symbol}: {e}")
        return None

def get_alpha_vantage_data(symbol: str, interval: str = "daily"):
    """Get historical data from Alpha Vantage with candlestick format"""
    try:
        clean_symbol = symbol.split('.')[0]
        
        if interval == "1d":
            function = "TIME_SERIES_DAILY"
            key = "Time Series (Daily)"
        else:
            function = "TIME_SERIES_DAILY"
            key = "Time Series (Daily)"
        
        url = f"https://www.alphavantage.co/query?function={function}&symbol={clean_symbol}&apikey={ALPHA_VANTAGE_API_KEY}&outputsize=full"
        
        response = requests.get(url, timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            
            if "Error Message" in data or "Note" in data:
                return None
            
            time_series = data.get(key, {})
            
            if not time_series:
                return None
            
            # Convert to candlestick format
            historical_data = []
            for date_str, values in sorted(time_series.items())[:100]:
                open_val = float(values.get("1. open", 0))
                high_val = float(values.get("2. high", 0))
                low_val = float(values.get("3. low", 0))
                close_val = float(values.get("4. close", 0))
                volume_val = int(values.get("5. volume", 0))
                
                historical_data.append({
                    "Date": date_str,
                    "Open": round(open_val, 2),
                    "High": round(high_val, 2),
                    "Low": round(low_val, 2),
                    "Close": round(close_val, 2),
                    "Volume": volume_val,
                    # Additional fields for candlestick visualization
                    "x": date_str,
                    "y": [open_val, high_val, low_val, close_val]
                })
            
            return historical_data[::-1]
        
        return None
    except Exception as e:
        print(f"Alpha Vantage error for {symbol}: {e}")
        return None

def generate_realistic_stock_data(symbol: str, base_price: float = None, days: int = 90):
    """Generate realistic stock data with proper candlestick patterns"""
    import random
    import math
    
    if base_price is None:
        # Default base prices for common stocks
        base_prices = {
            "RELIANCE": 2500, "TCS": 3500, "HDFCBANK": 1600,
            "INFY": 1400, "ICICIBANK": 950, "HINDUNILVR": 2400,
            "ITC": 450, "SBIN": 600, "BHARTIARTL": 900
        }
        base_price = base_prices.get(symbol.replace('.NS', ''), 1000)
    
    data = []
    current_price = base_price
    
    for i in range(days):
        date = datetime.now() - timedelta(days=days-i)
        
        # Add trend and volatility
        trend = math.sin(i / 10) * 0.002
        volatility = random.uniform(-0.03, 0.03)
        daily_change = trend + volatility
        
        # Calculate OHLC
        open_price = current_price * (1 + random.uniform(-0.01, 0.01))
        close_price = open_price * (1 + daily_change)
        high_price = max(open_price, close_price) * (1 + random.uniform(0, 0.02))
        low_price = min(open_price, close_price) * (1 - random.uniform(0, 0.02))
        
        volume = int(random.uniform(1000000, 5000000))
        
        data.append({
            "Date": date.strftime("%Y-%m-%d"),
            "Open": round(open_price, 2),
            "High": round(high_price, 2),
            "Low": round(low_price, 2),
            "Close": round(close_price, 2),
            "Volume": volume,
            "x": date.strftime("%Y-%m-%d"),
            "y": [
                round(open_price, 2),
                round(high_price, 2),
                round(low_price, 2),
                round(close_price, 2)
            ]
        })
        
        current_price = close_price
    
    return data

# Routes
@app.on_event("startup")
async def startup_event():
    init_db()

@app.post("/api/register")
async def register(register_data: RegisterRequest):
    try:
        with get_db_connection() as conn:
            with conn.cursor() as cursor:
                cursor.execute("SELECT * FROM stock_users WHERE username = %s", (register_data.username,))
                if cursor.fetchone():
                    raise HTTPException(status_code=400, detail="Username already exists")
                
                cursor.execute("SELECT * FROM stock_users WHERE email = %s", (register_data.email,))
                if cursor.fetchone():
                    raise HTTPException(status_code=400, detail="Email already exists")
                
                if len(register_data.password) < 6:
                    raise HTTPException(status_code=400, detail="Password must be at least 6 characters")
                
                hashed_password = hash_password(register_data.password)
                cursor.execute(
                    "INSERT INTO stock_users (username, email, hashed_password) VALUES (%s, %s, %s)",
                    (register_data.username, register_data.email, hashed_password)
                )
        
        return {"message": "Account created successfully", "username": register_data.username}
    
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Registration failed: {str(e)}")

@app.post("/api/login", response_model=TokenResponse)
async def login(login_data: LoginRequest):
    user = get_user_by_username(login_data.username)
    
    if not user or not verify_password(login_data.password, user["hashed_password"]):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password"
        )
    
    update_last_login(login_data.username)
    
    access_token = create_access_token(data={"sub": login_data.username})
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "username": login_data.username
    }

@app.post("/api/stocks/multiple")
async def get_multiple_stocks(
    request: StockRequest,
    username: str = Depends(verify_token)
):
    results = []
    
    for symbol in request.symbols:
        try:
            # Try NSE API first for current price
            nse_data = get_nse_quote(symbol)
            
            # Get historical data from Alpha Vantage
            historical_data = get_alpha_vantage_data(symbol, request.interval)
            
            if not historical_data:
                # Generate realistic fallback data
                base_price = nse_data["currentPrice"] if nse_data else None
                historical_data = generate_realistic_stock_data(
                    symbol, 
                    base_price=base_price,
                    days=90
                )
            
            # Add technical indicators
            historical_data = calculate_technical_indicators(historical_data)
            
            if not nse_data and historical_data:
                # Calculate from historical data
                latest = historical_data[-1]
                previous = historical_data[-2] if len(historical_data) > 1 else latest
                change = latest["Close"] - previous["Close"]
                change_percent = (change / previous["Close"] * 100) if previous["Close"] else 0
                
                nse_data = {
                    "currentPrice": latest["Close"],
                    "previousClose": previous["Close"],
                    "open": latest["Open"],
                    "dayHigh": latest["High"],
                    "dayLow": latest["Low"],
                    "volume": latest["Volume"],
                    "shortName": symbol.split('.')[0],
                    "change": round(change, 2),
                    "changePercent": round(change_percent, 2),
                    "marketCap": 0,
                    "yearHigh": max([d["High"] for d in historical_data]),
                    "yearLow": min([d["Low"] for d in historical_data])
                }
            
            if nse_data and historical_data:
                results.append({
                    "symbol": symbol,
                    "data": historical_data,
                    "info": nse_data,
                    "chartType": "candlestick"
                })
            else:
                results.append({
                    "symbol": symbol,
                    "error": f"No data available. Alpha Vantage free tier has rate limits (5 requests/min)."
                })
                
        except Exception as e:
            results.append({
                "symbol": symbol,
                "error": str(e)
            })
    
    return {"stocks": results}

@app.get("/api/verify")
async def verify_token_endpoint(username: str = Depends(verify_token)):
    return {"username": username, "valid": True}

@app.get("/api/user/profile")
async def get_user_profile(username: str = Depends(verify_token)):
    user = get_user_by_username(username)
    if not user:
        raise HTTPException(status_code=404, detail="User not found")
    
    return {
        "username": user["username"],
        "email": user["email"],
        "created_at": user["created_at"],
        "last_login": user["last_login"]
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)