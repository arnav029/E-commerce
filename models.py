from fastapi import FastAPI
from tortoise import Model,fields
from datetime import datetime
import pydantic
from tortoise.contrib.pydantic import pydantic_model_creator


class User(Model):
    id = fields.IntField(pk = True, index = True)
    username = fields.CharField(max_length=20, null=False, unique=True)
    email_id = fields.CharField(max_length=200, null=False, unique=True)
    password = fields.CharField(max_length=100, null=False)
    is_verified = fields.BooleanField(default=False, null=False)
    join_date = fields.DatetimeField(default=datetime.utcnow)


class Business(Model):
    id = fields.IntField(pk = True, index = True)
    business_name = fields.CharField(max_length=20, null=False, unique=True)
    city = fields.CharField(max_length=100, null=False, default = "unspecified")
    region = fields.CharField(max_length=100, null=False, default = "unspecified")
    business_description = fields.BooleanField(null = True)
    logo = fields.CharField(max_length=200, null=False, default= "default.jpg")
    owner = fields.ForeignKeyField("models.User", related_name="business")


class Product(Model):
    id = fields.IntField(pk = True, index = True)
    name = fields.CharField(max_length=100, null=False, index=True)
    category = fields.CharField(max_length=30, index=True)
    original_price = fields.DecimalField(max_digits=10, decimal_places=2)
    percentage_discount = fields.IntField()
    offer_expiration = fields.IntField()
    product_image = fields.CharField(max_length=200, null=False, default="productDefault.jpg")
    business = fields.ForeignKeyField("models.Business", related_name="product")


user_pydantic = pydantic_model_creator(User, name = "User", exclude = ("is_verified", ))
user_pydanticIn = pydantic_model_creator(User, name = "UserIn", exclude_readonly=True, exclude=("is_verified", "join_date"))
user_pydanticOut = pydantic_model_creator(User, name = "UserOut", exclude=("password", ))

business_pydantic = pydantic_model_creator(Business, name = "Business")
business_pydanticIn = pydantic_model_creator(Business, name = "BusinessIn", exclude_readonly=True)

product_pydantic = pydantic_model_creator(Product, name = "Product")
product_pydanticIn = pydantic_model_creator(Product, name = "ProductIn", exclude=("percentage_discount", "id") )
