from fastapi import (BackgroundTasks, UploadFile, File, Form, UploadFile, FastAPI,
                     HTTPException, status)

from fastapi_mail import FastMail, MessageSchema, ConnectionConfig
from dotenv import dotenv_values
from pydantic import BaseModel, EmailStr
from typing import List
from models import User
import jwt


config_credentials = dotenv_values(".env")


conf = ConnectionConfig(
    MAIL_USERNAME=config_credentials["EMAIL"],
    MAIL_PASSWORD=config_credentials["PASS"],
    MAIL_FROM=config_credentials["EMAIL"],
    MAIL_PORT=587,
    MAIL_SERVER="smtp.gmail.com",
    # MAIL_FROM_NAME="",
    # MAIL_TLS=True,
    # MAIL_SSL=False,
    MAIL_STARTTLS=True,
    MAIL_SSL_TLS=False,
    USE_CREDENTIALS=True
)


class EmailSchema(BaseModel):
    email: List[EmailStr]


async def send_email(email: EmailSchema, instance="User"):

    token_data = {
        "id": instance.id,
        "username": instance.username
    }

    token = jwt.encode(token_data, config_credentials["SECRET"])
    print(f"This is token {token}")

    template = f"""
<!DOCTYPE html>
<html>
<head>
</head>
<body style="font-family: sans-serif; margin: 0; display: flex; justify-content: center; align-items: center; min-height: 100vh; background-color: #f5f5f5;">
<div style="background-color: white; padding: 30px; border-radius: 5px; text-align: center;">
  <h3>Account Verification</h3>
  <br>
  <p>
    Thanks for choosing Oceanore, please click on the button below to verify your account.
  </p>
  <a href="https://e-commerce-api-7osv.onrender.com//verification/?token={token}" style="display: inline-block; padding: 10px 20px; border-radius: 5px; color: white; text-decoration: none; font-weight: bold; background-color: #0275d8; transition: all 0.2s ease-in-out;">Verify your email</a>
  <p>
    Please kindly ignore this email if you did not register for Oceanore. Thanks.
  </p>
</div>
</body>
</html>

    
    """

    message = MessageSchema(
        subject="Oceanore Account Verification Email",
        recipients=email,
        body=template,
        subtype="html"
    )

    fm = FastMail(conf)
    await fm.send_message(message= message)




