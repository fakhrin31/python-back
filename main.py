from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, Header, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from db import users_collection, tasks_collection

# HTTPException → Untuk menangani error dengan kode status HTTP.
# Request → Untuk menangani request HTTP dalam middleware.
# Depends → Untuk dependency injection (bisa untuk middleware per route).
# JSONResponse → Untuk mengembalikan respons dalam format JSON.
# BaseModel dan EmailStr dari pydantic → Untuk validasi data input.
# List, Optional dari typing → Untuk menentukan tipe data dalam list dan parameter opsional.
# motor, driver untuk asinkron dengan mongodb.
# ObjectId, mengubah id menjadi objectid agar bisa disimpan di mongodb.

app = FastAPI()

# Middleware global untuk logging
# setiap request yang masuk ke server akan melewati middleware ini sebelum mencapai route yang dituju.
@app.middleware("http") 
# Middleware akan menangkap semua request yang masuk
async def log_requests(request: Request, call_next):
    # mencetak log request dengan metode HTTP dan URL
    print(f"Incoming request: {request.method} {request.url}")
    # meneruskan request ke route yang sesuai
    response = await call_next(request)
    return response

# Model untuk User
class User(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str
    isActived: bool = True

# Model untuk Task
class Task(BaseModel):
    title: str
    description: str
    user_id: str
    completed: bool = False
    
# {Users}
# id (wajib) (primary key)
# name (varchar)
# email (unique)
# password (text)
# role (varchar)

@app.get("/")
def read_root():
    return {"Hello": "Backend"}

@app.get("/about")
def about():
    return {"message": "About Me: This is my personal website."}

@app.get("/contact")
def contact():
    return {"message": "Contact Me: example@email.com"}

@app.get("/aritmatic")
def add_numbers(a: float, b: float):
    result = a + b
    return {"a": a, "b": b, "sum": result}

# @app.get("/test-mongo")
# async def test_mongo():
#     try:
#         await db.command("ping")
#         return {"message": "MongoDB Connected!"}
#     except Exception as e:
#         return {"error": str(e)}

# -------------------------
# CRUD Users dengan MongoDB
# -------------------------
@app.get("/users")
async def get_users():
    users = await users_collection.find().to_list(100)
    for user in users:
        user["_id"] = str(user["_id"])  # Ubah ObjectId ke string
    return users

@app.get("/users/{user_id}")
async def get_user(user_id: str):
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    #menangani kesalahan dengan mengembalikan respons HTTP dengan status 404 (Not Found) ketika data yang diminta tidak ditemukan.
    if not user:
        raise HTTPException(status_code=404, detail="User not found") #raise - menghentikan eksekusi
    
    user["_id"] = str(user["_id"])  # Konversi `_id` ke string
    return user


@app.post("/users", status_code=201)
async def create_user(body: User):
    existing_user = await users_collection.find_one({"email": body.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")
    
    new_user = body.dict()
    new_user["_id"] = ObjectId()  # membuat _id ObjectId agar bisa disimpan ke mongodb

    await users_collection.insert_one(new_user)
    
    # Konversi `_id` ke string agar bisa dikembalikan dalam response JSON
    new_user["_id"] = str(new_user["_id"])
    
    return {"message": "User created successfully", "user": new_user}

@app.put("/users/{user_id}")
async def update_user(user_id: str, body: User):
    result = await users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": body.dict()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User updated successfully"}

@app.patch("/users/{user_id}/deactivate")
async def complete_user(user_id: str):
    result = await users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": {"isActived": False}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User is Deactivated"}


@app.delete("/users/{user_id}")
async def delete_user(user_id: str):
    result = await users_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}

# -------------------------
# CRUD Tasks dengan MongoDB
# -------------------------

@app.get("/tasks")
async def get_tasks():
    tasks = await tasks_collection.find().to_list(100) #fungsi untuk mencari semua data dalam list
    for task in tasks:
        task["_id"] = str(task["_id"])  # Ubah ObjectId ke string agar dapat ditampilkan
    return tasks

@app.get("/tasks/user/{user_id}")
async def get_tasks_by_user(user_id: str):
    try:
        #mencari semua data tasks berdasarkan user_id dalam format ObjectId
        user_tasks = await tasks_collection.find({"user_id": user_id}).to_list(100)

        if not user_tasks:
            raise HTTPException(status_code=404, detail="No tasks found for this user")

        # Konversi _id dari ObjectId ke string sebelum dikembalikan
        for task in user_tasks:
            task["_id"] = str(task["_id"])

        return user_tasks

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/tasks", status_code=201)
async def create_task(body: Task):
    new_task = body.dict()
    new_task["_id"] = ObjectId()  # membuat _id menjadi ObjectId agar bisa disimpan ke mongodb

    await tasks_collection.insert_one(new_task)     
    
    # Konversi `_id` ke string agar bisa dikembalikan dalam response JSON
    new_task["_id"] = str(new_task["_id"])
    
    return {"message": "Task created successfully", "task": new_task}

@app.put("/tasks/{task_id}")
async def update_task(task_id: str, body: Task):
    #mencari semua data tasks berdasarkan user_id dalam format ObjectId
    result = await tasks_collection.update_one({"_id": ObjectId(task_id)}, {"$set": body.dict()})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task updated successfully"}

@app.patch("/tasks/{task_id}/complete")
async def complete_task(task_id: str):
    result = await tasks_collection.update_one({"_id": ObjectId(task_id)}, {"$set": {"completed": True}})
    if result.matched_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task marked as completed"}

@app.delete("/tasks/{task_id}")
async def delete_task(task_id: str):
    result = await tasks_collection.delete_one({"_id": ObjectId(task_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"message": "Task deleted successfully"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)