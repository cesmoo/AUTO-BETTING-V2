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
    main_menu = State()

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
            [KeyboardButton(text="📋 Info")], 
            [KeyboardButton(text="🎰 Games")],
            [KeyboardButton(text="🔐 Logout")]
        ],
        resize_keyboard=True
    )

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
# 🔥 Playwright Logic: Login + Data Scraping & Save to State
# ==========================================================
@dp.message(LoginForm.enter_password)
async def process_password(message: types.Message, state: FSMContext):
    password = message.text
    data = await state.get_data()
    username = data.get('phone')
    
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
            
            # Data များ Load ရန် စောင့်ခြင်း
            await page.wait_for_timeout(8000)
            
            # Popup ပိတ်ခြင်း
            try:
                close_selector = ".announcement-dialog__button"
                for _ in range(5):
                    btn = await page.query_selector(close_selector)
                    if btn:
                        await btn.click()
                        await page.wait_for_timeout(1000)
                    else:
                        break
                await page.wait_for_timeout(2000)
            except:
                pass
            
            if "login" not in page.url.lower():
                
                # ==========================================================
                # 🔥 ဒီနေရာမှာ Data တွေကို DOM ထဲကနေ ဆွဲထုတ်ပြီး State ထဲ သိမ်းမယ်
                # ==========================================================
                user_id = "N/A"
                nickname = "Unknown"
                balance_text = "0.00 Ks"
                site_login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                try:
                    # Selector တွေကို သင့်ရဲ့ DOM Screenshot အတိုင်း ထားပေးထားပါတယ်
                    uid_el = await page.query_selector('.userInfo__container-content-uid > span:nth-child(3)')
                    if uid_el: user_id = await uid_el.inner_text()

                    nickname_el = await page.query_selector('.userInfo__container-content-nickname h3')
                    if nickname_el: nickname = await nickname_el.inner_text()
                    
                    balance_el = await page.query_selector('.totalSavings__container-header-box .balance_info p span')
                    if balance_el: balance_text = await balance_el.inner_text()
                    
                    logintime_el = await page.query_selector('.userInfo__container-content-logintime > span:nth-child(2)')
                    if logintime_el: site_login_time = await logintime_el.inner_text()

                except Exception as e:
                    print(f"Scraping Error: {e}")

                # ✅ State ထဲမှာ Data တွေကို သိမ်းဆည်းလိုက်တယ်
                await state.update_data(
                    is_logged_in=True,
                    username=username,
                    user_id=user_id.strip(),
                    nickname=nickname.strip(),
                    balance=balance_text.strip(),
                    login_time=site_login_time.strip()
                )

                await message.answer(
                    "✅ <b>LOGIN SUCCESSFUL</b>\n\n"
                    "သင့်အကောင့်အချက်အလက်များကို ကြည့်ရှုရန် အောက်ပါ <b>📋 Info</b> ခလုတ်ကို နှိပ်ပါ။",
                    reply_markup=get_logged_in_keyboard()
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

# ==========================================================
# 📋 Info Button (State ထဲက သိမ်းထားတဲ့ Data တွေကို ပြမယ်)
# ==========================================================
@dp.message(LoginForm.main_menu, F.text == "📋 Info")
async def show_info(message: types.Message, state: FSMContext):
    data = await state.get_data()
    
    user_id = data.get('user_id', '')
    username = data.get('username', 'N/A')
    nickname = data.get('nickname', '')
    balance = data.get('balance', '0.00 Ks')
    login_time = data.get('login_time', datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    info_text = (
        "👤 <b>User Information:</b>\n"
        "├─ 🆔 <b>User ID:</b> {user_id}\n"
        "├─ 📱 <b>Username:</b> {username}\n"
        "├─ 🏷️ <b>Nickname:</b> {nickname}\n"
        "├─ 💰 <b>Balance:</b> {balance}\n"
        "├─ 📅 <b>Login Date:</b> {login_time}\n"
        "└─ ✅ <b>Allow Withdraw:</b> Yes\n"
    ).format(
        user_id=user_id, 
        username=username, 
        nickname=nickname, 
        balance=balance, 
        login_time=login_time
    )
    
    await message.answer(info_text, reply_markup=get_logged_in_keyboard())

@dp.message(LoginForm.main_menu, F.text == "🔐 Logout")
async def logout(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("👋 အကောင့်ထွက်ပြီးပါပြီ။", reply_markup=get_main_keyboard())

@dp.message(F.text == "🎰 Games")
async def games(message: types.Message):
    await message.answer("🎮 <b>Game ရွေးချယ်ရန်:</b>", reply_markup=get_main_keyboard())

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
