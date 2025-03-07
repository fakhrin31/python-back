from motor.motor_asyncio import AsyncIOMotorClient
import os
from dotenv import load_dotenv

# Memuat variabel dari file .env
load_dotenv()

# Mengambil nilai variabel dari .env
MONGO_URI = os.getenv("MONGO_URI")
DB = os.getenv("DB_NAME")
SECRET_KEY = os.getenv("SECRET_KEY")
DEBUG = os.getenv("DEBUG")

# Inisialisasi Koneksi
client = AsyncIOMotorClient(MONGO_URI)
db = client[DB]

# Koleksi
users_collection = db["users"]
tasks_collection = db["tasks"]