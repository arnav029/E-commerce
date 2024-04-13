import fileinput

from fastapi import FastAPI, Request, HTTPException, status, Depends
from tortoise import models
from tortoise.contrib.fastapi import register_tortoise
from models import *

#authentication
from authentication import *
from fastapi.security import (OAuth2PasswordBearer, OAuth2PasswordRequestForm)

from email2 import *
from tortoise.exceptions import IntegrityError

from tortoise.signals import post_save
from typing import List, Optional, Type
from tortoise import BaseDBAsyncClient
from passlib.context import CryptContext

from fastapi.responses import HTMLResponse

from starlette.templating import Jinja2Templates

#image upload
from fastapi import File,UploadFile
import secrets
from fastapi.staticfiles import StaticFiles
from PIL import Image

app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')

#static file setup config
app.mount("/static", StaticFiles(directory="static"),name="static")

@app.post("/token")
async def generate_token(request_form: OAuth2PasswordRequestForm = Depends()):
    token = await token_generator(request_form.username, request_form.password)
    return {"access_token": token, "token_type": "bearer"}


async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, config_credential["SECRET"], algorithms= ['HS256'])
        user = await User.get(id = payload.get("id"))

    except:
        raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail = "Invalid username or password",
                headers={"WWW-Authenticate": "Bearer"}

        )

    return await user


@app.post("/user/me")
async def user_login(user: user_pydanticIn = Depends(get_current_user)):
    business = await Business.get(owner=user)
    logo = business.logo
    logo_path = "localhost:8000/static/images" + logo

    return {
        "status": "ok",
        "data": {
            "username": user.username,
            "email": user.email_id,
            "verified": user.is_verified,
            "joined date": user.join_date.strftime("%b %d %Y"),
            "logo": logo_path
        }
    }


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


@app.post("/uploadfile/profile")
async def create_upload_file(file: UploadFile = File(...),
                             user: user_pydanticIn = Depends(get_current_user)):
    FILEPATH = "./static/images"
    filename = file.filename
    extension = filename.split(".")[1] #Getting extension

    if extension not in ["png", "jpg"]:
        return {"status": "Error", "detail": "File extension not supported"}

    token_name = secrets.token_hex(10) + "." + extension

    generated_name = FILEPATH + token_name
    file_content = await file.read()

    with open(generated_name, "wb") as file:
        file.write(file_content)

    #PILLOW
    img = Image.open(generated_name)
    img = img.resize(size= (200,200))
    img.save(generated_name)

    file.close()

    business  = await Business.get(owner=user)
    owner = await business.owner

    if owner == user:
        business.logo = token_name
        await business.save()

    else:
        raise Exception(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detaIl="Not authenticated to perform this action",
            headers={"WWW-Authenticate": "Bearer"}
        )

    file_url = "localhost:8000" + generated_name[1:]

    return {"status": "ok", "filename": file_url}

@app.post("/uploadfile/products/{id}")
async def create_upload_file(id: int, file: UploadFile = File(...),
                             user: user_pydantic = Depends(get_current_user)):
    FILEPATH = "./static/images"
    filename = file.filename
    extension = filename.split(".")[1] #Getting extension

    if extension not in ["png", "jpg"]:
        return {"status": "Error", "detail": "File extension not supported"}

    token_name = secrets.token_hex(10) + "." + extension

    generated_name = FILEPATH + token_name
    file_content = await file.read()

    with open(generated_name, "wb") as file:
        file.write(file_content)

    #PILLOW
    img = Image.open(generated_name)
    img = img.resize(size= (200,200))
    img.save(generated_name)

    file.close()

    product = await Product.get(id= id)
    business =   await product.business
    owner = await  business.owner

    if owner == user:
        product.product_image = token_name
        await product.save()

    else:
        raise Exception(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detaIl="Not authenticated to perform this action",
            headers={"WWW-Authenticate": "Bearer"}
        )

#CRUD functionality
@app.post("/products")
async def add_new_product(product: product_pydanticIn,
                          user: user_pydantic = Depends(get_current_user)):
    product = product.dict(exclude_unset=True)

    #to avoid division error by zero
    if product["original_price"] >0:
        product["percentage_discount"] = ((product["original_price"] - product["new_price"]) / product["original_price"]) *100

        product_obj = await Product.create(**product, business=user)
        product_obj = await product_pydantic.from_tortoise_orm(product_obj)

        return { "status": "ok", "data": product_obj}

    else:
        return {"status": "error"}


@app.get("/product")
async def get_product():
    response = await product_pydantic.from_tortoise_orm(Product.all())
    return {"status": "ok", "data": response}


@app.get("/products/{id}")
async def get_product(id: int):
    product = await Product.get(id=id)
    business = await product.business
    owner = await business.owner
    response = await product_pydantic.from_queryset_single(product)
    return {"status": "ok",
            "data": {
                "product_details": response,
                "business_details": {
                    "name": business.business_name,
                    "city": business.city,
                    "region": business.region,
                    "description": business.declaration,
                    "logo": business.logo,
                    "owner_id": owner.id,
                    "email": owner.email,
                    "join_date": owner.join_date.strftime("%b %d %Y")


                }
            }
        }

@app.delete("products/{id}")
async def delete_product(id: int, user: user_pydantic = Depends(get_current_user)):
    product = await Product.get(id=id)
    business = await product.business
    owner = await business.owner

    if user == owner:
        product.delete()

    else:
        raise Exception(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detaIl="Not authenticated to perform this action",
            headers={"WWW-Authenticate": "Bearer"}
        )

    return {
        "status": "ok"
    }





register_tortoise(
    app,
    db_url="sqlite://database.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=True,
    add_exception_handlers=True
)
