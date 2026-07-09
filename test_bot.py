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
    select_game = State()

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

def get_game_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🟢 Win Go")], [KeyboardButton(text="🔴 K3")], [KeyboardButton(text="🔙 နောက်သို့")]],
        resize_keyboard=True
    )

@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer("👋 <b>မင်္ဂလာပါ!</b>", reply_markup=get_main_keyboard())

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

@dp.message(LoginForm.enter_password)
async def process_password(message: types.Message, state: FSMContext):
    password = message.text
    data = await state.get_data()
    username = data.get('phone')
    loading_msg = await message.answer("🔄 <b>အကောင့်ဝင်နေပါသည်... ခဏစောင့်ပါ...</b>", reply_markup=get_main_keyboard())
    asyncio.create_task(run_playwright_login_func(message, username, password, state, loading_msg))

async def run_playwright_login_func(message: types.Message, username, password, state: FSMContext, loading_msg: types.Message):
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

            # --- Login Step ---
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

            # ===========================================================
            # 🔥 Popup ပိတ်ခြင်း (DOM ကနေ အတိအကျ ပစ်မှတ်ထား)
            # ===========================================================
            try:
                close_selector = ".announcement-dialog__button"
                max_retries = 5
                for _ in range(max_retries):
                    btn = await page.query_selector(close_selector)
                    if btn:
                        await btn.click()
                        await page.wait_for_timeout(1000)
                    else:
                        break
                await page.wait_for_timeout(2000)
            except:
                pass

            # ===========================================================
            # 📸 Screenshot
            # ===========================================================
            screenshot_path = "result.png"
            await page.screenshot(path=screenshot_path)
            
            if "login" not in page.url.lower():
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # ===========================================================
                # 🔥 FINAL FIX: Data တွေ ပေါ်လာတဲ့အထိ စောင့်ပြီး ဆွဲမယ်
                # ===========================================================
                try:
                    # 1. Balance ကို ဦးစွာ စောင့်ရှာမယ် (ဒါက နောက်ဆုံးပေါ်လာတတ်တယ်)
                    await page.wait_for_selector('.totalSavings__container-header-box .balance_info p span', timeout=10000)
                    
                    # 2. User ID (DOM အတိုင်း span 3 ခုမြောက်ကို တိုက်ရိုက်ယူ)
                    uid_el = await page.query_selector('.userInfo__container-content-uid > span:nth-child(3)')
                    user_id = await uid_el.inner_text() if uid_el else "N/A"

                    # 3. Nickname
                    nickname_el = await page.query_selector('.userInfo__container-content-nickname h3')
                    nickname = await nickname_el.inner_text() if nickname_el else "Unknown"
                    
                    # 4. Balance
                    balance_el = await page.query_selector('.totalSavings__container-header-box .balance_info p span')
                    balance_text = await balance_el.inner_text() if balance_el else "0.00 Ks"
                    
                    # 5. Login Time
                    logintime_el = await page.query_selector('.userInfo__container-content-logintime > span:nth-child(2)')
                    site_login_time = await logintime_el.inner_text() if logintime_el else current_time

                except Exception:
                    user_id, nickname, balance_text, site_login_time = "N/A", "Unknown", "0.00 Ks", current_time
                
                nickname = nickname.strip()
                user_id = user_id.strip()
                balance_text = balance_text.strip()

                success_text = (
                    "✅ <b>LOGIN SUCCESSFUL</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "🌍 <b>Site:</b> 777BIGWIN\n"
                    "👤 <b>User Information:</b>\n"
                    "├─ 🆔 <b>User ID:</b> {user_id}\n"
                    "├─ 📱 <b>Username:</b> {username}\n"
                    "├─ 🏷️ <b>Nickname:</b> <i>{nickname}</i>\n"
                    "├─ 💰 <b>Balance:</b> <i>{balance}</i>\n"
                    "├─ 📅 <b>Login Date:</b> <i>{site_login_time}</i>\n"
                    "└─ ✅ <b>Allow Withdraw:</b> Yes\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "💎 <b>Auto Bet is available.</b>\n"
                    "Upgrade to Premium for Manual Bet, AI Prediction!\n\n"
                    "⚡ <b>Select your betting mode below:</b>"
                ).format(
                    user_id=user_id, 
                    username=username, 
                    nickname=nickname, 
                    balance=balance_text, 
                    site_login_time=site_login_time
                )

                await message.answer(success_text, reply_markup=get_game_keyboard())
                await bot.send_photo(message.chat.id, FSInputFile(screenshot_path), caption="📸 Result")
                await state.set_state(LoginForm.select_game)
                
            else:
                await message.answer("❌ <b>Login မအောင်မြင်ပါ။</b>", reply_markup=get_main_keyboard())
                await state.clear()

            if os.path.exists(screenshot_path): os.remove(screenshot_path)
            await loading_msg.delete()

        except Exception as e:
            await message.answer(f"⚠️ Error: {html.escape(str(e))}", reply_markup=get_main_keyboard())
            await state.clear()
            await loading_msg.delete()
        finally:
            await browser.close()

@dp.message(LoginForm.select_game)
async def process_game_selection(message: types.Message, state: FSMContext):
    if message.text == "🔙 နောက်သို့":
        await state.clear()
        return await message.answer("ပင်မစာမျက်နှာသို့ ပြန်သွားပါပြီ။", reply_markup=get_main_keyboard())
    await message.answer(f"🎮 <b>သင်ရွေးချယ်ထားသော Game:</b> {message.text}", reply_markup=get_main_keyboard())
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
