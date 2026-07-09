import asyncio
import os
import html
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

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

class LoginForm(StatesGroup):
    select_site = State()
    enter_phone = State()
    enter_password = State()
    main_menu = State() # Login ပြီးသွားရင် ဒီ State ကိုရောက်မယ်

# ==========================================
# Custom Keyboards
# ==========================================
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔐 Login")],
            [KeyboardButton(text="🎰 Games")]
        ],
        resize_keyboard=True
    )

def get_site_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="777BIGWIN")],
            [KeyboardButton(text="🔙 နောက်သို့")]
        ],
        resize_keyboard=True
    )

# 🔥 Login ပြီးသွားရင် ဒီ Keyboard ပေါ်လာမယ်
def get_logged_in_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="📋 Info")],      # ဒီခလုတ်ကို နှိပ်မှ Data ပြမယ်
            [KeyboardButton(text="🎰 Games")],
            [KeyboardButton(text="🔐 Logout")]
        ],
        resize_keyboard=True
    )

# ==========================================
# Command Handlers
# ==========================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("👋 <b>မင်္ဂလာပါ!</b>\nအကောင့်ဝင်ရန် Login ကိုနှိပ်ပါ။", reply_markup=get_main_keyboard())

# ==========================================
# Login Flow
# ==========================================
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

# ==========================================
# Playwright Logic (Login စစ်ဆေးရုံပဲ)
# ==========================================
@dp.message(LoginForm.enter_password)
async def process_password(message: types.Message, state: FSMContext):
    password = message.text
    data = await state.get_data()
    username = data.get('phone')
    site = data.get('site')
    
    loading_msg = await message.answer("🔄 <b>အကောင့်ဝင်နေပါသည်... ခဏစောင့်ပါ...</b>")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36", 
            viewport={'width': 390, 'height': 844}, 
            is_mobile=True
        )
        page = await context.new_page()
        
        try:
            await page.goto("https://www.777bigwingame.app/#/login", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(2000)

            await page.fill('input[name="userNumber"]', username)
            password_input = await page.query_selector('input[placeholder="စကားဝှက်"], input[placeholder="Password"]')
            if password_input:
                await password_input.fill(password)
            
            await page.wait_for_timeout(2000)
            await page.evaluate("""
                () => {
                    let btn = document.querySelector('button.active') || document.querySelector('button[type="submit"]');
                    if (btn) btn.click();
                }
            """)
            
            await page.wait_for_timeout(8000)

            # Popup ရှိရင် ပိတ်မယ် (ပုံထဲကအတိုင်း)
            try:
                close_selector = ".announcement-dialog__button"
                for _ in range(5):
                    btn = await page.query_selector(close_selector)
                    if btn:
                        await btn.click()
                        await page.wait_for_timeout(1000)
                    else:
                        break
            except:
                pass
            
            # URL စစ်ဆေးခြင်း
            if "login" not in page.url.lower():
                # ✅ Login အောင်မြင်ကြောင်းပဲ ပြီး Data မပြဘူး
                await message.answer(
                    "✅ <b>LOGIN SUCCESSFUL</b>\n\n"
                    "သင့်အကောင့်အချက်အလက်များကို ကြည့်ရှုရန် အောက်ပါ <b>📋 Info</b> ခလုတ်ကို နှိပ်ပါ။",
                    reply_markup=get_logged_in_keyboard()
                )
                
                # 🔥 Data တွေကို State ထဲမှာ သိမ်းထားမယ်
                await state.update_data(
                    is_logged_in=True,
                    username=username,
                    site=site
                )
                await state.set_state(LoginForm.main_menu)
                
            else:
                await message.answer("❌ <b>Login မအောင်မြင်ပါ။</b>", reply_markup=get_main_keyboard())
                await state.clear()

            await loading_msg.delete()

        except Exception as e:
            await message.answer(f"⚠️ Error: {html.escape(str(e))}", reply_markup=get_main_keyboard())
            await state.clear()
            await loading_msg.delete()
        finally:
            await browser.close()

# ==========================================
# 📋 Info Button (ဒီခလုတ်နှိပ်မှ Data တွေပြမယ်)
# ==========================================
@dp.message(LoginForm.main_menu, F.text == "📋 Info")
async def show_info(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    # State ထဲက Data တွေကို ထုတ်ယူမယ်
    username = data.get('username', 'N/A')
    site = data.get('site', 'N/A')
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    info_text = (
        "👤 <b>User Information:</b>\n"
        "├─ 🆔 <b>User ID:</b> \n"
        "├─ 📱 <b>Username:</b> {username}\n"
        "├─ 🏷️ <b>Nickname:</b> \n"
        "├─ 💰 <b>Balance:</b> 0.00 Ks\n"
        "├─ 📅 <b>Login Date:</b> {current_time}\n"
        "└─ ✅ <b>Allow Withdraw:</b> Yes\n"
    ).format(username=username, current_time=current_time)
    
    await message.answer(info_text, reply_markup=get_logged_in_keyboard())

# ==========================================
# Logout / Games
# ==========================================
@dp.message(LoginForm.main_menu, F.text == "🔐 Logout")
async def logout(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("👋 အကောင့်ထွက်ပြီးပါပြီ။", reply_markup=get_main_keyboard())

@dp.message(F.text == "🎰 Games")
async def games(message: types.Message):
    await message.answer("🎮 <b>Game ရွေးချယ်ရန်:</b>\n(နောက်ပိုင်း ဒီနေရာမှာ Game Logic ထည့်သွင်းသွားမှာပါ)", reply_markup=get_main_keyboard())

# ==========================================
# Main
# ==========================================
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
