from fastapi import Depends
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session
from app.config.settings import settings
from app.core.database import SessionLocal
from app.core.security import verify_token
from app.core.errors import DataTutorException
from app.core.database import  get_db

# Define que esperamos un Bearer token en el Header 'Authorization'
oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.KEYCLOAK_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/token")

def get_current_user(token: str = Depends(oauth2_scheme)) -> dict:
    payload = verify_token(token)
    sub = payload.get("sub")
    if not sub:
        raise DataTutorException("token_invalid","El token no contiene un identificador de usuario.", 401)
    # Extraemos el ID único del usuario (sub) y sus roles
    return {
        "sub": sub,
        "preferred_username": payload.get("preferred_username"),
        "roles": payload.get("realm_access", {}).get("roles", [])
    }