from fastapi import FastAPI
from tortoise import Model


app = FastAPI()

@app.get("/")
async def root():
    return {"Hello": "World"}
