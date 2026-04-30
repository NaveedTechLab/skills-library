# Authentication & Security Patterns

## Table of Contents
1. [JWT Authentication](#jwt-authentication)
2. [Password Hashing](#password-hashing)
3. [OAuth2 with Bearer Token](#oauth2-with-bearer-token)
4. [Role-Based Access Control](#role-based-access-control)
5. [Security Headers & CORS](#security-headers--cors)

---

## JWT Authentication

### `app/core/security.py`

```python
from datetime import datetime, timedelta
from typing import Any
from jose import jwt, JWTError
from passlib.context import CryptContext
from app.config import settings

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

ALGORITHM = "HS256"

def create_access_token(subject: str | Any, expires_delta: timedelta | None = None) -> str:
    if expires_delta:
        expire = datetime.utcnow() + expires_delta
    else:
        expire = datetime.utcnow() + timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)

    to_encode = {"exp": expire, "sub": str(subject)}
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=ALGORITHM)

def verify_token(token: str) -> str | None:
    try:
        payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[ALGORITHM])
        return payload.get("sub")
    except JWTError:
        return None

def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

def get_password_hash(password: str) -> str:
    return pwd_context.hash(password)
```

---

## Password Hashing

### Requirements

```
passlib[bcrypt]>=1.7.4
bcrypt>=4.0.0
```

### Password Validation Schema

```python
from pydantic import field_validator

class UserCreate(BaseModel):
    email: str
    password: str

    @field_validator("password")
    @classmethod
    def validate_password(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("Password must be at least 8 characters")
        if not any(c.isupper() for c in v):
            raise ValueError("Password must contain uppercase letter")
        if not any(c.islower() for c in v):
            raise ValueError("Password must contain lowercase letter")
        if not any(c.isdigit() for c in v):
            raise ValueError("Password must contain digit")
        return v
```

---

## OAuth2 with Bearer Token

### `app/dependencies.py`

```python
from typing import Annotated
from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.core.security import verify_token
from app.models.user import User
from app.db.session import get_db

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/v1/auth/login")

def get_current_user(
    db: Session = Depends(get_db),
    token: str = Depends(oauth2_scheme),
) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    user_id = verify_token(token)
    if user_id is None:
        raise credentials_exception

    user = db.query(User).filter(User.id == user_id).first()
    if user is None:
        raise credentials_exception

    return user

CurrentUser = Annotated[User, Depends(get_current_user)]

def get_current_active_user(current_user: CurrentUser) -> User:
    if not current_user.is_active:
        raise HTTPException(status_code=400, detail="Inactive user")
    return current_user

ActiveUser = Annotated[User, Depends(get_current_active_user)]
```

### Auth Endpoints

```python
from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from datetime import timedelta
from app.core.security import verify_password, create_access_token
from app.config import settings

router = APIRouter(prefix="/auth", tags=["auth"])

@router.post("/login")
def login(
    db: DbSession,
    form_data: OAuth2PasswordRequestForm = Depends(),
):
    user = db.query(User).filter(User.email == form_data.username).first()
    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect email or password",
            headers={"WWW-Authenticate": "Bearer"},
        )

    access_token = create_access_token(
        subject=user.id,
        expires_delta=timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES),
    )
    return {"access_token": access_token, "token_type": "bearer"}
```

---

## Role-Based Access Control

### User Model with Roles

```python
from sqlalchemy import Column, String, Boolean, Enum as SQLEnum
import enum

class UserRole(str, enum.Enum):
    USER = "user"
    ADMIN = "admin"
    SUPERADMIN = "superadmin"

class User(BaseModel):
    email = Column(String(255), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    role = Column(SQLEnum(UserRole), default=UserRole.USER, nullable=False)
```

### Role Dependency

```python
from functools import wraps
from fastapi import HTTPException, status

def require_role(*allowed_roles: UserRole):
    def dependency(current_user: CurrentUser) -> User:
        if current_user.role not in allowed_roles:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Insufficient permissions",
            )
        return current_user
    return dependency

# Usage
AdminUser = Annotated[User, Depends(require_role(UserRole.ADMIN, UserRole.SUPERADMIN))]

@router.delete("/{user_id}")
def delete_user(user_id: int, admin: AdminUser, db: DbSession):
    # Only admins can delete users
    ...
```

---

## Security Headers & CORS

### `app/core/middleware.py`

```python
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.trustedhost import TrustedHostMiddleware
from app.config import settings

def add_middleware(app: FastAPI) -> None:
    # CORS
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Trusted hosts (production)
    if not settings.DEBUG:
        app.add_middleware(
            TrustedHostMiddleware,
            allowed_hosts=settings.ALLOWED_HOSTS,
        )
```

### Security Headers Middleware

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Strict-Transport-Security"] = "max-age=31536000; includeSubDomains"
        return response
```

### Rate Limiting (with slowapi)

```python
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded

limiter = Limiter(key_func=get_remote_address)

def add_rate_limiting(app: FastAPI) -> None:
    app.state.limiter = limiter
    app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)

# Usage in endpoint
@router.post("/login")
@limiter.limit("5/minute")
def login(request: Request, ...):
    ...
```
