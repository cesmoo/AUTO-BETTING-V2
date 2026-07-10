import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB Connection String (Local သို့မဟုတ် Atlas)
MONGO_URI = os.getenv("MONGO_URI", "")

# Database & Collection သတ်မှတ်ခြင်း
client = AsyncIOMotorClient(MONGO_URI)
db = client["autobet_db"]
users_collection = db["users"]

async def get_user(user_id: int):
    """User ၏ Data များကို ယူရန်"""
    return await users_collection.find_one({"_id": user_id})

async def save_user_login(user_id: int, phone: str, site_user_id: str, nickname: str, balance: str, login_time: str, ai_mode: str):
    """Login အောင်မြင်ပါက User Data များကို သိမ်းဆည်း/Update လုပ်ရန်"""
    await users_collection.update_one(
        {"_id": user_id},
        {"$set": {
            "phone": phone,
            "user_id": site_user_id,
            "nickname": nickname,
            "balance": balance,
            "last_login": login_time,
            "ai_mode": ai_mode
        }},
        upsert=True
    )

async def update_user_ai_mode(user_id: int, ai_mode: str):
    """User ရွေးချယ်ထားသော AI Mode ကို သိမ်းဆည်းရန်"""
    await users_collection.update_one(
        {"_id": user_id},
        {"$set": {"ai_mode": ai_mode}},
        upsert=True
    )

async def update_user_balance(user_id: int, balance: str):
    """User ၏ Balance ကို Update လုပ်ရန်"""
    await users_collection.update_one(
        {"_id": user_id},
        {"$set": {"balance": balance}},
        upsert=True
    )
