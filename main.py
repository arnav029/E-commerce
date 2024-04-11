from fastapi import FastAPI, Request, HTTPException, status
from tortoise import models
from tortoise.contrib.fastapi import register_tortoise
from models import *
from authentication import (get_hashed_password, verify_token)

from email2 import *
from tortoise.exceptions import IntegrityError

from tortoise.signals import post_save
from typing import List, Optional, Type
from tortoise import BaseDBAsyncClient
from passlib.context import CryptContext

from fastapi.responses import HTMLResponse

from starlette.templating import Jinja2Templates

app = FastAPI()


@post_save(User)
async def create_business(
        sender: "Type[User]",
        instance: User,
        created: bool,
        using_db: "Optional[BaseDBAsyncClient]",
        update_fields: List[str]
) -> None:
    if created:
        business_obj = await Business.create(
            business_name=instance.username, owner=instance
        )

        await business_pydantic.from_tortoise_orm(business_obj)
        await send_email([instance.email_id], instance)


@app.post("/registration")
async def user_registration(user: user_pydanticIn):
    try:
        user_info = user.dict(exclude_unset=True)
        user_info["password"] = get_hashed_password(user_info["password"])
        user_obj = await User.create(**user_info)
        new_user = await user_pydantic.from_tortoise_orm(user_obj)
        return {
            "status": "ok",
            "data": f"Welcome {new_user.username}. Please check your email inbox. "
        }
    except IntegrityError as e:
        if "email_id" in str(e):  # Check if error is related to email constraint
            return {"status": "error", "message": "Email address already in use."}
        else:
            raise e


templates = Jinja2Templates(directory="templates")


@app.get('/verification', response_class=HTMLResponse)
async def email_verification(request: Request, token: str):
    user = await verify_token(token)

    if user and not user.is_verified:
        user.is_verified = True
        await user.save()
        return templates.TemplateResponse("verification.html",
                                          {"request": request,
                                           "username": user.username})

        raise Exception(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detaIl="Invalid token or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )



@app.get("/")
def root():
    return {"Hello": "There"}


register_tortoise(
    app,
    db_url="sqlite://database.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=True,
    add_exception_handlers=True
)
