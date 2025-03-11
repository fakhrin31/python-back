from datetime import datetime, timedelta
from fastapi import FastAPI, HTTPException, Request, Header, Depends
from fastapi.responses import JSONResponse
from fastapi.security import OAuth2PasswordBearer, OAuth2PasswordRequestForm
from pydantic import BaseModel, EmailStr, constr
from typing import List, Optional
from motor.motor_asyncio import AsyncIOMotorClient
from bson import ObjectId
from jose import JWTError, jwt
from db import users_collection, tasks_collection
from passlib.context import CryptContext  # Hashing password

# HTTPException → Untuk menangani error dengan kode status HTTP.
# Request → Untuk menangani request HTTP dalam middleware.
# Depends → Untuk dependency injection (bisa untuk middleware per route).
# JSONResponse → Untuk mengembalikan respons dalam format JSON.
# BaseModel dan EmailStr dari pydantic → Untuk validasi data input.
# List, Optional dari typing → Untuk menentukan tipe data dalam list dan parameter opsional.
# motor, driver untuk asinkron dengan mongodb.
# ObjectId, mengubah id menjadi objectid agar bisa disimpan di mongodb.

# Konfigurasi JWT
SECRET_KEY = "your_secret_key_here"
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30

#menangani autentikasi menggunakan OAuth2 dengan skema Bearer Token
oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/token")

# Konfigurasi hashing password
pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

app = FastAPI()

# Middleware global untuk logging dan error handling
@app.middleware("http")
async def log_requests(request: Request, call_next):
    try:
        print(f"Incoming request: {request.method} {request.url}")
        response = await call_next(request)
        return response
    except Exception as e:
        return JSONResponse(status_code=500, content={"detail": "Internal Server Error", "error": str(e)})


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

class Token(BaseModel):
    access_token: str
    token_type: str

# Fungsi hashing dan verifikasi password
def hash_password(password: str) -> str: #mengenkripsi atau meng-hash password sebelum disimpan ke database.
    return pwd_context.hash(password)

#memeriksa apakah password yang dimasukkan oleh pengguna sesuai dengan password yang telah di-hash dan disimpan di database.
def verify_password(plain_password: str, hashed_password: str) -> bool:
    return pwd_context.verify(plain_password, hashed_password)

# membuat JSON Web Token (JWT) yang digunakan untuk autentikasi pengguna.
def create_access_token(data: dict, expires_delta: timedelta | None = None):
    to_encode = data.copy()
    # menentukan waktu kadaluarsa token
    expire = datetime.utcnow() + (expires_delta if expires_delta else timedelta(minutes=15))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

# autentikasi setiap pengguna berdasarkan token JWT
async def get_current_user(token: str = Depends(oauth2_scheme)):
    credentials_exception = HTTPException(
        status_code=401,
        detail="Invalid or expired token",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # mendapatkan payload dari token
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email: str = payload.get("sub")
        if email is None:
            raise credentials_exception

        # Ambil user berdasarkan email dari token
        user = await users_collection.find_one({"email": email})
        if user is None:
            raise credentials_exception

        return user
    
    except JWTError:
        raise credentials_exception

# membatasi akses ke endpoint berdasarkan peran (role) pengguna.
def check_role(required_roles: List[str]):
    def role_checker(user: dict = Depends(get_current_user)):
        # memeriksa apakah pengguna ada dalam role
        if user["role"] not in required_roles:
            raise HTTPException(status_code=403, detail="Access forbidden")
        return user
    return role_checker

@app.post("/token", response_model=Token)
async def login_for_access_token(form_data: OAuth2PasswordRequestForm = Depends()):
    # """ Login user dan buat token JWT """
    user = await users_collection.find_one({"email": form_data.username})
    
    # memeriksa password yang sebelumnya dihash
    if not user or not verify_password(form_data.password, user["password"]):
        raise HTTPException(status_code=401, detail="Incorrect email or password")
    
    access_token = create_access_token({"sub": user["email"]}, timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES))
    
    return {"access_token": access_token, "token_type": "bearer"}

@app.post("/users", status_code=201)
async def create_user(body: User):
    # """ Buat user baru dengan password yang di-hash """
    existing_user = await users_collection.find_one({"email": body.email})
    if existing_user:
        raise HTTPException(status_code=400, detail="Email already exists")

    new_user = body.dict()
    new_user["password"] = hash_password(new_user["password"])  # Hash password sebelum disimpan
    new_user["_id"] = ObjectId()  # membuat _id ObjectId agar bisa disimpan ke mongodb

    await users_collection.insert_one(new_user)
    # Konversi `_id` ke string agar bisa dikembalikan dalam response JSON
    new_user["_id"] = str(new_user["_id"])

    return {"message": "User created successfully", "user": new_user}

@app.get("/users/me")
async def read_users_me(current_user: dict = Depends(get_current_user)):
    return {"message": "Authenticated", "user": {"email": current_user["email"], "name": current_user["name"]}}

@app.get("/")
def read_root():
    return {"Hello": "Backend"}

# get user hanya bisa dilihat oleh role admin
@app.get("/users", dependencies=[Depends(check_role(["admin"]))])
async def get_users():
    users = await users_collection.find().to_list(100)
    for user in users:
        user["_id"] = str(user["_id"]) # Konversi `_id` ke string agar bisa dikembalikan dalam response JSON
    return users

@app.put("/users/{user_id}")
async def update_user(user_id: str, update_data: dict, current_user: dict = Depends(get_current_user)):
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Cek apakah user yang login adalah yang punya data atau admin
    if current_user["email"] != user["email"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized")

    await users_collection.update_one({"_id": ObjectId(user_id)}, {"$set": update_data})
    return {"message": "User updated successfully"}


# PATCH: Nonaktifkan akun user
@app.patch("/users/{user_id}/deactivate")
async def deactivate_user(user_id: str, current_user: dict = Depends(get_current_user)):
    # Ambil data user berdasarkan ID
    user = await users_collection.find_one({"_id": ObjectId(user_id)})
    
    if not user:
        raise HTTPException(status_code=404, detail="User not found")

    # Hanya admin atau user itu sendiri yang bisa menonaktifkan akun
    if current_user["email"] != user["email"] and current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to deactivate this user")

    # Update status isActived menjadi False
    result = await users_collection.update_one(
        {"_id": ObjectId(user_id)},
        {"$set": {"isActived": False}}
    )

    if result.matched_count == 0:
        raise HTTPException(status_code=500, detail="Failed to deactivate user")

    return {"message": "User is Deactivated"}


@app.delete("/users/{user_id}")
async def delete_user(user_id: str, current_user: dict = Depends(get_current_user)):
    # Cek user adalah admin
    if current_user["role"] != "admin":
        raise HTTPException(status_code=403, detail="Not authorized to delete this user")

    result = await users_collection.delete_one({"_id": ObjectId(user_id)})
    if result.deleted_count == 0:
        raise HTTPException(status_code=404, detail="User not found")
    return {"message": "User deleted successfully"}

#------------------
# Crud Task

@app.post("/tasks", response_model=dict, dependencies=[Depends(check_role(["admin", "editor"]))])
async def create_task(task: Task, current_user: dict = Depends(get_current_user)):
    try:
        # Pastikan user_id yang dikirim sama dengan yang login
        if task.user_id != str(current_user["_id"]):
            raise HTTPException(status_code=403, detail="Not authorized to create task for this user")

        # Simpan task ke database
        new_task = await tasks_collection.insert_one(task.dict())

        # Pastikan task berhasil disimpan
        if not new_task.inserted_id:
            raise HTTPException(status_code=500, detail="Failed to create task")

        return {
            "message": "Task created successfully",
            "task_id": str(new_task.inserted_id)
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/tasks/{task_id}")
async def get_task(task_id: str, current_user: dict = Depends(get_current_user)):
    try:
        object_id = ObjectId(task_id)
    except:
        raise HTTPException(status_code=400, detail="Invalid task ID format")

    #mencari semua data tasks berdasarkan user_id dalam format ObjectId
    task = await tasks_collection.find_one({"_id": object_id, "user_id": str(current_user["_id"])})

    if not task:
        raise HTTPException(status_code=404, detail="Task not found or not authorized")

    # Konversi ObjectId ke string agar JSON bisa mengirimnya
    task["_id"] = str(task["_id"])
    task["user_id"] = str(task["user_id"])

    return task

@app.put("/tasks/{task_id}", dependencies=[Depends(check_role(["admin", "editor"]))])
async def update_task(task_id: str, updated_task: dict, current_user: dict = Depends(get_current_user)):
    try:
        task = await tasks_collection.find_one({"_id": ObjectId(task_id)})

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if task["user_id"] != current_user["_id"]:
            raise HTTPException(status_code=403, detail="Not authorized to update this task")

        await tasks_collection.update_one({"_id": ObjectId(task_id)}, {"$set": updated_task})
        return {"message": "Task updated"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.patch("/tasks/{task_id}/complete")
async def complete_task(task_id: str, current_user: dict = Depends(get_current_user)):
    try:
        task = await tasks_collection.find_one({"_id": ObjectId(task_id)})

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if task["user_id"] != current_user["_id"]:
            raise HTTPException(status_code=403, detail="Not authorized to complete this task")

        await tasks_collection.update_one({"_id": ObjectId(task_id)}, {"$set": {"status": "completed"}})
        return {"message": "Task marked as completed"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.delete("/tasks/{task_id}", dependencies=[Depends(check_role(["admin"]))])
async def delete_task(task_id: str, current_user: dict = Depends(get_current_user)):
    try:
        task = await tasks_collection.find_one({"_id": ObjectId(task_id)})

        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if task["user_id"] != current_user["_id"]:
            raise HTTPException(status_code=403, detail="Not authorized to delete this task")

        await tasks_collection.delete_one({"_id": ObjectId(task_id)})
        return {"message": "Task deleted"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
