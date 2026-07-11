import os
from motor.motor_asyncio import AsyncIOMotorClient
from dotenv import load_dotenv

load_dotenv()

# MongoDB Connection String
MONGO_URI = os.getenv("MONGO_URI", "")

# Database & Collection သတ်မှတ်ခြင်း
client = AsyncIOMotorClient(MONGO_URI)
db = client["autobet_db"]
users_collection = db["users"]
keys_collection = db["keys"] # Key များသိမ်းရန် Collection အသစ်

# ==========================================
# 👤 User Data Functions
# ==========================================
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

# ==========================================
# 🔑 Auth & Subscription Functions
# ==========================================
async def create_key(key_str: str, duration: str):
    """Owner ထုတ်လိုက်သော Key ကို DB တွင်သိမ်းရန်"""
    await keys_collection.insert_one({"key": key_str, "duration": duration})

async def get_key(key_str: str):
    """Key အချက်အလက်ကို ဆွဲယူရန်"""
    return await keys_collection.find_one({"key": key_str})

async def delete_key(key_str: str):
    """အသုံးပြုပြီးသော Key ကို ဖျက်ရန်"""
    await keys_collection.delete_one({"key": key_str})

async def update_user_subscription(user_id: int, expire_iso: str):
    """User ၏ အသုံးပြုခွင့် သက်တမ်းကို Update လုပ်ရန်"""
    await users_collection.update_one(
        {"_id": user_id},
        {"$set": {"expire_date": expire_iso}},
        upsert=True
    )

async def get_user_subscription(user_id: int):
    """User ၏ သက်တမ်းကုန်ဆုံးမည့် အချိန်ကို ယူရန်"""
    user = await get_user(user_id)
    if user and "expire_date" in user:
        return user["expire_date"]
    return None
