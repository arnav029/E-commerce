from fastapi.exceptions import HTTPException
from passlib.context import CryptContext
from dotenv import dotenv_values
from models import User
from fastapi import status
import jwt

config_credential = dotenv_values(".env")

pwd_context = CryptContext(schemes=['bcrypt'], deprecated='auto')


def get_hashed_password(password):
    return pwd_context.hash(password)


async def verify_token(token: str):
    try:
        payload = jwt.decode(token, config_credential['SECRET'], algorithms=['HS256'])
        user = await User.get(id=payload.get("id"))


    except:
        raise Exception(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detial="Invalid token",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return user
