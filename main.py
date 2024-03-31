from fastapi import FastAPI
from tortoise import models
from tortoise.contrib.fastapi import register_tortoise
from models import *
from authentication import get_hashed_password
from tortoise.signals import  post_save
from tortoise import List,Optional, Type
from tortoise import BaseDBAsyncClient
from passlib.context import CryptContext


app = FastAPI()


@post_save(User)
async def create_business(
        sender:"Type[User]",
        instance: User,
        created: bool,
        using_db: "Optional[BaseDBAsyncClient]",
        update_fields: List[str]
) -> None:
    if created:
        business_obj = await Business.create(
            business_name = instance.username , owner = instance
        )

        await business_pydantic.from_tortoise_orm(business_obj)





@app.post("/registration")
async def user_registraion(user: user_pydantic):
    user_info = user.dict(exclude_unset=True)
    user_info["password"] = get_hashed_password(user_info["password"])
    user_obj = await User.create(**user_info)
    new_user = await user_pydantic.from_tortoise_orm(user_obj)
    return {
        "status": "ok",
        "data" : f"Welcome {new_user.username}. Please check your email inbox."
    }

@app.get("/")
def root():
    return {"Hello":"World"}


register_tortoise(
    app,
    db_url = "sqlite://database.sqlite3",
    modules = {"models": ["models"]},
    generate_schemas = True,
    add_exception_handlers = True
)


