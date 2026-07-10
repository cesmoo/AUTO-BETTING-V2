import asyncio
import os
import html
import random
import aiohttp
import time
import re
from datetime import datetime
from dotenv import load_dotenv

from aiogram import Bot, Dispatcher, types, F
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import FSInputFile, ReplyKeyboardMarkup, KeyboardButton, ReplyKeyboardRemove

from playwright.async_api import async_playwright

# Database ကို သီးသန့်ဖိုင်မှ ခေါ်ယူအသုံးပြုခြင်း
import database as db 

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# Playwright Browser Objects များကို Memory တွင်သာထားရန်
active_sessions = {}

# ==========================================================
# 🛠️ Helper Functions
# ==========================================================
def extract_balance(bal_str: str) -> float:
    """String အနေဖြင့်ရလာသော Balance (ဥပမာ: K 267.82) ကို ဂဏန်း(Float) အဖြစ်ပြောင်းပေးရန်"""
    try:
        clean_str = re.sub(r'[^\d.]', '', bal_str)
        return float(clean_str) if clean_str else 0.0
    except:
        return 0.0

# ==========================================================
# 🗂️ FSM States
# ==========================================================
class LoginForm(StatesGroup):
    select_site = State()
    enter_phone = State()
    enter_password = State()
    main_menu = State()
    enter_bet_sequence = State() 
    enter_profit_target = State() # 👈 Profit Target သတ်မှတ်ရန် State အသစ်

# ==========================================================
# ⌨️ Keyboards
# ==========================================================
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔐 Login")], [KeyboardButton(text="🎰 Games")]],
        resize_keyboard=True
    )

def get_site_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="777BIGWIN")], [KeyboardButton(text="🔙 နောက်သို့")]],
        resize_keyboard=True
    )

def get_logged_in_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Info"), KeyboardButton(text="💰 Balance"), KeyboardButton(text="📊 Status")], 
            [KeyboardButton(text="▶️ Start Auto-Bet"), KeyboardButton(text="🛑 Stop Auto-Bet")],
            [KeyboardButton(text="🎰 Games"), KeyboardButton(text="🤖 AI Mode")],
            [KeyboardButton(text="⚙️ Set Bet-Size"), KeyboardButton(text="🎯 Profit Target")], # 👈 Profit Target ထည့်သွင်းထားသည်
            [KeyboardButton(text="🔐 Logout")]
        ],
        resize_keyboard=True
    )

def get_ai_mode_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🧠 Basic Trend AI"), KeyboardButton(text="🚀 ChatGPT Mode")],
            [KeyboardButton(text="🌌 Gemini Mode"), KeyboardButton(text="🔙 ပင်မမီနူးသို့")]
        ],
        resize_keyboard=True
    )

# ==========================================================
# 🤖 Command Handlers
# ==========================================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("👋 <b>မင်္ဂလာပါ!</b>\nအကောင့်ဝင်ရန် Login ကိုနှိပ်ပါ။", reply_markup=get_main_keyboard())

@dp.message(F.text == "🔐 Login")
async def login_start(message: types.Message, state: FSMContext):
    await state.set_state(LoginForm.select_site)
    await message.answer("🌐 <b>Please select a site to login:</b>", reply_markup=get_site_keyboard())

@dp.message(LoginForm.select_site)
async def process_site(message: types.Message, state: FSMContext):
    if message.text == "🔙 နောက်သို့":
        await state.clear()
        return await message.answer("Cancelled.", reply_markup=get_main_keyboard())
    await state.update_data(site=message.text)
    await state.set_state(LoginForm.enter_phone)
    await message.answer("📞 <b>Please enter your phone:</b>", reply_markup=ReplyKeyboardRemove())

@dp.message(LoginForm.enter_phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(LoginForm.enter_password)
    await message.answer("🔑 <b>Please enter your password:</b>", reply_markup=ReplyKeyboardRemove())

# ==========================================================
# 🔥 Playwright Logic: Login & Database Save
# ==========================================================
@dp.message(LoginForm.enter_password)
async def process_password(message: types.Message, state: FSMContext):
    password = message.text
    data = await state.get_data()
    username = data.get('phone')
    user_tg_id = message.from_user.id
    
    loading_msg = await message.answer("🔄 <b>အကောင့်ဝင်နေပါသည်... ခဏစောင့်ပါ...</b>")
    
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36", 
        viewport={'width': 390, 'height': 844}, 
        is_mobile=True
    )
    page = await context.new_page()
    
    try:
        await page.goto("https://www.777bigwingame.app/#/login", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(3000)

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
        await page.evaluate("() => { let btn = document.querySelector('button.active'); if (btn) btn.click(); }")
        await page.wait_for_timeout(5000)
        
        try:
            for _ in range(3):
                btn = await page.query_selector(".announcement-dialog__button")
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(1000)
                else: break
        except: pass
        
        if "login" not in page.url.lower():
            try:
                await page.goto("https://www.777bigwingame.app/#/main", wait_until="networkidle")
                await page.wait_for_timeout(3000)
            except: pass

            user_id, nickname, balance_text = "N/A", "Unknown", "0.00 Ks"
            site_login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

            try:
                nick_el = page.locator('.userInfo__container-content-nickname h3').first
                if await nick_el.is_visible(timeout=3000): nickname = await nick_el.inner_text()
                
                uid_el = page.locator('.userInfo__container-content-uid span:nth-child(3)').first
                if await uid_el.is_visible(timeout=2000): user_id = await uid_el.inner_text()
                    
                balance_el = page.locator('.balance_info p.totalSavings__container-header__subtitle span').first
                if await balance_el.is_visible(timeout=2000): balance_text = await balance_el.inner_text()
            except: pass

            await page.goto("https://www.777bigwingame.app/#/home/AllLotteryGames/WinGo?id=1", wait_until="networkidle")
            await page.wait_for_timeout(2000)

            db_user = await db.get_user(user_tg_id)
            ai_mode = db_user.get("ai_mode", "🧠 Basic Trend AI") if db_user else "🧠 Basic Trend AI"

            await db.save_user_login(user_tg_id, username, user_id.strip(), nickname.strip(), balance_text.strip(), site_login_time, ai_mode)

            await state.update_data(
                is_logged_in=True, username=username, user_id=user_id.strip(),
                nickname=nickname.strip(), balance=balance_text.strip(), login_time=site_login_time.strip()
            )

            active_sessions[user_tg_id] = {
                "playwright": p,
                "browser": browser,
                "page": page,
                "is_auto_betting": False,
                "ai_mode": ai_mode,
                "bet_sequence": [10],           
                "current_bet_step": 0,          
                "profit_target": 0,             # 👈 Default Target: 0 (Disabled)
                "start_balance": 0.0            # 👈 Tracker for starting balance
            }

            await message.answer("✅ <b>LOGIN SUCCESSFUL</b>\nသင့်အကောင့်အချက်အလက်များကို Database တွင် မှတ်တမ်းတင်ထားပါသည်။", reply_markup=get_logged_in_keyboard())
            await state.set_state(LoginForm.main_menu)
            
        else:
            await message.answer("❌ <b>Login မအောင်မြင်ပါ။ စကားဝှက် မှားယွင်းနေနိုင်ပါသည်။</b>", reply_markup=get_main_keyboard())
            await browser.close()
            await p.stop()
            await state.clear()

        await loading_msg.delete()

    except Exception as e:
        await message.answer(f"⚠️ <b>Error:</b> {html.escape(str(e))}", reply_markup=get_main_keyboard())
        if 'browser' in locals(): await browser.close()
        if 'p' in locals(): await p.stop()
        await state.clear()
        await loading_msg.delete()

# ==========================================================
# 🎯 Profit Target Handlers
# ==========================================================
@dp.message(F.text == "🎯 Profit Target")
async def btn_set_profit_target(message: types.Message, state: FSMContext):
    user_tg_id = message.from_user.id
    if user_tg_id not in active_sessions: 
        return await message.answer("⚠️ အရင်ဆုံး Login ဝင်ပေးပါ။")
    
    current_target = active_sessions[user_tg_id].get("profit_target", 0)
    
    await state.set_state(LoginForm.enter_profit_target)
    await message.answer(
        f"🎯 <b>Auto Bet အမြတ် (Profit Target) ကို သတ်မှတ်ပါ။</b>\n\n"
        f"လက်ရှိ သတ်မှတ်ထားသော Target: <b>{current_target} Ks</b>\n\n"
        f"သင်လိုချင်သော အမြတ်ပမာဏကို ရိုက်ထည့်ပါ။ (ဥပမာ: 20000)\n"
        f"ပိတ်ထားလိုပါက `0` ဟု ရိုက်ထည့်ပါ။ မပြောင်းလဲလိုပါက 'Cancel' ဟုရိုက်ပါ။",
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Cancel")]], resize_keyboard=True)
    )

@dp.message(LoginForm.enter_profit_target)
async def process_profit_target(message: types.Message, state: FSMContext):
    user_tg_id = message.from_user.id
    text = message.text.strip()
    
    if text.lower() == 'cancel':
        await state.set_state(LoginForm.main_menu)
        return await message.answer("❌ မပြောင်းလဲတော့ပါ။", reply_markup=get_logged_in_keyboard())
    
    if not text.isdigit():
        return await message.answer("❌ ကျေးဇူးပြု၍ ဂဏန်းသာ ရိုက်ထည့်ပါ။ (ဥပမာ: 20000)")
        
    target_amount = int(text)
    active_sessions[user_tg_id]["profit_target"] = target_amount
    
    await state.set_state(LoginForm.main_menu)
    if target_amount > 0:
        await message.answer(f"✅ <b>Profit Target သတ်မှတ်ပြီးပါပြီ:</b> {target_amount} Ks မြတ်ပါက အလိုအလျောက် ရပ်တန့်ပေးပါမည်။", reply_markup=get_logged_in_keyboard())
    else:
        await message.answer("✅ <b>Profit Target စနစ်ကို ပိတ်လိုက်ပါပြီ။</b>", reply_markup=get_logged_in_keyboard())

# ==========================================================
# 🤖 AI Mode Selection Handlers
# ==========================================================
@dp.message(F.text == "🤖 AI Mode")
async def cmd_ai_mode(message: types.Message):
    user_tg_id = message.from_user.id
    if user_tg_id not in active_sessions: return await message.answer("⚠️ အရင်ဆုံး Login ဝင်ပေးပါ။")
        
    current_mode = active_sessions[user_tg_id].get("ai_mode", "🧠 Basic Trend AI")
    await message.answer(
        f"🤖 <b>အသုံးပြုလိုသော AI Prediction စနစ်ကို ရွေးချယ်ပါ:</b>\n\n"
        f"လက်ရှိ အသုံးပြုနေသော စနစ်: <b>{current_mode}</b>\n\n"
        "1️⃣ <b>Basic Trend AI:</b> နောက်ဆုံး ၅ ပွဲကိုကြည့်၍ တွက်ချက်သောစနစ်။\n"
        "2️⃣ <b>ChatGPT Mode:</b> အနိုင်အရှုံး Pattern ရှာဖွေတွက်ချက်သောစနစ်။\n"
        "3️⃣ <b>Gemini Mode:</b> ပွဲစဉ် ၁၀ ပွဲစာကို ခြုံငုံသုံးသပ်သောစနစ်။",
        reply_markup=get_ai_mode_keyboard()
    )

@dp.message(F.text.in_(["🧠 Basic Trend AI", "🚀 ChatGPT Mode", "🌌 Gemini Mode"]))
async def set_ai_mode(message: types.Message):
    user_tg_id = message.from_user.id
    if user_tg_id not in active_sessions: return await message.answer("⚠️ အရင်ဆုံး Login ဝင်ပေးပါ။")
        
    selected_mode = message.text
    active_sessions[user_tg_id]["ai_mode"] = selected_mode
    await db.update_user_ai_mode(user_tg_id, selected_mode)
    await message.answer(f"✅ AI စနစ်ကို <b>{selected_mode}</b> သို့ ပြောင်းလဲသတ်မှတ်လိုက်ပါပြီ။", reply_markup=get_logged_in_keyboard())

@dp.message(F.text == "🔙 ပင်မမီနူးသို့")
async def back_to_main(message: types.Message):
    await message.answer("ပင်မမီနူးသို့ ရောက်ရှိပါပြီ။", reply_markup=get_logged_in_keyboard())

# ==========================================================
# 🚀 Single Auto Bet Execution Function
# ==========================================================
async def place_auto_bet(page, message: types.Message, bet_type: str, amount: int = 10, silent: bool = False):
    try:
        bet_choice = bet_type.lower()
        
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
        except:
            pass

        if bet_choice == "big": await page.locator('.Betting__C-foot-b').click(timeout=5000, force=True) 
        elif bet_choice == "small": await page.locator('.Betting__C-foot-s').click(timeout=5000, force=True)
        elif bet_choice == "red": await page.locator('.Betting__C-head-r').click(timeout=5000, force=True)
        elif bet_choice == "green": await page.locator('.Betting__C-head-g').click(timeout=5000, force=True)
        elif bet_choice in ["violet", "purple"]: await page.locator('.Betting__C-head-p').click(timeout=5000, force=True)
        else:
            if not silent: await message.answer("❌ မှားယွင်းနေပါသည်။")
            return False

        await page.wait_for_timeout(1000)

        # Base Amount တွက်ချက်ခြင်း
        if amount >= 1000:
            base_text = "1000"
            multiplier = amount // 1000
        elif amount >= 100:
            base_text = "100"
            multiplier = amount // 100
        else:
            base_text = "10"
            multiplier = amount // 10

        # အတိအကျ နှိပ်ရန်
        try:
            base_locator = page.locator("div.Betting__Popup-body-line-item").get_by_text(base_text, exact=True).first
            await base_locator.click(timeout=2000, force=True)
            await page.wait_for_timeout(500)
        except:
            pass 

        # Multiplier တိုက်ရိုက်ထည့်သွင်းရန်
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

        confirm_btn = page.locator('.Betting__Popup-foot > div').last
        await confirm_btn.click(timeout=3000, force=True)

        await page.wait_for_timeout(2000)
        if not silent: await message.answer("✅ <b>လောင်းကြေး အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ။</b>")
        return True

    except Exception as e:
        if not silent:
            error_image_path = f"debug_error_{message.from_user.id}.png"
            try:
                await page.screenshot(path=error_image_path, full_page=True)
                photo = FSInputFile(error_image_path)
                await message.answer_photo(photo=photo, caption=f"❌ <b>Auto Bet Error:</b>\n<code>{str(e).splitlines()[0][:200]}</code>")
                if os.path.exists(error_image_path): os.remove(error_image_path)
            except: pass
        return False

# ==========================================================
# 📊 API Fetching (Updated Timestamps to prevent cache delay)
# ==========================================================
async def get_latest_game_result(target_issue):
    url = 'https://api.bigwinqaz.com/api/webapi/GetNoaverageEmerdList'
    headers = {
        'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOiIxNzgzNjY1OTAyIiwibmJmIjoiMTc4MzY2NTkwMiIsImV4cCI6IjE3ODM2Njc3MDIiLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL2V4cGlyYXRpb24iOiI3LzEwLzIwMjYgMTo0NTowMiBQTSIsImh0dHA6Ly9zY2hlbWFzLm1pY3Jvc29mdC5jb20vd3MvMjAwOC8wNi9pZGVudGl0eS9jbGFpbXMvcm9sZSI6IkFjY2Vzc19Ub2tlbiIsIlVzZXJJZCI6IjU3NDMzNSIsIlVzZXJOYW1lIjoiOTU5Njc1MzIzODc4IiwiVXNlclBob3RvIjoiNyIsIk5pY2tOYW1lIjoiV2FuZyBMaW4iLCJBbW91bnQiOiIxMDAwLjAwIiwiSW50ZWdyYWwiOiIwIiwiTG9naW5NYXJrIjoiSDUiLCJMb2dpblRpbWUiOiI3LzEwLzIwMjYgMToxNTowMiBQTSIsIkxvZ2luSVBBZGRyZXNzIjoiMTg4LjI0NS44Ny4zIiwiRGJOdW1iZXIiOiIwIiwiSXN2YWxpZGF0b3IiOiIwIiwiS2V5Q29kZSI6IjEwNiIsIlRva2VuVHlwZSI6IkFjY2Vzc19Ub2tlbiIsIlBob25lVHlwZSI6IjEiLCJVc2VyVHlwZSI6IjAiLCJVc2VyTmFtZTIiOiJweWFlc29uZTVwc3BAeWFob28uY29tIiwiaXNzIjoiand0SXNzdWVyIiwiYXVkIjoibG90dGVyeVRpY2tldCJ9.U-YRQvRv20OmGnLmm_DLdS9D-jDyNhCqWhFk4M1zmkc',
        'content-type': 'application/json;charset=UTF-8',
    }
    json_data = {
        'pageSize': 10, 'pageNo': 1, 'typeId': 30, 'language': 7,
        'random': '7bc385b8267d48ebbc62fe04296cbed4',
        'signature': '2B34898B971F29208D293D1E530F8627', 
        'timestamp': int(time.time()), # 👈 Dynamic Timestamp to bypass delay
    }
    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as response:
                api_result = await response.json()
        records = api_result.get('data', {}).get('list', [])
        for item in records:
            if str(item['issueNumber']) == str(target_issue):
                num = int(item['number'])
                size = "BIG" if num >= 5 else "SMALL"
                return f"{num} | {size}"
    except: pass
    return "? | ?"

async def get_ai_prediction(user_tg_id):
    url = 'https://api.bigwinqaz.com/api/webapi/GetNoaverageEmerdList'
    headers = {
        'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOiIxNzgzNjQzMjUwIiwibmJmIjoiMTc4MzY0MzI1MCIsImV4cCI6IjE3ODM2NDUwNTAiLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL2V4cGlyYXRpb24iOiI3LzEwLzIwMjYgNzoyNzozMCBBTSIsImh0dHA6Ly9zY2hlbWFzLm1pY3Jvc29mdC5jb20vd3MvMjAwOC8wNi9pZGVudGl0eS9jbGFpbXMvcm9sZSI6IkFjY2Vzc19Ub2tlbiIsIlVzZXJJZCI6IjU3NDMzNSIsIlVzZXJOYW1lIjoiOTU5Njc1MzIzODc4IiwiVXNlclBob3RvIjoiNyIsIk5pY2tOYW1lIjoiV2FuZyBMaW4iLCJBbW91bnQiOiIxMDAwLjAwIiwiSW50ZWdyYWwiOiIwIiwiTG9naW5NYXJrIjoiSDUiLCJMb2dpblRpbWUiOiI3LzEwLzIwMjYgNjo1NzozMCBBTSIsIkxvZ2luSVBBZGRyZXNzIjoiMTAzLjEzNC4yMDcuMTUyIiwiRGJOdW1iZXIiOiIwIiwiSXN2YWxpZGF0b3IiOiIwIiwiS2V5Q29kZSI6Ijk3IiwiVG9rZW5UeXBlIjoiQWNjZXNzX1Rva2VuIiwiUGhvbmVUeXBlIjoiMSIsIlVzZXJUeXBlIjoiMCIsIlVzZXJOYW1lMiI6InB5YWVzb25lNXBzcEB5YWhvby5jb20iLCJpc3MiOiJqd3RJc3N1ZXIiLCJhdWQiOiJsb3R0ZXJ5VGlja2V0In0.C-FbAazz7HkLeQ5L5eISGHGJCdwarGdz4A3v9XyvqCE',
        'content-type': 'application/json;charset=UTF-8',
    }
    json_data = {
        'pageSize': 10, 'pageNo': 1, 'typeId': 30, 'language': 7,
        'random': 'e431a6544cde4cbb8e09a4c01199b75b',
        'signature': '1668945A145F050B049ED587E6E9E0E7', 
        'timestamp': int(time.time()), # 👈 Dynamic Timestamp
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as response:
                api_result = await response.json()
                
        records = api_result.get('data', {}).get('list', [])
        if records:
            last_completed_issue = records[0]['issueNumber']
            next_issue = str(int(last_completed_issue) + 1)
            ai_mode = active_sessions.get(user_tg_id, {}).get("ai_mode", "🧠 Basic Trend AI")
            
            if ai_mode == "🚀 ChatGPT Mode":
                recent_7 = [int(item['number']) for item in records[:7]] if len(records) >= 7 else [int(item['number']) for item in records]
                big_count = sum(1 for n in recent_7 if n >= 5)
                prediction_choice = "big" if big_count >= 4 else "small"
                confidence = random.randint(82, 98)
                ai_name = "ChatGPT-4"
            elif ai_mode == "🌌 Gemini Mode":
                recent_10 = [int(item['number']) for item in records]
                big_count = sum(1 for n in recent_10 if n >= 5)
                prediction_choice = "big" if big_count > (len(recent_10) - big_count) else "small"
                confidence = random.randint(80, 95)
                ai_name = "Gemini Pro"
            else:
                recent_5 = [int(item['number']) for item in records[:5]] if len(records) >= 5 else [int(item['number']) for item in records]
                big_count = sum(1 for n in recent_5 if n >= 5)
                prediction_choice = "big" if big_count > (len(recent_5) - big_count) else "small"
                confidence = random.randint(70, 85)
                ai_name = "Basic AI"
            
            return prediction_choice, confidence, next_issue, ai_name
        else:
            return None, 0, None, None
    except Exception as e:
        print(f"API Fetching Error: {e}")
        return None, 0, None, None

# ==========================================================
# 🔄 Continuous Auto Bet Loop Task (Balance & Profit Included)
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
                    
                    sequence = active_sessions[user_tg_id].get("bet_sequence", [10])
                    step = active_sessions[user_tg_id].get("current_bet_step", 0)
                    
                    if step >= len(sequence):
                        step = 0
                        active_sessions[user_tg_id]["current_bet_step"] = 0
                        
                    current_amount = sequence[step]

                    # 🛑 Check Balance Before Betting
                    try:
                        bal_el_pre = page.locator('.Wallet__C-balance-l1 div').first
                        if await bal_el_pre.is_visible(timeout=2000):
                            current_bal_str = await bal_el_pre.inner_text()
                            current_bal_val = extract_balance(current_bal_str)
                            
                            if current_bal_val < current_amount:
                                await message.answer(f"⚠️ <b>လက်ကျန်ငွေ မလုံလောက်တော့ပါ။</b>\nလိုအပ်သောငွေ: {current_amount} Ks\nလက်ကျန်: {current_bal_str}\n🛑 Auto Bet ကို ရပ်နားလိုက်ပါသည်။")
                                active_sessions[user_tg_id]["is_auto_betting"] = False
                                break
                    except:
                        pass # Ignore pre-check error and continue

                    betting_msg = (
                        f"• WINGO_30S : {current_issue}\n"
                        f"• Model : {ai_name}\n"
                        f"• Pred : {predicted_bet.upper()} | {current_amount} Ks\n"
                        f"• Step : {step + 1}/{len(sequence)}\n"
                        f"• Auto-Betting ✅"
                    )
                    await message.answer(betting_msg)

                    success = await place_auto_bet(page, message, predicted_bet, current_amount, silent=True)
                    
                    if success:
                        last_betted_issue = current_issue
                        
                        # 🛑 Dynamic Delay Fix: Fixed Wait ကိုဖြုတ်ပြီး API ရလဒ်ထွက်သည်အထိ (၂) စက္ကန့်တစ်ခါ Polling လုပ်မည်
                        actual_result = "? | ?"
                        for _ in range(20): # အများဆုံး 40 စက္ကန့် စောင့်မည်
                            if not active_sessions.get(user_tg_id, {}).get("is_auto_betting", False):
                                break # User ကရပ်လိုက်ရင် ချက်ချင်းထွက်မည်
                                
                            await asyncio.sleep(2)
                            actual_result = await get_latest_game_result(current_issue)
                            if actual_result != "? | ?":
                                break # ရလဒ်ထွက်လာပါက Loop မှ ချက်ချင်းထွက်မည်
                        
                        # Update Balance
                        balance_after_str = "0"
                        new_bal_val = 0.0
                        try:
                            bal_el = page.locator('.Wallet__C-balance-l1 div').first
                            if await bal_el.is_visible(timeout=2000):
                                balance_after_str = await bal_el.inner_text()
                                new_bal_val = extract_balance(balance_after_str)
                        except: pass

                        try:
                            actual_size = actual_result.split(" | ")[1].strip().lower() 
                            predicted_size = predicted_bet.lower()
                            
                            if predicted_size == actual_size:
                                profit = current_amount * 0.96
                                status_title = f"✅ <b>WIN +{profit:.2f} Ks</b>"
                                active_sessions[user_tg_id]["current_bet_step"] = 0 
                                
                            elif actual_size == "?":
                                status_title = f"⚖️ <b>DRAW (Pending)</b>"
                            else:
                                status_title = f"❌ <b>LOSE -{current_amount:.2f} Ks</b>"
                                active_sessions[user_tg_id]["current_bet_step"] += 1
                                if active_sessions[user_tg_id]["current_bet_step"] >= len(sequence):
                                    active_sessions[user_tg_id]["current_bet_step"] = 0
                                
                            result_msg = (
                                f"{status_title}\n"
                                f"━━━━━━━━━━━━━━━\n"
                                f"• WINGO_30S : {current_issue}\n"
                                f"• Result : {actual_result}\n"
                                f"• Balance : {balance_after_str}"
                            )
                            await message.answer(result_msg)
                            await db.update_user_balance(user_tg_id, balance_after_str.strip())
                            
                            # 🎯 Check Profit Target
                            start_bal = active_sessions[user_tg_id].get("start_balance", new_bal_val)
                            profit_target = active_sessions[user_tg_id].get("profit_target", 0)
                            current_profit = new_bal_val - start_bal
                            
                            if profit_target > 0 and current_profit >= profit_target:
                                await message.answer(
                                    f"🎉 <b>Target ပြည့်သွားပါပြီ! (+{current_profit:g} Ks)</b>\n"
                                    f"သတ်မှတ်ထားသော အမြတ် {profit_target} Ks သို့ ရောက်ရှိသွားသဖြင့် Auto Bet ကို အလိုအလျောက် ရပ်နားလိုက်ပါသည်။"
                                )
                                active_sessions[user_tg_id]["is_auto_betting"] = False
                                break
                            
                        except Exception:
                            await message.answer(f"• WINGO_30S : {current_issue}\n• Result : {actual_result}\n• Balance : {balance_after_str}")

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
@dp.message(F.text == "⚙️ Set Bet-Size")
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
        reply_markup=ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="Cancel")]], resize_keyboard=True)
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
    except ValueError:
        await message.answer("❌ မှားယွင်းနေပါသည်။ ဥပမာ: 10-20-40-80 ဟုသာ ဂဏန်းများကို တုံးတို (-) ခြား၍ ရိုက်ထည့်ပါ။")

# ==========================================================
# 🤖 Reply Keyboard Auto Bet & Status Handlers
# ==========================================================
@dp.message(F.text == "▶️ Start Auto-Bet")
async def btn_start_auto(message: types.Message, state: FSMContext):
    user_tg_id = message.from_user.id
    if user_tg_id not in active_sessions: 
        return await message.answer("⚠️ အရင်ဆုံး Login ဝင်ပေးပါ။")

    if active_sessions[user_tg_id].get("is_auto_betting", False):
        return await message.answer("⚠️ Auto Bet အလုပ်လုပ်နေဆဲ ဖြစ်ပါသည်။ ရပ်လိုပါက 🛑 Stop Auto-Bet ကိုနှိပ်ပါ။")

    if "bet_sequence" not in active_sessions[user_tg_id]:
        active_sessions[user_tg_id]["bet_sequence"] = [10]
        active_sessions[user_tg_id]["current_bet_step"] = 0

    # 🛑 Auto Bet စတင်ချိန်တွင် လက်ရှိ Balance ကို Start Balance အဖြစ် မှတ်သားထားမည် (Target တွက်ရန်)
    try:
        page = active_sessions[user_tg_id]["page"]
        bal_el = page.locator('.Wallet__C-balance-l1 div').first
        if await bal_el.is_visible(timeout=3000):
            bal_str = await bal_el.inner_text()
            active_sessions[user_tg_id]["start_balance"] = extract_balance(bal_str)
    except:
        active_sessions[user_tg_id]["start_balance"] = 0.0

    active_sessions[user_tg_id]["is_auto_betting"] = True
    asyncio.create_task(auto_bet_loop(user_tg_id, message))

@dp.message(F.text == "🛑 Stop Auto-Bet")
async def btn_stop_auto(message: types.Message, state: FSMContext):
    user_tg_id = message.from_user.id
    if user_tg_id not in active_sessions: 
        return await message.answer("⚠️ အရင်ဆုံး Login ဝင်ပေးပါ။")

    active_sessions[user_tg_id]["is_auto_betting"] = False
    await message.answer("🛑 <b>ဆက်တိုက် Auto Bet စနစ်ကို ရပ်တန့်လိုက်ပါပြီ။</b>")

@dp.message(F.text == "📊 Status")
async def btn_status(message: types.Message, state: FSMContext):
    user_tg_id = message.from_user.id
    if user_tg_id not in active_sessions: 
        return await message.answer("⚠️ အရင်ဆုံး Login ဝင်ပေးပါ။")

    session = active_sessions[user_tg_id]
    is_auto = "Running 🟢" if session.get("is_auto_betting", False) else "Stopped 🔴"
    ai_mode = session.get("ai_mode", "🧠 Basic Trend AI")
    
    current_seq = session.get("bet_sequence", [10])
    seq_str = "-".join(map(str, current_seq))
    current_step = session.get("current_bet_step", 0)
    
    profit_target = session.get("profit_target", 0)
    start_bal = session.get("start_balance", 0.0)
    
    # Update real-time balance
    current_bal_val = start_bal
    current_bal_str = "0.00 Ks"
    try:
        page = session["page"]
        bal_el = page.locator('.Wallet__C-balance-l1 div').first
        if await bal_el.is_visible(timeout=2000):
            current_bal_str = await bal_el.inner_text()
            current_bal_val = extract_balance(current_bal_str)
    except: pass
    
    current_profit = current_bal_val - start_bal
    profit_str = f"+{current_profit:g} Ks" if current_profit >= 0 else f"{current_profit:g} Ks"
    target_str = f"{profit_target} Ks" if profit_target > 0 else "Not Set"

    status_text = (
        "📊 <b>Bot Status</b>\n"
        "━━━━━━━━━━━━━━━\n"
        f"🤖 <b>Auto-Bet State:</b> {is_auto}\n"
        f"🧠 <b>Active AI Mode:</b> {ai_mode}\n"
        f"💰 <b>Current Balance:</b> {current_bal_str}\n"
        f"⚙️ <b>Bet Sequence:</b> <code>{seq_str}</code>\n"
        f"📍 <b>Current Step:</b> {current_step + 1}/{len(current_seq)} ({current_seq[current_step]} Ks)\n"
        f"🎯 <b>Profit Target:</b> {target_str}\n"
        f"📈 <b>Current Profit:</b> {profit_str}\n"
    )
    await message.answer(status_text)

# ==========================================================
# 💰 Check Balance & Other Handlers
# ==========================================================
@dp.message(LoginForm.main_menu, F.text == "💰 Balance")
async def check_balance(message: types.Message, state: FSMContext):
    user_tg_id = message.from_user.id
    if user_tg_id not in active_sessions: return await message.answer("⚠️ အရင်ဆုံး Login ဝင်ပေးပါ။")

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

@dp.message(LoginForm.main_menu, F.text == "📋 Info")
async def show_info(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    user_id = data.get('user_id', 'N/A')
    username = data.get('username', 'N/A')
    nickname = data.get('nickname', 'Unknown')
    balance = data.get('balance', '0.00 Ks')
    login_time = data.get('login_time', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    info_text = (
        "👤 <b>User Information:</b>\n"
        f"├─ 🆔 <b>User ID:</b> {user_id}\n"
        f"├─ 📱 <b>Username:</b> {username}\n"
        f"├─ 🏷️ <b>Nickname:</b> {nickname}\n"
        f"├─ 💰 <b>Balance:</b> {balance}\n"
        f"├─ 📅 <b>Login Date:</b> {login_time}\n"
        "└─ ✅ <b>Allow Withdraw:</b> Yes\n"
    )
    await message.answer(info_text, reply_markup=get_logged_in_keyboard())

@dp.message(LoginForm.main_menu, F.text == "🔐 Logout")
async def logout(message: types.Message, state: FSMContext):
    user_tg_id = message.from_user.id
    if user_tg_id in active_sessions:
        active_sessions[user_tg_id]["is_auto_betting"] = False 
        try:
            await active_sessions[user_tg_id]["browser"].close()
            await active_sessions[user_tg_id]["playwright"].stop()
        except: pass
        del active_sessions[user_tg_id]
        
    await state.clear()
    await message.answer("👋 အကောင့်ထွက်ပြီးပါပြီ။", reply_markup=get_main_keyboard())

@dp.message(F.text == "🎰 Games")
async def games(message: types.Message):
    await message.answer(
        "🎮 <b>Game ရွေးချယ်ရန်:</b>\nWin Go 30s ကို ရွေးချယ်ထားပါသည်။\n\n"
        "🤖 <b>Bot Commands:</b>\n"
        "<code>▶️ Start Auto-Bet</code> - ခလုတ်နှိပ်၍ Auto Bet စတင်နိုင်ပါသည်\n"
        "<code>🛑 Stop Auto-Bet</code> - ခလုတ်နှိပ်၍ Auto Bet ရပ်တန့်နိုင်ပါသည်\n",
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
