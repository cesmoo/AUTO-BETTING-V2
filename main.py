[file name]: xxx.py
[file content begin]
import asyncio
import os
import html
import random
import aiohttp
import time
import re
import string
from datetime import datetime, timedelta
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F, BaseMiddleware
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import (
    FSInputFile, ReplyKeyboardMarkup, KeyboardButton, 
    ReplyKeyboardRemove, InlineKeyboardMarkup, InlineKeyboardButton
)

from playwright.async_api import async_playwright

# Database နှင့် AI ကို ချိတ်ဆက်ခြင်း
import database as db 
import ai_engines

# ==========================================================
# ⚙️ Configuration
# ==========================================================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = int(os.getenv("OWNER_ID", "0")) # .env တွင်ထည့်ရန်

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

active_sessions = {}

# ==========================================================
# 🌟 Premium Emojis for Keyboard
# ==========================================================
E_INFO = '<tg-emoji emoji-id="5971801057540443125">ℹ️</tg-emoji>'
E_BALANCE = '<tg-emoji emoji-id="5971801057540443125">💰</tg-emoji>'
E_STATUS = '<tg-emoji emoji-id="5971801057540443125">📊</tg-emoji>'
E_START = '<tg-emoji emoji-id="5971801057540443125">▶️</tg-emoji>'
E_STOP = '<tg-emoji emoji-id="5971801057540443125">🛑</tg-emoji>'
E_GAMES = '<tg-emoji emoji-id="5971801057540443125">🎰</tg-emoji>'
E_AI = '<tg-emoji emoji-id="5971801057540443125">🤖</tg-emoji>'
E_BETSIZE = '<tg-emoji emoji-id="5971801057540443125">⚙️</tg-emoji>'
E_PROFIT = '<tg-emoji emoji-id="5971801057540443125">🎯</tg-emoji>'
E_HIT = '<tg-emoji emoji-id="5971801057540443125">🎯</tg-emoji>'
E_PREDICT = '<tg-emoji emoji-id="5971801057540443125">🔮</tg-emoji>'
E_LOGOUT = '<tg-emoji emoji-id="5971801057540443125">🔐</tg-emoji>'
E_LOGIN = '<tg-emoji emoji-id="5971801057540443125">🔐</tg-emoji>'
E_BACK = '<tg-emoji emoji-id="5971801057540443125">🔙</tg-emoji>'

# ==========================================================
# 🛠️ Helper Functions
# ==========================================================
def extract_balance(bal_str: str) -> float:
    """String အနေဖြင့်ရလာသော Balance ကို ဂဏန်း(Float) အဖြစ်ပြောင်းပေးရန်"""
    try:
        clean_str = re.sub(r'[^\d.]', '', bal_str)
        if clean_str:
            return float(clean_str)
        else:
            return 0.0
    except Exception:
        return 0.0

async def delete_message_later(msg: types.Message, delay: int = 5):
    """သတ်မှတ်ထားသောအချိန်အကြာတွင် Message ကို အလိုအလျောက်ဖျက်ပေးမည်"""
    await asyncio.sleep(delay)
    try:
        await msg.delete()
    except Exception:
        pass

def parse_duration(duration_str: str):
    """'2H', '5D' စသည့် format များကို timedelta သို့ပြောင်းပေးရန်"""
    duration_str = duration_str.upper()
    if duration_str.endswith('H') and duration_str[:-1].isdigit():
        return timedelta(hours=int(duration_str[:-1]))
    elif duration_str.endswith('D') and duration_str[:-1].isdigit():
        return timedelta(days=int(duration_str[:-1]))
    return None

def get_myanmar_time() -> datetime:
    """Server Time အစား Myanmar Time (UTC+6:30) အတိအကျကို ယူရန်"""
    return datetime.utcnow() + timedelta(hours=6, minutes=30)

# ==========================================================
# 🛡️ Auth Middleware (သုံးခွင့်ရှိ/မရှိ စစ်ဆေးရေးဂိတ်)
# ==========================================================
class AuthMiddleware(BaseMiddleware):
    async def __call__(self, handler, event, data):
        user_id = None
        text = ""
        
        if isinstance(event, types.Message):
            user_id = event.from_user.id
            text = event.text or ""
        elif isinstance(event, types.CallbackQuery):
            user_id = event.from_user.id
            
        if user_id:
            # Owner ဆိုလျှင် အမြဲဖြတ်သန်းခွင့်ပေးမည်
            if user_id == OWNER_ID:
                return await handler(event, data)
            
            # Key 16 လုံးရိုက်ထည့်လျှင် ဖြတ်ခွင့်ပေးမည် (Key ရိုက်ထည့်နေစဉ် Block မဖြစ်စေရန်)
            if isinstance(event, types.Message) and len(text) == 16 and text[:8].isdigit() and text[8:].isupper():
                return await handler(event, data)
                
            # DB မှ သက်တမ်းစစ်ဆေးခြင်း
            expire_iso = await db.get_user_subscription(user_id)
            is_authorized = False
            
            if expire_iso:
                expire_time = datetime.fromisoformat(expire_iso)
                if get_myanmar_time() < expire_time:
                    is_authorized = True
            
            if not is_authorized:
                if isinstance(event, types.Message):
                    await event.answer(
                        "ᴄᴏɴᴛᴀᴄᴛ ᴜꜱ @iwillgoforwardsalone "
                    )
                elif isinstance(event, types.CallbackQuery):
                    await event.answer("အသုံးပြုခွင့် သက်တမ်းကုန်သွားပါပြီ။", show_alert=True)
                return 
        
        return await handler(event, data)

# Middleware ကို တပ်ဆင်ခြင်း
dp.message.middleware(AuthMiddleware())
dp.callback_query.middleware(AuthMiddleware())

# ==========================================================
# 🎡 AI Configuration
# ==========================================================
def circle_rnd_predict(history_docs):
    wheel = ["BIG", "SMALL", "BIG", "SMALL", "BIG", "SMALL", "BIG", "SMALL"]
    predicted = random.choice(wheel)
    if predicted == "BIG":
        emoji = "🔴"
    else:
        emoji = "🟢"
    confidence = round(random.uniform(50.0, 65.0), 1)
    
    name_str = "အကြီး" if predicted == "BIG" else "အသေး"
    return predicted, f"{predicted} ({name_str}) {emoji}", confidence, "🎡 Circle Rnd: Spinner"

ai_engines.AI_MODES["circle_rnd"] = {
    "func": circle_rnd_predict,
    "name": "🎡 Circle Rnd",
    "desc": "Random Wheel Spin"
}

VALID_AI_NAMES = [m["name"] for m in ai_engines.AI_MODES.values()]

# ==========================================================
# 🗂️ FSM States
# ==========================================================
class LoginForm(StatesGroup):
    select_site = State()
    enter_phone = State()
    enter_password = State()
    main_menu = State()
    enter_bet_sequence = State() 
    enter_profit_target = State()

# ==========================================================
# ⌨️ Keyboards
# ==========================================================
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=f"{E_LOGIN} Login")], 
            [KeyboardButton(text=f"{E_GAMES} Games")]
        ],
        resize_keyboard=True
    )

def get_site_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="𝟳𝟳𝟳𝗕𝗜𝗚𝗪𝗜𝗡"), KeyboardButton(text="𝗦𝗜𝗫 𝗟𝗢𝗧𝗧𝗘𝗥𝗬")], 
            [KeyboardButton(text=f"{E_BACK} နောက်သို့")]
        ],
        resize_keyboard=True
    )

def get_logged_in_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text=f"{E_INFO} Info"), KeyboardButton(text=f"{E_BALANCE} Balance"), KeyboardButton(text=f"{E_STATUS} Status")], 
            [KeyboardButton(text=f"{E_START} Start Auto-Bet"), KeyboardButton(text=f"{E_STOP} Stop Auto-Bet")],
            [KeyboardButton(text=f"{E_GAMES} Games"), KeyboardButton(text=f"{E_AI} AI Mode")],
            [KeyboardButton(text=f"{E_BETSIZE} Set Bet-Size"), KeyboardButton(text=f"{E_PROFIT} Profit Target")], 
            [KeyboardButton(text=f"{E_HIT} Hit Betting"), KeyboardButton(text=f"{E_PREDICT} AI Prediction")],
            [KeyboardButton(text=f"{E_LOGOUT} Logout")]
        ],
        resize_keyboard=True
    )

def get_ai_mode_keyboard():
    modes = list(ai_engines.AI_MODES.values())
    keyboard = []
    row = []
    for mode in modes:
        row.append(KeyboardButton(text=mode["name"]))
        if len(row) == 2:
            keyboard.append(row)
            row = []
    if row: 
        keyboard.append(row)
    keyboard.append([KeyboardButton(text=f"{E_BACK} ပင်မမီနူးသို့")])
    return ReplyKeyboardMarkup(keyboard=keyboard, resize_keyboard=True)

def get_hit_betting_inline_keyboard(current_wait: int = 0):
    keyboard = []
    number_buttons = []
    for i in range(1, 10):
        if current_wait == i:
            btn_style = "success"
        else:
            btn_style = "primary"
        number_buttons.append(
            InlineKeyboardButton(text=str(i), callback_data=f"hitbet_{i}", style=btn_style)
        )
        
    for i in range(0, 9, 3): 
        keyboard.append(number_buttons[i:i+3])
        
    if current_wait == 0:
        disable_text = "0 (Disabled)"
    else:
        disable_text = "0 (Disable)"
        
    keyboard.append([
        InlineKeyboardButton(text=disable_text, callback_data="hitbet_0", style="danger")
    ])
    return InlineKeyboardMarkup(inline_keyboard=keyboard)

def get_ai_prediction_toggle_keyboard(is_enabled: bool):
    if is_enabled:
        btn = InlineKeyboardButton(text="🟢 Enabled", callback_data="toggle_aipred", style="success")
    else:
        btn = InlineKeyboardButton(text="🔴 Disabled", callback_data="toggle_aipred", style="danger")
    return InlineKeyboardMarkup(inline_keyboard=[[btn]])

def get_cancel_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="Cancel")]], 
        resize_keyboard=True
    )

# ==========================================================
# 👑 Owner Commands (.key & .add)
# ==========================================================
@dp.message(F.text.startswith(".key "))
async def cmd_generate_key(message: types.Message):
    if message.from_user.id != OWNER_ID: 
        return
    
    parts = message.text.split(" ")
    if len(parts) < 2:
        return await message.answer("⚠️ Format မှားနေပါသည်။\nအသုံးပြုရန်: <code>.key 2H</code>, <code>.key 5D</code>")
        
    duration = parts[1].strip().upper()
    if not parse_duration(duration):
        return await message.answer("⚠️ အချိန်သတ်မှတ်ချက် မှားနေပါသည်။\nဂဏန်းနောက်တွင် H (နာရီ) သို့မဟုတ် D (ရက်) ထည့်ပါ။\nဥပမာ: <code>2H</code>, <code>5D</code>, <code>15D</code>")
    
    date_prefix = get_myanmar_time().strftime("%Y%m%d")
    random_str = ''.join(random.choices(string.ascii_uppercase, k=8))
    key_str = f"{date_prefix}{random_str}"
    
    await db.create_key(key_str, duration)
    
    await message.answer(
        f"✅ <b>Key အသစ် ဖန်တီးပြီးပါပြီ။</b>\n\n"
        f"🔑 Key: <code>{key_str}</code>\n"
        f"⏱️ Duration: <b>{duration}</b>\n\n"
        f"(User အား အပေါ်က Key လေးကို Copy ကူးပေးလိုက်ပါ။)"
    )

@dp.message(F.text.startswith(".add "))
async def cmd_add_user(message: types.Message):
    if message.from_user.id != OWNER_ID: 
        return
    
    parts = message.text.split(" ")
    if len(parts) < 3:
        return await message.answer("⚠️ Format မှားနေပါသည်။\nအသုံးပြုရန်: <code>.add [Telegram_ID] [Duration]</code>\nဥပမာ: <code>.add 123456789 2D</code>")
        
    target_id = parts[1].strip()
    duration = parts[2].strip().upper()
    
    td = parse_duration(duration)
    if not td: 
        return await message.answer("⚠️ Duration မှားနေပါသည်။ (ဂဏန်းနောက်တွင် H သို့မဟုတ် D ထည့်ပါ။ ဥပမာ: 2H, 5D)")
    
    new_expire = get_myanmar_time() + td
    await db.update_user_subscription(int(target_id), new_expire.isoformat())
    
    await message.answer(
        f"✅ User ID: <code>{target_id}</code> ကို <b>{duration}</b> စာ အသုံးပြုခွင့် ပေးလိုက်ပါပြီ။\n"
        f"ကုန်ဆုံးမည့်အချိန်: {new_expire.strftime('%Y-%m-%d %I:%M %p')} (MMT)"
    )

# ==========================================================
# 🔑 User Key Redemption Handler
# ==========================================================
@dp.message(lambda msg: msg.text and len(msg.text) == 16 and msg.text[:8].isdigit() and msg.text[8:].isupper())
async def process_key_redemption(message: types.Message):
    key_str = message.text.strip()
    key_data = await db.get_key(key_str)
    
    if key_data:
        duration = key_data["duration"]
        td = parse_duration(duration)
        if not td: 
            td = timedelta(days=1)
        
        user_id = message.from_user.id
        current_expire = get_myanmar_time()
        
        existing_expire_iso = await db.get_user_subscription(user_id)
        if existing_expire_iso:
            old_expire = datetime.fromisoformat(existing_expire_iso)
            if old_expire > get_myanmar_time():
                current_expire = old_expire
                
        new_expire = current_expire + td
        await db.update_user_subscription(user_id, new_expire.isoformat())
        
        # 1 Key One Time (အသုံးပြုပြီးပါက ဖျက်မည်)
        await db.delete_key(key_str)
        
        await message.answer(
            f"ʟɪᴄᴇɴꜱᴇ ᴋᴇʏ ᴀᴄᴛɪᴠᴇ\n"
            f"ᴇxᴘɪʀᴇ ᴛɪᴍᴇ <b>{new_expire.strftime('%Y-%m-%d %I:%M %p')}</b> (MMT) \n"
            f"ᴄʟɪᴄᴋ /start ᴛᴏ ᴘʟᴀʏ."
        )
    else:
        await message.answer("ɪɴᴄᴏʀʀᴇᴄᴛ ᴋᴇʏ ᴏʀ ᴋᴇʏ ɪꜱ ᴇxᴘɪʀᴇᴅ.")

# ==========================================================
# 🤖 Standard Bot Handlers
# ==========================================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("ᴄʟɪᴄᴋ ᴛᴏ ʟᴏɢɪɴ", reply_markup=get_main_keyboard())

@dp.message(F.text == f"{E_LOGIN} Login")
async def login_start(message: types.Message, state: FSMContext):
    await state.set_state(LoginForm.select_site)
    await message.answer("ᴘʟᴇᴀꜱᴇ ꜱᴇʟᴇᴄᴛ ᴀ ꜱɪᴛᴇ ᴛᴏ ʟᴏɢɪɴ", reply_markup=get_site_keyboard())

@dp.message(LoginForm.select_site)
async def process_site(message: types.Message, state: FSMContext):
    if message.text == f"{E_BACK} နောက်သို့":
        await state.clear()
        return await message.answer("Cancelled.", reply_markup=get_main_keyboard())
    await state.update_data(site=message.text)
    await state.set_state(LoginForm.enter_phone)
    await message.answer("ᴘʟᴇᴀꜱᴇ ᴇɴᴛᴇʀ ʏᴏᴜʀ ᴘʜᴏɴᴇ ɴᴜᴍʙᴇʀ", reply_markup=ReplyKeyboardRemove())

@dp.message(LoginForm.enter_phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(LoginForm.enter_password)
    await message.answer("ᴘʟᴇᴀꜱᴇ ᴇɴᴛᴇʀ ʏᴏᴜʀ ᴘᴀꜱꜱᴡᴏʀᴅ", reply_markup=ReplyKeyboardRemove())

# ==========================================================
# 🔥 Playwright Logic: Login & Database Save
# ==========================================================
@dp.message(LoginForm.enter_password)
async def process_password(message: types.Message, state: FSMContext):
    password = message.text
    data = await state.get_data()
    username = data.get('phone')
    site_name = data.get('site', '777BIGWIN')
    user_tg_id = message.from_user.id
    
    if site_name == "6Lottery":
        login_url = "https://www.6win584.com/#/login"
        main_url = "https://www.6win584.com/#/main"
        game_url = "https://www.6win584.com/#/home/AllLotteryGames/WinGo?id=1"
    else:
        login_url = "https://www.777bigwingame.app/#/login"
        main_url = "https://www.777bigwingame.app/#/main"
        game_url = "https://www.777bigwingame.app/#/home/AllLotteryGames/WinGo?id=1"

    # 📊 Progress Bar Update လုပ်ပေးမည့် Helper Function
    async def update_progress(msg: types.Message, pct: int):
        filled = pct // 10
        empty = 10 - filled
        bar = "■" * filled + "□" * empty
        try:
            await msg.edit_text(f"{bar} Logging in... {pct}%")
        except Exception:
            pass

    # Initial Loading State 0%
    loading_msg = await message.answer("□□□□□□□□□□ Logging in... 0%")
    
    # 10% - Browser စတင်ဖွင့်ခြင်း
    await update_progress(loading_msg, 10)
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36", 
        viewport={'width': 390, 'height': 844}, 
        is_mobile=True
    )
    page = await context.new_page()
    
    try:
        # 30% - Login စာမျက်နှာသို့ သွားခြင်း
        await update_progress(loading_msg, 30)
        await page.goto(login_url, wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(3000)

        # 50% - ဖုန်းနံပါတ်နှင့် စကားဝှက် ရိုက်ထည့်ခြင်း
        await update_progress(loading_msg, 50)
        js_code = """
        ([user, pwd]) => {
            function fillVueInput(element, value) {
                if (!element) return false;
                const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                nativeSetter.call(element, value);
                element.dispatchEvent(new Event('input', { bubbles: true }));
                element.dispatchEvent(new Event('change', { bubbles: true }));
                element.blur();
                return true;
            }
            let phone = document.querySelector('input[name="userNumber"]');
            fillVueInput(phone, user);
            let pass = document.querySelector('input[placeholder="စကားဝှက်"]') || 
                       document.querySelector('input[placeholder="Password"]') || 
                       document.querySelector('.passwordInput__container-input input');
            fillVueInput(pass, pwd);
        }
        """
        await page.evaluate(js_code, [username, password])
        await page.wait_for_timeout(1000)
        
        # 70% - Login ခလုတ်နှိပ်ခြင်း
        await update_progress(loading_msg, 70)
        await page.evaluate("() => { let btn = document.querySelector('button.active'); if (btn) btn.click(); }")
        await page.wait_for_timeout(5000)
        
        try:
            for _ in range(3):
                btn = await page.query_selector(".announcement-dialog__button")
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(1000)
                else:
                    break
        except Exception: 
            pass
        
        if "login" not in page.url.lower():
            # 85% - Main စာမျက်နှာသို့သွား၍ အချက်အလက်များယူခြင်း
            await update_progress(loading_msg, 85)
            try:
                await page.goto(main_url, wait_until="networkidle")
                await page.wait_for_timeout(3000)
            except Exception: 
                pass

            user_id = "N/A"
            nickname = "Unknown"
            balance_text = "0.00 Ks"
            site_login_time = get_myanmar_time().strftime("%Y-%m-%d %H:%M:%S")

            try:
                nick_el = page.locator('.userInfo__container-content-nickname h3').first
                if await nick_el.is_visible(timeout=3000): 
                    nickname = await nick_el.inner_text()
                
                uid_el = page.locator('.userInfo__container-content-uid span:nth-child(3)').first
                if await uid_el.is_visible(timeout=2000): 
                    user_id = await uid_el.inner_text()
                    
                balance_el = page.locator('.balance_info p.totalSavings__container-header__subtitle span').first
                if await balance_el.is_visible(timeout=2000): 
                    balance_text = await balance_el.inner_text()
            except Exception: 
                pass

            await page.goto(game_url, wait_until="networkidle")
            await page.wait_for_timeout(2000)

            db_user = await db.get_user(user_tg_id)
            if db_user:
                ai_mode = db_user.get("ai_mode", "🎯 Pattern AI")
            else:
                ai_mode = "🎯 Pattern AI"
            
            if ai_mode not in VALID_AI_NAMES: 
                ai_mode = "🎯 Pattern AI"

            await db.save_user_login(user_tg_id, username, user_id.strip(), nickname.strip(), balance_text.strip(), site_login_time, ai_mode)

            await state.update_data(
                is_logged_in=True, 
                username=username, 
                user_id=user_id.strip(),
                nickname=nickname.strip(), 
                balance=balance_text.strip(), 
                login_time=site_login_time.strip()
            )

            active_sessions[user_tg_id] = {
                "site": site_name,
                "playwright": p,
                "browser": browser,
                "page": page,
                "is_auto_betting": False,
                "ai_mode": ai_mode,
                "bet_sequence": [10],           
                "current_bet_step": 0,          
                "profit_target": 0,             
                "start_balance": extract_balance(balance_text),
                "session_profit": 0.0, 
                "hit_wait": 0,
                "current_misses": 0,
                "is_ai_prediction_enabled": False, 
                "last_predicted_issue": None       
            }

            # 100% - အရာအားလုံးပြီးစီးခြင်း
            await update_progress(loading_msg, 100)
            await asyncio.sleep(0.5) 
            
            await message.answer(f"𝗟𝗢𝗚𝗜𝗡 𝗦𝗨𝗖𝗖𝗘𝗦𝗦 ({site_name})", reply_markup=get_logged_in_keyboard())
            await state.set_state(LoginForm.main_menu)
            
        else:
            await message.answer("ʟᴏɢɪɴ ꜰᴀɪʟᴇᴅ ᴘᴀꜱꜱᴡᴏʀᴅ ɪɴᴄᴏʀʀᴇᴄᴛ", reply_markup=get_main_keyboard())
            await browser.close()
            await p.stop()
            await state.clear()

        await loading_msg.delete()

    except Exception as e:
        await message.answer(f"⚠️ <b>Error:</b> {html.escape(str(e))}", reply_markup=get_main_keyboard())
        if 'browser' in locals(): 
            await browser.close()
        if 'p' in locals(): 
            await p.stop()
        await state.clear()
        await loading_msg.delete()

P_1 = '<tg-emoji emoji-id="5890997763331591703">⚙️</tg-emoji>'
P_2 = '<tg-emoji emoji-id="5875180111744995604">⚙️</tg-emoji>'
P_3 = '<tg-emoji emoji-id="5877443460725739250">⚙️</tg-emoji>'
P_4 = '<tg-emoji emoji-id="5967574255670399788">⚙️</tg-emoji>'
P_5 = '<tg-emoji emoji-id="5807868868886009920">⚙️</tg-emoji>'
P_6 = '<tg-emoji emoji-id="5807461353799030682">⚙️</tg-emoji>'

# ==========================================================
# 🔮 AI Prediction Mode Handlers
# ==========================================================
@dp.message(F.text == f"{E_PREDICT} AI Prediction")
async def btn_ai_prediction_toggle(message: types.Message):
    user_tg_id = message.from_user.id
    if user_tg_id not in active_sessions: 
        return await message.answer("⚠️ အရင်ဆုံး Login ဝင်ပေးပါ။")
        
    is_enabled = active_sessions[user_tg_id].get("is_ai_prediction_enabled", False)
    
    await message.answer(
        f"🔮 <b>AI Prediction Broadcast</b>\n\n"
        "AI ၏ ခန့်မှန်းချက်များကိုသာ ကြည့်ရှုလိုပါက ဤစနစ်ကို ဖွင့်နိုင်ပါသည်။",
        reply_markup=get_ai_prediction_toggle_keyboard(is_enabled)
    )

@dp.callback_query(F.data == "toggle_aipred")
async def process_toggle_aipred(callback: types.CallbackQuery):
    user_tg_id = callback.from_user.id
    if user_tg_id not in active_sessions: 
        return await callback.answer("⚠️ Session Expired.", show_alert=True)
        
    current_state = active_sessions[user_tg_id].get("is_ai_prediction_enabled", False)
    new_state = not current_state
    active_sessions[user_tg_id]["is_ai_prediction_enabled"] = new_state
    
    await callback.message.edit_reply_markup(reply_markup=get_ai_prediction_toggle_keyboard(new_state))
    
    if new_state:
        await callback.answer("✅ AI Prediction ပြသခြင်းကို ဖွင့်လိုက်ပါပြီ။", show_alert=True)
        asyncio.create_task(prediction_broadcast_loop(user_tg_id, callback.message))
    else:
        await callback.answer("❌ AI Prediction ပြသခြင်းကို ပိတ်လိုက်ပါပြီ။", show_alert=True)

async def prediction_broadcast_loop(user_tg_id, message: types.Message):
    api_error_count = 0
    
    # ခြေရာခံမည့် Current & Longest Streaks များကို အစပြုရန်
    if "current_win_streak" not in active_sessions.get(user_tg_id, {}):
        active_sessions[user_tg_id]["current_win_streak"] = 0
        active_sessions[user_tg_id]["current_lose_streak"] = 0
        active_sessions[user_tg_id]["longest_win_streak"] = 0
        active_sessions[user_tg_id]["longest_lose_streak"] = 0

    while active_sessions.get(user_tg_id, {}).get("is_ai_prediction_enabled", False):
        try:
            predicted_bet, confidence, current_issue, ai_name = await get_ai_prediction(user_tg_id)
            last_issue = active_sessions[user_tg_id].get("last_predicted_issue")

            if current_issue:
                api_error_count = 0
                if current_issue != last_issue:
                    active_sessions[user_tg_id]["last_predicted_issue"] = current_issue
                    
                    # Longest Streaks များကို ယူရန်
                    long_w = active_sessions[user_tg_id].get("longest_win_streak", 0)
                    long_l = active_sessions[user_tg_id].get("longest_lose_streak", 0)
                    
                    pred_msg = await message.answer(
                        f"<blockquote>"
                        f"{P_1} Ai Prediction - Live\n"
                        f"━━━━━━━━━━━━━━━\n"
                        f"{P_2} WINGO_30S : <code>{current_issue}</code>\n"
                        f"{P_3} Prediction : <b>{predicted_bet.upper()}</b>〔 {long_w} 〕|〔 {long_l} 〕\n"
                        f"{P_4} Status : Waiting for result..."
                        f"</blockquote>"
                    )
                    
                    actual_result = "? | ?"
                    for _ in range(20):
                        if not active_sessions.get(user_tg_id, {}).get("is_ai_prediction_enabled", False): 
                            break
                        await asyncio.sleep(2)
                        actual_result = await get_latest_game_result(current_issue, user_tg_id)
                        if actual_result != "? | ?": 
                            break
                    
                    if actual_result != "? | ?":
                        actual_size = actual_result.split(" | ")[1].strip().lower()
                        if predicted_bet.lower() == actual_size:
                            status_text = f"{P_5}WIN{actual_result}"
                            
                            # Win တွက်ချက်မှုများ
                            active_sessions[user_tg_id]["current_win_streak"] += 1
                            active_sessions[user_tg_id]["current_lose_streak"] = 0
                            
                            # လက်ရှိ Win Streak သည် Longest ထက်များသွားပါက Update လုပ်မည်
                            if active_sessions[user_tg_id]["current_win_streak"] > active_sessions[user_tg_id]["longest_win_streak"]:
                                active_sessions[user_tg_id]["longest_win_streak"] = active_sessions[user_tg_id]["current_win_streak"]
                        else:
                            status_text = f"{P_6} LOSE{actual_result}"
                            
                            # Lose တွက်ချက်မှုများ
                            active_sessions[user_tg_id]["current_lose_streak"] += 1
                            active_sessions[user_tg_id]["current_win_streak"] = 0
                            
                            # လက်ရှိ Lose Streak သည် Longest ထက်များသွားပါက Update လုပ်မည်
                            if active_sessions[user_tg_id]["current_lose_streak"] > active_sessions[user_tg_id]["longest_lose_streak"]:
                                active_sessions[user_tg_id]["longest_lose_streak"] = active_sessions[user_tg_id]["current_lose_streak"]
                    else:
                        status_text = "⚖️ <b>DRAW (Timeout)</b>"
                        
                    # ရလဒ်ထွက်ပြီးနောက် Update ဖြစ်သွားသော Longest Streaks များကို ပြန်ယူရန်
                    new_long_w = active_sessions[user_tg_id].get("longest_win_streak", 0)
                    new_long_l = active_sessions[user_tg_id].get("longest_lose_streak", 0)
                        
                    try:
                        await pred_msg.edit_text(
                            f"<blockquote>"
                            f"{P_1} Ai Prediction - Live\n"
                            f"━━━━━━━━━━━━━━━\n"
                            f"{P_2} WINGO_30S : <code>{current_issue}</code>\n"
                            f"{P_3} Prediction : <b>{predicted_bet.upper()}</b>〔 {long_w} 〕|〔 {long_l} 〕\n"
                            f"{P_4} Status : {status_text}"
                            f"</blockquote>"
                        )
                    except Exception: 
                        pass
                    
                    await asyncio.sleep(2)
                else:
                    await asyncio.sleep(2)
            else:
                api_error_count += 1
                if api_error_count == 3: 
                    await message.answer("⚠️ <b>API အမှားအယွင်း:</b> ပွဲစဉ်အချက်အလက်များကို ယူ၍မရပါ။")
                await asyncio.sleep(5)
                
        except Exception: 
            await asyncio.sleep(5)

# ==========================================================
# 🎯 Feature Handlers (Hit, Profit, AI Mode)
# ==========================================================
@dp.message(F.text == f"{E_HIT} Hit Betting")
async def btn_hit_betting(message: types.Message):
    user_tg_id = message.from_user.id
    if user_tg_id not in active_sessions: 
        return await message.answer("⚠️ အရင်ဆုံး Login ဝင်ပေးပါ။")
        
    current_wait = active_sessions[user_tg_id].get("hit_wait", 0)
    await message.answer(
        "🎯 <b>Hit Betting System</b>\n(စနစ်ကို ပိတ်ထားလိုပါက အောက်ဆုံးရှိ '0' ကို နှိပ်ပါ။)", 
        reply_markup=get_hit_betting_inline_keyboard(current_wait)
    )

@dp.callback_query(F.data.startswith("hitbet_"))
async def process_hit_bet(callback: types.CallbackQuery):
    user_tg_id = callback.from_user.id
    wait_count = int(callback.data.split("_")[1])
    
    if user_tg_id in active_sessions:
        active_sessions[user_tg_id]["hit_wait"] = wait_count
        active_sessions[user_tg_id]["current_misses"] = 0 
        
    await callback.message.edit_reply_markup(reply_markup=get_hit_betting_inline_keyboard(wait_count))
    
    if wait_count > 0: 
        await callback.answer(f"✅ {wait_count} ပွဲရှုံးတာကို စောင့်ပြီးမှ စထိုးရန် သတ်မှတ်လိုက်ပါပြီ။", show_alert=True)
    else: 
        await callback.answer("❌ Hit Betting စနစ်ကို ပိတ်လိုက်ပါပြီ။", show_alert=True)

@dp.message(F.text == f"{E_PROFIT} Profit Target")
async def btn_set_profit_target(message: types.Message, state: FSMContext):
    user_tg_id = message.from_user.id
    if user_tg_id not in active_sessions: 
        return await message.answer("⚠️ အရင်ဆုံး Login ဝင်ပေးပါ။")
        
    current_target = active_sessions[user_tg_id].get("profit_target", 0)
    await state.set_state(LoginForm.enter_profit_target)
    await message.answer(
        f"🎯 <b>Auto Bet အမြတ် (Profit Target) ကို သတ်မှတ်ပါ။</b>\n"
        f"လက်ရှိ သတ်မှတ်ထားသော Target: <b>{current_target} Ks</b>", 
        reply_markup=get_cancel_keyboard()
    )

@dp.message(LoginForm.enter_profit_target)
async def process_profit_target(message: types.Message, state: FSMContext):
    user_tg_id = message.from_user.id
    text = message.text.strip()
    
    if text.lower() == 'cancel':
        await state.set_state(LoginForm.main_menu)
        return await message.answer("❌ မပြောင်းလဲတော့ပါ။", reply_markup=get_logged_in_keyboard())
        
    if not text.isdigit(): 
        return await message.answer("❌ ကျေးဇူးပြု၍ ဂဏန်းသာ ရိုက်ထည့်ပါ။")
        
    target_amount = int(text)
    active_sessions[user_tg_id]["profit_target"] = target_amount
    await state.set_state(LoginForm.main_menu)
    
    if target_amount > 0: 
        await message.answer(f"✅ <b>Profit Target:</b> {target_amount} Ks မြတ်ပါက အလိုအလျောက် ရပ်တန့်ပေးပါမည်။", reply_markup=get_logged_in_keyboard())
    else: 
        await message.answer("✅ <b>Profit Target စနစ်ကို ပိတ်လိုက်ပါပြီ။</b>", reply_markup=get_logged_in_keyboard())

@dp.message(F.text == f"{E_AI} AI Mode")
async def cmd_ai_mode(message: types.Message):
    user_tg_id = message.from_user.id
    if user_tg_id not in active_sessions: 
        return await message.answer("⚠️ အရင်ဆုံး Login ဝင်ပေးပါ။")
        
    current_mode = active_sessions[user_tg_id].get("ai_mode", "🎯 Pattern AI")
    await message.answer(f"🤖 <b>AI Mode:</b> {current_mode}", reply_markup=get_ai_mode_keyboard())

@dp.message(F.text.in_(VALID_AI_NAMES))
async def set_ai_mode(message: types.Message):
    user_tg_id = message.from_user.id
    if user_tg_id not in active_sessions: 
        return await message.answer("⚠️ အရင်ဆုံး Login ဝင်ပေးပါ။")
        
    active_sessions[user_tg_id]["ai_mode"] = message.text
    await db.update_user_ai_mode(user_tg_id, message.text)
    await message.answer(f"✅ AI စနစ်ကို <b>{message.text}</b> သို့ ပြောင်းလဲသတ်မှတ်လိုက်ပါပြီ။", reply_markup=get_logged_in_keyboard())

@dp.message(F.text == f"{E_BACK} ပင်မမီနူးသို့")
async def back_to_main(message: types.Message):
    await message.answer("ပင်မမီနူးသို့ ရောက်ရှိပါပြီ။", reply_markup=get_logged_in_keyboard())

# ==========================================================
# 🚀 Auto Bet Core Functions
# ==========================================================
async def place_auto_bet(page, message: types.Message, bet_type: str, amount: int = 10, silent: bool = False):
    try:
        bet_choice = bet_type.lower()
        
        # 1. Winning Tip (Dialog) တက်နေလျှင် ပိတ်မည်
        try:
            winning_tip = page.locator('.WinningTip__C').first
            if await winning_tip.is_visible(timeout=1000):
                close_btn = page.locator('.WinningTip__C .closeBtn').first
                if await close_btn.is_visible(): 
                    await close_btn.click(force=True)
                else:
                    active_btn = page.locator('.WinningTip__C .acitveBtn').first
                    if await active_btn.is_visible(): 
                        await active_btn.click(force=True)
                await page.wait_for_timeout(500) 
        except Exception: 
            pass

        # 2. အရောင်/အကြီးအသေး ရွေးမည်
        if bet_choice == "big": 
            await page.locator('.Betting__C-foot-b').click(timeout=5000, force=True) 
        elif bet_choice == "small": 
            await page.locator('.Betting__C-foot-s').click(timeout=5000, force=True)
        elif bet_choice == "red": 
            await page.locator('.Betting__C-head-r').click(timeout=5000, force=True)
        elif bet_choice == "green": 
            await page.locator('.Betting__C-head-g').click(timeout=5000, force=True)
        elif bet_choice in ["violet", "purple"]: 
            await page.locator('.Betting__C-head-p').click(timeout=5000, force=True)
        else:
            if not silent: 
                await message.answer("❌ မှားယွင်းနေပါသည်။")
            return False

        await page.wait_for_timeout(1000)

        # 3. လောင်းကြေး (Multiplier) တွက်ချက်ခြင်း
        if amount >= 1000:
            multiplier = amount // 1000
            base_text = "1000"
        elif amount >= 100:
            multiplier = amount // 100
            base_text = "100"
        else:
            multiplier = amount // 10
            base_text = "10"

        try:
            base_locator = page.locator("div.Betting__Popup-body-line-item").get_by_text(base_text, exact=True).first
            await base_locator.click(timeout=2000, force=True)
            await page.wait_for_timeout(500)
        except Exception: 
            pass 

        js_set_multiplier = f"""
        () => {{
            let input = document.querySelector('.Betting__Popup-body input') || 
                        document.querySelector('input[type="number"]') || 
                        document.querySelector('input.van-stepper__input');
            if(input) {{
                const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                nativeSetter.call(input, '{multiplier}');
                input.dispatchEvent(new Event('input', {{ bubbles: true }}));
                input.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        }}
        """
        await page.evaluate(js_set_multiplier)
        await page.wait_for_timeout(500)

        # 4. အတည်ပြုမည်
        confirm_btn = page.locator('.Betting__Popup-foot > div').last
        await confirm_btn.click(timeout=3000, force=True)

        await page.wait_for_timeout(2000)
        if not silent: 
            await message.answer("✅ <b>လောင်းကြေး အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ။</b>")
        return True

    except Exception as e:
        # Error တက်ပါက Screenshot ရိုက်၍ ပို့ပေးမည်
        if not silent:
            error_image_path = f"debug_error_{message.from_user.id}.png"
            try:
                await page.screenshot(path=error_image_path, full_page=True)
                photo = FSInputFile(error_image_path)
                await message.answer_photo(photo=photo, caption=f"❌ <b>Auto Bet Error:</b>\n<code>{str(e).splitlines()[0][:200]}</code>")
                if os.path.exists(error_image_path): 
                    os.remove(error_image_path)
            except Exception: 
                pass
        return False

# ==========================================================
# 📊 API Fetching
# ==========================================================
async def get_latest_game_result(target_issue, user_tg_id):
    site = active_sessions.get(user_tg_id, {}).get("site", "777BIGWIN")

    if site == "6Lottery":
        url = 'https://6lotteryapi.com/api/webapi/GetNoaverageEmerdList'
        headers = {
            'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOiIxNzgzNzQ3OTQ1IiwibmJmIjoiMTc4Mzc0Nzk0NSIsImV4cCI6IjE3ODM3NDk3NDUiLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL2V4cGlyYXRpb24iOiI3LzExLzIwMjYgMTI6MzI6MjUgUE0iLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL3JvbGUiOiJBY2Nlc3NfVG9rZW4iLCJVc2VySWQiOiIxMDc2NTk0IiwiVXNlck5hbWUiOiI5NTk2NzUzMjM4NzgiLCJVc2VyUGhvdG8iOiI3IiwiTmlja05hbWUiOiLhgJXhgLzhgIrhgLfhgLrhgIXhgK_hgLYiLCJBbW91bnQiOiI2ODIuMDAiLCJJbnRlZ3JhbCI6IjAiLCJMb2dpbk1hcmsiOiJINSIsIkxvZ2luVGltZSI6IjcvMTEvMjAyNiAxMjowMjoyNSBQTSIsIkxvZ2luSVBBZGRyZXNzIjoiMTAzLjEzNC4yMDcuMTUyIiwiRGJOdW1iZXIiOiIwIiwiSXN2YWxpZGF0b3IiOiIwIiwiS2V5Q29kZSI6IjEzMCIsIlRva2VuVHlwZSI6IkFjY2Vzc19Ub2tlbiIsIlBob25lVHlwZSI6IjEiLCJVc2VyVHlwZSI6IjAiLCJVc2VyTmFtZTIiOiIiLCJpc3MiOiJqd3RJc3N1ZXIiLCJhdWQiOiJsb3R0ZXJ5VGlja2V0In0.LcFWlrh3lOnhgdztdqGJv0idysPzMbzk5yHaW_mRPZA',
            'content-type': 'application/json;charset=UTF-8',
        }
        json_data = {
            'pageSize': 10, 'pageNo': 1, 'typeId': 30, 'language': 7,
            'random': 'f8e6fe62969046bf875bd73756a0d058',
            'signature': 'E156CA0133F342D84E376535EEE5CDD9', 
            'timestamp': 1783748130,
        }
    else:
        url = 'https://api.bigwinqaz.com/api/webapi/GetNoaverageEmerdList'
        headers = {
            'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOiIxNzgzNjY1OTAyIiwibmJmIjoiMTc4MzY2NTkwMiIsImV4cCI6IjE3ODM2Njc3MDIiLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL2V4cGlyYXRpb24iOiI3LzEwLzIwMjYgMTo0NTowMiBQTSIsImh0dHA6Ly9zY2hlbWFzLm1pY3Jvc29mdC5jb20vd3MvMjAwOC8wNi9pZGVudGl0eS9jbGFpbXMvcm9sZSI6IkFjY2Vzc19Ub2tlbiIsIlVzZXJJZCI6IjU3NDMzNSIsIlVzZXJOYW1lIjoiOTU5Njc1MzIzODc4IiwiVXNlclBob3RvIjoiNyIsIk5pY2tOYW1lIjoiV2FuZyBMaW4iLCJBbW91bnQiOiIxMDAwLjAwIiwiSW50ZWdyYWwiOiIwIiwiTG9naW5NYXJrIjoiSDUiLCJMb2dpblRpbWUiOiI3LzEwLzIwMjYgMToxNTowMiBQTSIsIkxvZ2luSVBBZGRyZXNzIjoiMTg4LjI0NS44Ny4zIiwiRGJOdW1iZXIiOiIwIiwiSXN2YWxpZGF0b3IiOiIwIiwiS2V5Q29kZSI6IjEwNiIsIlRva2VuVHlwZSI6IkFjY2Vzc19Ub2tlbiIsIlBob25lVHlwZSI6IjEiLCJVc2VyVHlwZSI6IjAiLCJVc2VyTmFtZTIiOiJweWFlc29uZTVwc3BAeWFob28uY29tIiwiaXNzIjoiand0SXNzdWVyIiwiYXVkIjoibG90dGVyeVRpY2tldCJ9.U-YRQvRv20OmGnLmm_DLdS9D-jDyNhCqWhFk4M1zmkc',
            'content-type': 'application/json;charset=UTF-8',
        }
        json_data = {
            'pageSize': 10, 'pageNo': 1, 'typeId': 30, 'language': 7,
            'random': '7bc385b8267d48ebbc62fe04296cbed4',
            'signature': '2B34898B971F29208D293D1E530F8627', 
            'timestamp': 1783665931,
        }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as response:
                api_result = await response.json()
                
        records = api_result.get('data', {}).get('list', [])
        for item in records:
            if str(item['issueNumber']) == str(target_issue):
                num = int(item['number'])
                if num >= 5:
                    size = "BIG"
                else:
                    size = "SMALL"
                return f"{num} | {size}"
    except Exception: 
        pass
        
    return "? | ?"

async def get_ai_prediction(user_tg_id):
    site = active_sessions.get(user_tg_id, {}).get("site", "777BIGWIN")

    if site == "6Lottery":
        url = 'https://6lotteryapi.com/api/webapi/GetNoaverageEmerdList'
        headers = {
            'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOiIxNzgzNzQ3OTQ1IiwibmJmIjoiMTc4Mzc0Nzk0NSIsImV4cCI6IjE3ODM3NDk3NDUiLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL2V4cGlyYXRpb24iOiI3LzExLzIwMjYgMTI6MzI6MjUgUE0iLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL3JvbGUiOiJBY2Nlc3NfVG9rZW4iLCJVc2VySWQiOiIxMDc2NTk0IiwiVXNlck5hbWUiOiI5NTk2NzUzMjM4NzgiLCJVc2VyUGhvdG8iOiI3IiwiTmlja05hbWUiOiLhgJXhgLzhgIrhgLfhgLrhgIXhgK_hgLYiLCJBbW91bnQiOiI2ODIuMDAiLCJJbnRlZ3JhbCI6IjAiLCJMb2dpbk1hcmsiOiJINSIsIkxvZ2luVGltZSI6IjcvMTEvMjAyNiAxMjowMjoyNSBQTSIsIkxvZ2luSVBBZGRyZXNzIjoiMTAzLjEzNC4yMDcuMTUyIiwiRGJOdW1iZXIiOiIwIiwiSXN2YWxpZGF0b3IiOiIwIiwiS2V5Q29kZSI6IjEzMCIsIlRva2VuVHlwZSI6IkFjY2Vzc19Ub2tlbiIsIlBob25lVHlwZSI6IjEiLCJVc2VyVHlwZSI6IjAiLCJVc2VyTmFtZTIiOiIiLCJpc3MiOiJqd3RJc3N1ZXIiLCJhdWQiOiJsb3R0ZXJ5VGlja2V0In0.LcFWlrh3lOnhgdztdqGJv0idysPzMbzk5yHaW_mRPZA',
            'content-type': 'application/json;charset=UTF-8',
        }
        json_data = {
            'pageSize': 10, 'pageNo': 1, 'typeId': 30, 'language': 7,
            'random': 'f8e6fe62969046bf875bd73756a0d058',
            'signature': 'E156CA0133F342D84E376535EEE5CDD9', 
            'timestamp': 1783748130,
        }
    else:
        url = 'https://api.bigwinqaz.com/api/webapi/GetNoaverageEmerdList'
        headers = {
            'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOiIxNzgzNjQzMjUwIiwibmJmIjoiMTc4MzY0MzI1MCIsImV4cCI6IjE3ODM2NDUwNTAiLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL2V4cGlyYXRpb24iOiI3LzEwLzIwMjYgNzoyNzozMCBBTSIsImh0dHA6Ly9zY2hlbWFzLm1pY3Jvc29mdC5jb20vd3MvMjAwOC8wNi9pZGVudGl0eS9jbGFpbXMvcm9sZSI6IkFjY2Vzc19Ub2tlbiIsIlVzZXJJZCI6IjU3NDMzNSIsIlVzZXJOYW1lIjoiOTU5Njc1MzIzODc4IiwiVXNlclBob3RvIjoiNyIsIk5pY2tOYW1lIjoiV2FuZyBMaW4iLCJBbW91bnQiOiIxMDAwLjAwIiwiSW50ZWdyYWwiOiIwIiwiTG9naW5NYXJrIjoiSDUiLCJMb2dpblRpbWUiOiI3LzEwLzIwMjYgNjo1NzozMCBBTSIsIkxvZ2luSVBBZGRyZXNzIjoiMTAzLjEzNC4yMDcuMTUyIiwiRGJOdW1iZXIiOiIwIiwiSXN2YWxpZGF0b3IiOiIwIiwiS2V5Q29kZSI6Ijk3IiwiVG9rZW5UeXBlIjoiQWNjZXNzX1Rva2VuIiwiUGhvbmVUeXBlIjoiMSIsIlVzZXJUeXBlIjoiMCIsIlVzZXJOYW1lMiI6InB5YWVzb25lNXBzcEB5YWhvby5jb20iLCJpc3MiOiJqd3RJc3N1ZXIiLCJhdWQiOiJsb3R0ZXJ5VGlja2V0In0.C-FbAazz7HkLeQ5L5eISGHGJCdwarGdz4A3v9XyvqCE',
            'content-type': 'application/json;charset=UTF-8',
        }
        json_data = {
            'pageSize': 10, 'pageNo': 1, 'typeId': 30, 'language': 7,
            'random': 'e431a6544cde4cbb8e09a4c01199b75b',
            'signature': '1668945A145F050B049ED587E6E9E0E7', 
            'timestamp': 1000000000,
        }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as response:
                api_result = await response.json()
                
        records = api_result.get('data', {}).get('list', [])
        if records:
            last_completed_issue = records[0]['issueNumber']
            next_issue = str(int(last_completed_issue) + 1)
            
            history_docs = []
            for item in records:
                num = int(item['number'])
                if num >= 5:
                    size_text = "BIG"
                else:
                    size_text = "SMALL"
                history_docs.append({"size": size_text, "number": num})
            
            user_ai_name = active_sessions.get(user_tg_id, {}).get("ai_mode", "🎯 Pattern AI")
            
            mode_key = "pattern"
            for key, val in ai_engines.AI_MODES.items():
                if val["name"] == user_ai_name:
                    mode_key = key
                    break
                    
            predicted_size, display_name, confidence, desc = ai_engines.get_prediction(history_docs, mode_key)
            
            return predicted_size.lower(), confidence, next_issue, user_ai_name
        else:
            return None, 0, None, None
            
    except Exception as e:
        print(f"API Fetching Error: {e}")
        return None, 0, None, None

# ==========================================================
# 🔄 Continuous Auto Bet Loop Task 
# ==========================================================
async def auto_bet_loop(user_tg_id, message: types.Message):
    await message.answer("🚀 Auto-Betting စတင်ပါပြီ! ရပ်တန့်ရန် 🛑 Stop Auto-Bet ကို နှိပ်ပါ။")
    last_betted_issue = None
    api_error_count = 0 

    while active_sessions.get(user_tg_id, {}).get("is_auto_betting", False):
        try:
            predicted_bet, confidence, current_issue, ai_name = await get_ai_prediction(user_tg_id)

            if current_issue:
                api_error_count = 0 
                if current_issue != last_betted_issue:
                    page = active_sessions[user_tg_id]["page"]
                    
                    # --- Hit Betting Logic ---
                    hit_wait = active_sessions[user_tg_id].get("hit_wait", 0)
                    current_misses = active_sessions[user_tg_id].get("current_misses", 0)
                    
                    if hit_wait > 0 and current_misses < hit_wait:
                        msg = await message.answer(
                            f"⏳ <b>Hit Waiting: {current_misses}/{hit_wait}</b>\n"
                            f"• WINGO_30S : {current_issue}\n"
                            f"• Pred : {predicted_bet.upper()} (စောင့်ကြည့်နေပါသည်)"
                        )
                        
                        actual_result = "? | ?"
                        for _ in range(20):
                            if not active_sessions.get(user_tg_id, {}).get("is_auto_betting", False): 
                                break
                            await asyncio.sleep(2)
                            actual_result = await get_latest_game_result(current_issue, user_tg_id)
                            if actual_result != "? | ?": 
                                break
                                
                        try:
                            actual_size = actual_result.split(" | ")[1].strip().lower()
                            if predicted_bet.lower() == actual_size:
                                active_sessions[user_tg_id]["current_misses"] = 0 
                                await msg.edit_text(f"🔄 <b>Hit Reset:</b> AI အမှန်ခန့်မှန်းသွားသဖြင့် အစမှပြန်စောင့်ပါမည်။\nResult: {actual_result}")
                                asyncio.create_task(delete_message_later(msg, 5)) 
                                
                            elif actual_size != "?":
                                active_sessions[user_tg_id]["current_misses"] += 1 
                                new_miss = active_sessions[user_tg_id]["current_misses"]
                                if new_miss >= hit_wait:
                                    await msg.edit_text(f"🎯 <b>Target Reached!</b> {hit_wait} ပွဲဆက်တိုက်လွဲသွားသဖြင့် နောက်ပွဲမှစတင်လောင်းပါမည်။\nResult: {actual_result}")
                                    asyncio.create_task(delete_message_later(msg, 5)) 
                                else:
                                    await msg.edit_text(f"❌ <b>Virtual Loss:</b> {new_miss}/{hit_wait} ပွဲလွဲသွားပါပြီ။\nResult: {actual_result}")
                                    asyncio.create_task(delete_message_later(msg, 5)) 
                                    
                            last_betted_issue = current_issue
                        except Exception: 
                            pass
                            
                        await asyncio.sleep(2)
                        continue 

                    # --- အထက်ပါအဆင့်ကို ကျော်သွားမှသာ တကယ်လောင်းမည် ---
                    sequence = active_sessions[user_tg_id].get("bet_sequence", [10])
                    step = active_sessions[user_tg_id].get("current_bet_step", 0)
                    
                    if step >= len(sequence):
                        step = 0
                        active_sessions[user_tg_id]["current_bet_step"] = 0
                        
                    current_amount = sequence[step]

                    try:
                        bal_el_pre = page.locator('.Wallet__C-balance-l1 div').first
                        if await bal_el_pre.is_visible(timeout=2000):
                            current_bal_str = await bal_el_pre.inner_text()
                            current_bal_val = extract_balance(current_bal_str)
                            
                            if current_bal_val < current_amount:
                                await message.answer(f"⚠️ <b>လက်ကျန်ငွေ မလုံလောက်တော့ပါ။</b>\nလိုအပ်သောငွေ: {current_amount} Ks\nလက်ကျန်: {current_bal_str}\n🛑 Auto Bet ကို ရပ်နားလိုက်ပါသည်။")
                                active_sessions[user_tg_id]["is_auto_betting"] = False
                                break
                    except Exception: 
                        pass 

                    # 📝 ပုံစံသစ်ဖြင့် လောင်းကြေးအချက်အလက်ကို ပြသခြင်း (Blockquote)
                    betting_msg = (
                        f"<blockquote>"
                        f"📄 WINGO_30S : {current_issue}\n"
                        f"📄 Series : Ai Prediction\n"
                        f"🌸 Pred : {predicted_bet.upper()} | {current_amount} Ks"
                        f"</blockquote>"
                    )
                    await message.answer(betting_msg)

                    last_betted_issue = current_issue
                    await asyncio.sleep(7)

                    success = await place_auto_bet(page, message, predicted_bet, current_amount, silent=True)
                    
                    if success:
                        actual_result = "? | ?"
                        for _ in range(20): 
                            if not active_sessions.get(user_tg_id, {}).get("is_auto_betting", False): 
                                break 
                                
                            await asyncio.sleep(2)
                            actual_result = await get_latest_game_result(current_issue, user_tg_id)
                            if actual_result != "? | ?": 
                                break 
                        
                        balance_after_str = "0"
                        new_bal_val = 0.0
                        try:
                            bal_el = page.locator('.Wallet__C-balance-l1 div').first
                            if await bal_el.is_visible(timeout=2000):
                                balance_after_str = await bal_el.inner_text()
                                new_bal_val = extract_balance(balance_after_str)
                        except Exception: 
                            pass

                        try:
                            actual_size = actual_result.split(" | ")[1].strip().lower() 
                            predicted_size = predicted_bet.lower()
                            
                            if predicted_size == actual_size:
                                profit_amount = current_amount * 0.96
                                status_title = f"⚙️ <b>WIN</b> 👑 +{profit_amount:.2f} Ks"
                                active_sessions[user_tg_id]["session_profit"] += profit_amount
                                active_sessions[user_tg_id]["current_bet_step"] = 0 
                                active_sessions[user_tg_id]["current_misses"] = 0 
                                
                            elif actual_size == "?": 
                                status_title = f"⚙️ <b>DRAW</b> (Pending)"
                                
                            else:
                                status_title = f"⚙️ <b>LOSE</b> 💸 {current_amount:.2f} Ks"
                                active_sessions[user_tg_id]["session_profit"] -= current_amount
                                active_sessions[user_tg_id]["current_bet_step"] += 1
                                if active_sessions[user_tg_id]["current_bet_step"] >= len(sequence): 
                                    active_sessions[user_tg_id]["current_bet_step"] = 0
                                
                            current_profit = active_sessions[user_tg_id].get("session_profit", 0.0)
                            if current_profit > 0:
                                profit_display = f"+{current_profit:,.2f} Ks"
                            else:
                                profit_display = f"{current_profit:,.2f} Ks"
                            
                            # 📝 ပုံစံသစ်ဖြင့် ရလဒ်ကို ပြသခြင်း (Blockquote)
                            result_msg = (
                                f"<blockquote>"
                                f"{status_title}\n"
                                f"──────────────────\n"
                                f"🔠 WINGO_30S : {current_issue}\n"
                                f"🔠 Result : {actual_result}\n"
                                f"📝 Balance : K{new_bal_val:,.2f}\n"
                                f"📝 Total Profit : {profit_display}"
                                f"</blockquote>"
                            )
                            await message.answer(result_msg)
                            await db.update_user_balance(user_tg_id, balance_after_str.strip())
                            
                            profit_target = active_sessions[user_tg_id].get("profit_target", 0)
                            if profit_target > 0 and current_profit >= profit_target:
                                await message.answer(
                                    f"🎉 <b>Target ပြည့်သွားပါပြီ! ({profit_display})</b>\n"
                                    f"သတ်မှတ်ထားသော အမြတ် {profit_target} Ks သို့ ရောက်ရှိသွားသဖြင့် Auto Bet ကို အလိုအလျောက် ရပ်နားလိုက်ပါသည်။"
                                )
                                active_sessions[user_tg_id]["is_auto_betting"] = False
                                break
                                
                        except Exception: 
                            pass
                            
                    else: 
                        await asyncio.sleep(5) 
                        
                else: 
                    await asyncio.sleep(2) 
                    
            else:
                api_error_count += 1
                if api_error_count == 3: 
                    await message.answer("⚠️ <b>API အမှားအယွင်း:</b> ပွဲစဉ်အချက်အလက်များကို ယူ၍မရပါ။ API Token သက်တမ်းကုန်သွားခြင်း ဖြစ်နိုင်ပါသည်။")
                await asyncio.sleep(5) 
                
        except Exception as e:
            print(f"Auto Loop Error: {e}")
            await asyncio.sleep(5)

# ==========================================================
# ⚙️ Set Bet-Size Handlers
# ==========================================================
@dp.message(F.text == f"{E_BETSIZE} Set Bet-Size")
async def btn_set_betsize(message: types.Message, state: FSMContext):
    user_tg_id = message.from_user.id
    if user_tg_id not in active_sessions: 
        return await message.answer("⚠️ အရင်ဆုံး Login ဝင်ပေးပါ။")
        
    current_seq = active_sessions[user_tg_id].get("bet_sequence", [10])
    seq_str = "-".join(map(str, current_seq))
    
    await state.set_state(LoginForm.enter_bet_sequence)
    await message.answer(
        f"⚙️ <b>Auto Bet လောင်းကြေး (Bet Size) ကို သတ်မှတ်ပါ။</b>\n\n"
        f"လက်ရှိ သတ်မှတ်ထားသော ပမာဏ: <code>{seq_str}</code>\n\n"
        f"<b>Format:</b> 10-20-40-80 (သို့) 100-200-400\n"
        f"ကျေးဇူးပြု၍ မိမိလိုချင်သော ပမာဏကို (-) ခြား၍ ရိုက်ထည့်ပါ။ မပြောင်းလဲလိုပါက 'Cancel' ဟုရိုက်ပါ။",
        reply_markup=get_cancel_keyboard()
    )

@dp.message(LoginForm.enter_bet_sequence)
async def process_bet_sequence(message: types.Message, state: FSMContext):
    user_tg_id = message.from_user.id
    text = message.text.strip()
    
    if text.lower() == 'cancel':
        await state.set_state(LoginForm.main_menu)
        return await message.answer("❌ မပြောင်းလဲတော့ပါ။", reply_markup=get_logged_in_keyboard())
        
    try:
        sequence = [int(x.strip()) for x in text.split('-')]
        if len(sequence) == 0 or any(x <= 0 for x in sequence):
            raise ValueError
            
        active_sessions[user_tg_id]["bet_sequence"] = sequence
        active_sessions[user_tg_id]["current_bet_step"] = 0 
        
        seq_str = "-".join(map(str, sequence))
        await state.set_state(LoginForm.main_menu)
        await message.answer(
            f"✅ <b>Bet Size အောင်မြင်စွာ သတ်မှတ်ပြီးပါပြီ:</b> <code>{seq_str}</code>", 
            reply_markup=get_logged_in_keyboard()
        )
    except Exception:
        await message.answer("❌ မှားယွင်းနေပါသည်။ ဥပမာ: 10-20-40-80 ဟုသာ ဂဏန်းများကို တုံးတို (-) ခြား၍ ရိုက်ထည့်ပါ။")

# ==========================================================
# 🤖 Reply Keyboard Auto Bet & Status Handlers
# ==========================================================
@dp.message(F.text == f"{E_START} Start Auto-Bet")
async def btn_start_auto(message: types.Message, state: FSMContext):
    user_tg_id = message.from_user.id
    if user_tg_id not in active_sessions: 
        return await message.answer("⚠️ အရင်ဆုံး Login ဝင်ပေးပါ။")
        
    if active_sessions[user_tg_id].get("is_auto_betting", False):
        return await message.answer("⚠️ Auto Bet အလုပ်လုပ်နေဆဲ ဖြစ်ပါသည်။ ရပ်လိုပါက 🛑 Stop Auto-Bet ကိုနှိပ်ပါ။")

    if "bet_sequence" not in active_sessions[user_tg_id]:
        active_sessions[user_tg_id]["bet_sequence"] = [10]
        active_sessions[user_tg_id]["current_bet_step"] = 0

    try:
        page = active_sessions[user_tg_id]["page"]
        bal_el = page.locator('.Wallet__C-balance-l1 div').first
        if await bal_el.is_visible(timeout=3000):
            bal_str = await bal_el.inner_text()
            active_sessions[user_tg_id]["start_balance"] = extract_balance(bal_str)
    except Exception:
        active_sessions[user_tg_id]["start_balance"] = 0.0

    active_sessions[user_tg_id]["is_auto_betting"] = True
    asyncio.create_task(auto_bet_loop(user_tg_id, message))

@dp.message(F.text == f"{E_STOP} Stop Auto-Bet")
async def btn_stop_auto(message: types.Message, state: FSMContext):
    user_tg_id = message.from_user.id
    if user_tg_id not in active_sessions: 
        return await message.answer("⚠️ အရင်ဆုံး Login ဝင်ပေးပါ။")

    active_sessions[user_tg_id]["is_auto_betting"] = False
    await message.answer("🛑 <b>ဆက်တိုက် Auto Bet စနစ်ကို ရပ်တန့်လိုက်ပါပြီ။</b>")

@dp.message(F.text == f"{E_STATUS} Status")
async def btn_status(message: types.Message, state: FSMContext):
    user_tg_id = message.from_user.id
    if user_tg_id not in active_sessions: 
        return await message.answer("⚠️ အရင်ဆုံး Login ဝင်ပေးပါ။")

    session = active_sessions[user_tg_id]
    
    if session.get("is_auto_betting", False):
        is_auto = "Running 🟢"
    else:
        is_auto = "Stopped 🔴"
        
    ai_mode = session.get("ai_mode", "🎯 Pattern AI")
    site_name = session.get("site", "777BIGWIN")
    
    current_seq = session.get("bet_sequence", [10])
    seq_str = "-".join(map(str, current_seq))
    current_step = session.get("current_bet_step", 0)
    
    profit_target = session.get("profit_target", 0)
    
    current_bal_str = "0.00 Ks"
    try:
        page = session["page"]
        bal_el = page.locator('.Wallet__C-balance-l1 div').first
        if await bal_el.is_visible(timeout=2000):
            current_bal_str = await bal_el.inner_text()
    except Exception: 
        pass
    
    current_profit = session.get("session_profit", 0.0)
    if current_profit >= 0:
        profit_str = f"+{current_profit:g} Ks"
    else:
        profit_str = f"{current_profit:g} Ks"
        
    if profit_target > 0:
        target_str = f"{profit_target} Ks"
    else:
        target_str = "Not Set"

    status_text = (
        "📊 <b>Bot Status</b>\n"
        "━━━━━━━━━━━━━━━\n"
        f"🌐 <b>Active Site:</b> {site_name}\n"
        f"🤖 <b>Auto-Bet State:</b> {is_auto}\n"
        f"🧠 <b>Active AI Mode:</b> {ai_mode}\n"
        f"💰 <b>Current Balance:</b> {current_bal_str}\n"
        f"⚙️ <b>Bet Sequence:</b> <code>{seq_str}</code>\n"
        f"📍 <b>Current Step:</b> {current_step + 1}/{len(current_seq)} ({current_seq[current_step]} Ks)\n"
        f"🎯 <b>Profit Target:</b> {target_str}\n"
        f"📈 <b>Total Profit:</b> {profit_str}\n"
    )
    await message.answer(status_text)

# ==========================================================
# 💰 Check Balance & Other Handlers
# ==========================================================
@dp.message(LoginForm.main_menu, F.text == f"{E_BALANCE} Balance")
async def check_balance(message: types.Message, state: FSMContext):
    user_tg_id = message.from_user.id
    if user_tg_id not in active_sessions: 
        return await message.answer("⚠️ အရင်ဆုံး Login ဝင်ပေးပါ။")
        
    loading_msg = await message.answer("🔄 <b>လက်ကျန်ငွေ (Balance) ကို စစ်ဆေးနေပါသည်...</b>")
    page = active_sessions[user_tg_id]["page"]

    try:
        balance_text = "0.00 Ks"
        balance_el = page.locator('.Wallet__C-balance-l1 div').first
        if await balance_el.is_visible(timeout=3000):
            balance_text = await balance_el.inner_text()

        await state.update_data(balance=balance_text.strip())
        await db.update_user_balance(user_tg_id, balance_text.strip())

        await loading_msg.delete()
        await message.answer(f"💰 <b>သင့်ရဲ့ လက်ရှိ လက်ကျန်ငွေ:</b> {balance_text.strip()}", reply_markup=get_logged_in_keyboard())
    except Exception as e:
        await loading_msg.delete()
        await message.answer(f"⚠️ <b>Error:</b> Balance စစ်ဆေးရာတွင် အခက်အခဲရှိနေပါသည်။", reply_markup=get_logged_in_keyboard())

@dp.message(LoginForm.main_menu, F.text == f"{E_INFO} Info")
async def show_info(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    user_id = data.get('user_id', 'N/A')
    username = data.get('username', 'N/A')
    nickname = data.get('nickname', 'Unknown')
    balance = data.get('balance', '0.00 Ks')
    site_name = active_sessions.get(message.from_user.id, {}).get("site", "Unknown")
    login_time = data.get('login_time', get_myanmar_time().strftime("%Y-%m-%d %H:%M:%S"))
    
    expire_iso = await db.get_user_subscription(message.from_user.id)
    if expire_iso:
        expire_str = datetime.fromisoformat(expire_iso).strftime('%Y-%m-%d %I:%M %p')
    else:
        expire_str = "N/A"

    info_text = (
        "👤 <b>User Information:</b>\n"
        f"├─ 🌐 <b>Site:</b> {site_name}\n"
        f"├─ 🆔 <b>User ID:</b> {user_id}\n"
        f"├─ 📱 <b>Username:</b> {username}\n"
        f"├─ 🏷️ <b>Nickname:</b> {nickname}\n"
        f"├─ 💰 <b>Balance:</b> {balance}\n"
        f"├─ 📅 <b>Login Date:</b> {login_time}\n"
        f"├─ 🔑 <b>Expire On:</b> {expire_str} (MMT)\n"
        "└─ ✅ <b>Allow Withdraw:</b> Yes\n"
    )
    await message.answer(info_text, reply_markup=get_logged_in_keyboard())

@dp.message(LoginForm.main_menu, F.text == f"{E_LOGOUT} Logout")
async def logout(message: types.Message, state: FSMContext):
    user_tg_id = message.from_user.id
    if user_tg_id in active_sessions:
        active_sessions[user_tg_id]["is_auto_betting"] = False 
        active_sessions[user_tg_id]["is_ai_prediction_enabled"] = False 
        
        page = active_sessions[user_tg_id].get("page")
        site = active_sessions[user_tg_id].get("site", "777BIGWIN")
        
        if page:
            try:
                if site == "6Lottery":
                    await page.goto("https://www.6win584.com/#/main", wait_until="networkidle")
                else:
                    await page.goto("https://www.777bigwingame.app/#/main", wait_until="networkidle")
                await page.wait_for_timeout(2000)

                logout_btn = page.locator("div, button, span").filter(has_text="လော့အောက်").first
                if await logout_btn.is_visible(timeout=3000):
                    await logout_btn.click()
                    await page.wait_for_timeout(1000) 

                confirm_btn = page.locator("div.dialog__container-footer button", has_text="အတည်ပြုပါ").first
                if await confirm_btn.is_visible(timeout=3000):
                    await confirm_btn.click()
                    await page.wait_for_timeout(2000)
                    
            except Exception as e:
                print(f"Logout UI Click Error: {e}")

        # Browser များကို ပိတ်ခြင်း
        try:
            await active_sessions[user_tg_id]["browser"].close()
            await active_sessions[user_tg_id]["playwright"].stop()
        except Exception: 
            pass
            
        del active_sessions[user_tg_id]
        
    await state.clear()
    await message.answer("👋 အကောင့်ထွက်ပြီးပါပြီ။", reply_markup=get_main_keyboard())

@dp.message(F.text == f"{E_GAMES} Games")
async def games(message: types.Message):
    await message.answer(
        "🎮 <b>Game ရွေးချယ်ရန်:</b>\nWin Go 30s ကို ရွေးချယ်ထားပါသည်။\n\n"
        "🤖 <b>Bot Commands:</b>\n"
        f"<code>{E_START} Start Auto-Bet</code> - ခလုတ်နှိပ်၍ Auto Bet စတင်နိုင်ပါသည်\n"
        f"<code>{E_STOP} Stop Auto-Bet</code> - ခလုတ်နှိပ်၍ Auto Bet ရပ်တန့်နိုင်ပါသည်\n",
        reply_markup=get_main_keyboard()
    )

# ==========================================================
# 🚀 Main Bot Loop
# ==========================================================
async def main():
    print("🚀 Auto-Bet v2 Bot စတင်နေပါပြီ...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Bot ကို ရပ်တန့်လိုက်ပါသည်။")
[file content end]
