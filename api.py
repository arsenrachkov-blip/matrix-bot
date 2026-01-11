from fastapi import FastAPI, HTTPException, Depends, Response
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel
from datetime import datetime, timedelta
from jose import jwt, JWTError
from passlib.context import CryptContext
import httpx

import database
from config import SECRET_KEY, CLIENT_JAR_URL, LOADER_VERSION, LOADER_DOWNLOAD_URL, LOADER_CHANGELOG

app = FastAPI(title="Matrix API")
security = HTTPBearer()
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

class UpdateCheckResponse(BaseModel):
    update_available: bool
    latest_version: str = ""
    download_url: str = ""
    changelog: str = ""

class LoginRequest(BaseModel):
    username: str
    password: str
    hwid: str

class LoginResponse(BaseModel):
    success: bool
    message: str = ""
    token: str = ""
    username: str = ""
    expires_at: str = ""

def create_token(username: str) -> str:
    expire = datetime.utcnow() + timedelta(hours=24)
    return jwt.encode(
        {"sub": username, "exp": expire},
        SECRET_KEY,
        algorithm="HS256"
    )

def verify_token(credentials: HTTPAuthorizationCredentials = Depends(security)) -> str:
    try:
        payload = jwt.decode(credentials.credentials, SECRET_KEY, algorithms=["HS256"])
        return payload.get("sub")
    except JWTError:
        raise HTTPException(status_code=401, detail="Invalid token")

@app.post("/auth/login", response_model=LoginResponse)
async def login(request: LoginRequest):
    user = await database.get_user_by_username(request.username)
    
    if not user:
        return LoginResponse(success=False, message="Пользователь не найден")
    
    if not pwd_context.verify(request.password, user['password_hash']):
        return LoginResponse(success=False, message="Неверный пароль")
    
    if not user['is_active']:
        return LoginResponse(success=False, message="Аккаунт заблокирован")
    
    # Проверка подписки
    has_sub = await database.check_subscription(request.username)
    if not has_sub:
        return LoginResponse(success=False, message="Подписка истекла")
    
    # Проверка HWID
    if user['hwid'] and user['hwid'] != request.hwid:
        return LoginResponse(success=False, message="HWID не совпадает. Обратитесь в поддержку")
    
    # Привязка HWID если ещё не привязан
    if not user['hwid']:
        await database.update_hwid(request.username, request.hwid)
    
    token = create_token(request.username)
    
    return LoginResponse(
        success=True,
        token=token,
        username=request.username,
        expires_at=user['subscription_end'] or ""
    )

@app.get("/client/download")
async def download_client(username: str = Depends(verify_token)):
    # Проверяем подписку ещё раз
    has_sub = await database.check_subscription(username)
    if not has_sub:
        raise HTTPException(status_code=403, detail="Subscription expired")
    
    # Скачиваем JAR из облака и отдаём клиенту
    async with httpx.AsyncClient(follow_redirects=True, timeout=60.0) as client:
        response = await client.get(CLIENT_JAR_URL)
        if response.status_code != 200:
            raise HTTPException(status_code=500, detail="Failed to fetch client")
        
        return Response(
            content=response.content,
            media_type="application/java-archive",
            headers={"Content-Disposition": "attachment; filename=client.jar"}
        )

@app.get("/update/check", response_model=UpdateCheckResponse)
async def check_update(version: str = "0.0.0"):
    # Сравниваем версии
    current_parts = [int(x) for x in version.split(".")]
    latest_parts = [int(x) for x in LOADER_VERSION.split(".")]
    
    update_available = latest_parts > current_parts
    
    return UpdateCheckResponse(
        update_available=update_available,
        latest_version=LOADER_VERSION,
        download_url=LOADER_DOWNLOAD_URL if update_available else "",
        changelog=LOADER_CHANGELOG if update_available else ""
    )

@app.on_event("startup")
async def startup():
    await database.init_db()
