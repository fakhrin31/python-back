from datetime import datetime
from fastapi import FastAPI, HTTPException, Request, Depends
from fastapi.responses import JSONResponse
from pydantic import BaseModel, EmailStr
from typing import List, Optional, Callable

# HTTPException → Untuk menangani error dengan kode status HTTP.
# Request → Untuk menangani request HTTP dalam middleware.
# Depends → Untuk dependency injection (bisa untuk middleware per route).
# JSONResponse → Untuk mengembalikan respons dalam format JSON.
# BaseModel dan EmailStr dari pydantic → Untuk validasi data input.
# List, Optional dari typing → Untuk menentukan tipe data dalam list dan parameter opsional.

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

# middleware local
# async def local_middleware(request: Request, call_next):
#     print(f"Local middleware executed for: {request.url.path}")
#     response = await call_next(request)
#     return response

# Model untuk User
class User(BaseModel):
    id: int
    name: str
    email: EmailStr
    password: str
    role: str
    isActived: bool = True
class UserBody(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str
    isActived: Optional[bool] = True

# Model untuk Task
class Task(BaseModel):
    id: float
    title: str
    description: str
    user_id: float
    completed: bool = False

class TaskBody(BaseModel):
    title: str
    description: str
    user_id: float
    completed: Optional[bool] = False

users = []
tasks = []

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

# users route

@app.get("/users")
def get_users():
    return {
        "success": True,
        "status": 200,
        "data": users
    }
    
@app.get("/users/{user_id}", response_model=User)
def get_user(user_id: float):
    for user in users:
        if user["id"] == user_id:
            return user
    #menangani kesalahan dengan mengembalikan respons HTTP dengan status 404 (Not Found) ketika data yang diminta tidak ditemukan.
    #raise - menghentikan eksekusi
    raise HTTPException(status_code=404, detail="User not found")

@app.post("/users")
def create_user(body: UserBody):
    # Validasi jika email sudah digunakan
    for existing_user in users:
        if existing_user['email'] == body.email:
            return JSONResponse(status_code=400, content={
                "success": False,
                "status": 400,
                "message": "Email already exists",
            })

    # Tambahkan user baru dengan ID unik
    new_user = body.dict()
    now = datetime.now()
    new_user['id'] = now.timestamp() # pakai timestamp
    users.append(new_user)
    return {
        "success": True,
        "status": 201,
        "message": "User created successfully",
    }

@app.put("/users/{user_id}")
def update_user(user_id: float, body: UserBody):
    for user in users:
        if user["id"] == user_id:
            user.update(body.dict())
            return {"message": "User updated successfully", "user": user}
    raise HTTPException(status_code=404, detail="User not found")

@app.patch("/users/{user_id}/deactivate")
def deactivate_user(user_id: float):
    for user in users:
        if user["id"] == user_id:
            user["isActived"] = False
            return {"message": "User deactivated successfully", "user": user}
    raise HTTPException(status_code=404, detail="User not found")

@app.delete("/users/{user_id}")
def delete_user(user_id: float):
    global users
    for user in users:
        if user["id"] == user_id:
            users.remove(user)
            return {"message": "User deleted successfully"}
    raise HTTPException(status_code=404, detail="User not found")

# Task Routes
# @app.get("/tasks", response_model=List[Task])
# async def get_tasks(request: Request, middleware=Depends(local_middleware)):
#     return tasks

@app.get("/tasks", response_model=List[Task])
def get_tasks():
    return tasks

@app.get("/tasks/{task_id}", response_model=Task)
def get_task(task_id: float):
    for task in tasks:
        if task["id"] == task_id:
            return task
    raise HTTPException(status_code=404, detail="Task not found")

@app.post("/tasks", status_code=201)
def create_task(body: TaskBody):
    for user in users:
        if user["id"] == body.user_id:
            new_task = body.dict()
            new_task["id"] = datetime.now().timestamp()
            tasks.append(new_task)
            return {"message": "Task created successfully", "task": new_task}
    raise HTTPException(status_code=400, detail="Invalid user ID")

@app.put("/tasks/{task_id}")
def update_task(task_id: float, body: TaskBody):
    for task in tasks:
        if task["id"] == task_id:
            task.update(body.dict())
            return {"message": "Task updated successfully", "task": task}
    raise HTTPException(status_code=404, detail="Task not found")

@app.patch("/tasks/{task_id}/complete")
def complete_task(task_id: float):
    for task in tasks:
        if task["id"] == task_id:
            task["completed"] = True
            return {"message": "Task marked as completed", "task": task}
    raise HTTPException(status_code=404, detail="Task not found")

@app.delete("/tasks/{task_id}")
def delete_task(task_id: float):
    global tasks
    for task in tasks:
        if task["id"] == task_id:
            tasks.remove(task)
            return {"message": "Task deleted successfully"}
    raise HTTPException(status_code=404, detail="Task not found")


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)