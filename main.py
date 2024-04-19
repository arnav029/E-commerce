from fastapi import FastAPI, Request, HTTPException, status, Depends
from tortoise.contrib.fastapi import register_tortoise
from models import *
# authentication
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

# image upload
from fastapi import File, UploadFile
import secrets
from fastapi.staticfiles import StaticFiles
from PIL import Image

from datetime import datetime

#
app = FastAPI()

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='token')

# static file setup config
app.mount("/static", StaticFiles(directory="static"), name="static")

from fastapi import HTTPException


class UnauthorizedUpdate(HTTPException):
    def __init__(self, detail: str, status_code: int = status.HTTP_401_UNAUTHORIZED):
        super().__init__(
            status_code=status_code,
            detail=detail,
            headers={"WWW-Authenticate": "Bearer"}
        )


@app.post("/token")
async def generate_token(request_form: OAuth2PasswordRequestForm = Depends()):
    token = await token_generator(request_form.username, request_form.password)
    return {"access_token": token, "token_type": "bearer"}


async def get_current_user(token: str = Depends(oauth2_scheme)):
    try:
        payload = jwt.decode(token, config_credential["SECRET"], algorithms=['HS256'])
        user = await User.get(id=payload.get("id"))

    except:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid username or password",
            headers={"WWW-Authenticate": "Bearer"}

        )

    return await user


@app.post("/user/me")
async def user_login(user: user_pydanticIn = Depends(get_current_user)):
    business = await Business.get(owner=user)
    logo = business.logo
    logo_path = "https://e-commerce-api-7osv.onrender.com//static/images" + logo

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

    else:
        return UnauthorizedUpdate(detail="Invalid token  or expired token", status_code=status.HTTP_403_FORBIDDEN)


@app.get("/")
async def root():
    """
    Welcome to the E-commerce API!

    This API is currently under maintenance and may take up to 50 seconds to initiate.
    Here, you can manage your products, user accounts, and more.

    **Getting Started:**

    1. **Registration:** Create a new user account: https://docs.render.com/api
    2. **Verification:** Check your account verification status: https://apiando.com/en/e-commerce/

    **Product Management:**

    - View all products: https://docs.render.com/api
    - Upload product images (requires product ID): https://mailchimp.com/developer/marketing/docs/e-commerce/
    - Manage products (CRUD operations):
        - Create (publish): https://medium.com/@lotus.lin/e-commerce-apis-introduction-29664558a3b0
        - Read (specific product): https://mailchimp.com/developer/marketing/docs/e-commerce/
        - Update: https://mailchimp.com/developer/marketing/docs/e-commerce/
        - Delete: https://mailchimp.com/developer/marketing/docs/e-commerce/

    **Profile Management:**

    - Upload your profile picture: https://docs.render.com/

    **Note:** Use Postman for sending POST requests to interact with the API.
    """

    return {
        "Welcome Message": "Welcome to the E-commerce API!",
        "API Status": "Under Maintenance (may take up to 50 seconds to initiate)",
        "Functionality": "Create and manage your products and user accounts",
        "Getting Started": {
            "Registration": "https://e-commerce-api-7osv.onrender.com/registration",
            "Verification": "https://e-commerce-api-7osv.onrender.com/user/me",
        },
        "Product Management": {
            "View All Products": "https://e-commerce-api-7osv.onrender.com/product",
            "Upload Product Images": "https://e-commerce-api-7osv.onrender.com/uploadfile/product/{id}",
            "CRUD Operations": {
                "Create (Publish)": "https://e-commerce-api-7osv.onrender.com/products/",
                "Read (Specific Product)": "https://e-commerce-api-7osv.onrender.com/product/{id}",
                "Update": "https://e-commerce-api-7osv.onrender.com/product/{id}",
                "Delete": "https://e-commerce-api-7osv.onrender.com/{id}",
            },
        },
        "Profile Management": {
            "Upload Profile Picture": "https://e-commerce-api-7osv.onrender.com/uploadfile/profile",
        },
        "Note": "Use Postman for sending POST requests.",
    }


@app.post("/uploadfile/profile")
async def create_upload_file(file: UploadFile = File(...),
                             user: user_pydanticIn = Depends(get_current_user)):
    FILEPATH = "./static/images"
    filename = file.filename
    extension = filename.split(".")[1]  # Getting extension

    if extension not in ["png", "jpg"]:
        return {"status": "Error", "detail": "File extension not supported"}

    token_name = secrets.token_hex(10) + "." + extension

    generated_name = FILEPATH + token_name
    file_content = await file.read()

    with open(generated_name, "wb") as file:
        file.write(file_content)

    # PILLOW
    img = Image.open(generated_name)
    img = img.resize(size=(200, 200))
    img.save(generated_name)

    file.close()

    business = await Business.get(owner=user)
    owner = await business.owner

    if owner == user:
        business.logo = token_name
        await business.save()

    else:
        return UnauthorizedUpdate(detail="Not authenticated   to perform this action or invalid user input",
                                  status_code=status.HTTP_403_FORBIDDEN)

    file_url = "https://e-commerce-api-7osv.onrender.com/" + generated_name[1:]

    return {"status": "ok", "filename": file_url}


@app.post("/uploadfile/products/{id}")
async def create_upload_file(id: int, file: UploadFile = File(...),
                             user: user_pydantic = Depends(get_current_user)):
    FILEPATH = "./static/images"
    filename = file.filename
    extension = filename.split(".")[1]  # Getting extension

    if extension not in ["png", "jpg"]:
        return {"status": "Error", "detail": "File extension not supported"}

    token_name = secrets.token_hex(10) + "." + extension

    generated_name = FILEPATH + token_name
    file_content = await file.read()

    with open(generated_name, "wb") as file:
        file.write(file_content)

    # PILLOW
    img = Image.open(generated_name)
    img = img.resize(size=(200, 200))
    img.save(generated_name)

    file.close()

    product = await Product.get(id=id)
    business = await product.business
    owner = await business.owner

    if owner == user:
        product.product_image = token_name
        await product.save()

    else:
        return UnauthorizedUpdate(detail="Not authenticated to perform this action or invalid user input",
                                  status_code=status.HTTP_403_FORBIDDEN)


# CRUD functionality
@app.post("/products")
async def add_new_product(product: product_pydanticIn,
                          user: user_pydantic = Depends(get_current_user)):
    product = product.dict(exclude_unset=True)

    # to avoid division error by zero
    if product["original_price"] > 0:
        product["percentage_discount"] = ((product["original_price"] - product["new_price"]) / product[
            "original_price"]) * 100

        product_obj = await Product.create(**product, business=user)
        product_obj = await product_pydantic.from_tortoise_orm(product_obj)

        return {"status": "ok", "data": product_obj}


    else:
        return {"status": "error"}


@app.get("/product")
async def get_product():
    response = await product_pydantic.from_queryset(Product.all())
    return {"status": "ok", "data": response}


@app.get("/product/{id}")
async def get_product(id: int):
    product = await Product.get(id=id)
    business = await product.business
    owner = await business.owner
    response = await product_pydantic.from_queryset_single(Product.get(id=id))
    return {"status": "ok",
            "data": {
                "product_details": response,
                "business_details": {
                    "name": business.business_name,
                    "city": business.city,
                    "region": business.region,
                    "description": business.business_description,
                    "logo": business.logo,
                    "owner_id": owner.id,
                    "business_id": business.id,
                    "email": owner.email_id,
                    "join_date": owner.join_date.strftime("%b %d %Y")

                }
            }
            }


@app.delete("/product/{id}")
async def delete_product(id: int, user: user_pydantic = Depends(get_current_user)):
    product = await Product.get(id=id)
    business = await product.business
    owner = await business.owner

    if user == owner:
        await product.delete()


    else:
        return UnauthorizedUpdate(detail="Not authenticated to perform this action or invalid user input",
                                  status_code=status.HTTP_403_FORBIDDEN)

    return {
        "status": "ok"
    }


@app.put("/product/{id}")
async def update_product(id: int,
                         update_info: product_pydanticIn,
                         user: user_pydantic = Depends(get_current_user)):
    product = await Product.get(id=id)
    business = await product.business
    owner = await business.owner

    update_info = update_info.dict(exclude_unset=True)
    update_info["date_published"] = datetime.utcnow()

    if user == owner and update_info["original_price"] > 0:
        update_info["percentage_discount"] = ((update_info["original_price"] -
                                               update_info["new_price"]) / update_info["original_price"]) * 100

        product = await product.update_from_dict(update_info)
        await product.save()
        response = await product_pydantic.from_tortoise_orm(product)

        return {"status": "ok", "data": response}


    else:
        # raise Exception(
        #     status.HTTP_401_UNAUTHORIZED,
        #     "Not authenticated   to perform this action or invalid user input",
        #     {"WWW-Authenticate": "Bearer"}
        # )
        return UnauthorizedUpdate(detail="Not authenticated to perform this action or invalid user input",
                                  status_code=status.HTTP_403_FORBIDDEN)


@app.put("/business/{id}")
async def update_business(id: int,
                          update_business: business_pydanticIn,
                          user: user_pydantic = Depends(get_current_user)):
    update_business = update_business.dict()

    business = await Business.get(id=id)
    business_owner = await business.owner

    if user == business_owner:
        await business.update_from_dict(update_business)
        await business.save()
        response = await business_pydantic.from_tortoise_orm(business)
        return {"status": "ok",
                "data": response}

    else:
        return UnauthorizedUpdate(detail="Not authenticated to perform this action",
                                  status_code=status.HTTP_403_FORBIDDEN)


register_tortoise(
    app,
    db_url="sqlite://database.sqlite3",
    modules={"models": ["models"]},
    generate_schemas=True,
    add_exception_handlers=True
)
