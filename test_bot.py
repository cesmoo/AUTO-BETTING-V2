import asyncio
import os
import html
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
    loading_msg = await message.answer("🔄 <b>Logging in... (ခဏစောင့်ပါ)</b>", reply_markup=get_main_keyboard())
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

            await page.fill('input[name="userNumber"]', username)
            pwd_el = await page.query_selector('input[placeholder="စကားဝှက်"], input[placeholder="Password"]')
            if pwd_el: await pwd_el.fill(password)
            
            await page.evaluate("""
                () => {
                    let btn = document.querySelector('button.active') || document.querySelector('button[type="submit"]');
                    if (btn) btn.click();
                }
            """)
            
            # 🔥 Data Load ဖို့ အချိန် ၁၅ စက္ကန့် စောင့်မယ်
            await page.wait_for_timeout(15000)
            
            screenshot_path = "result.png"
            await page.screenshot(path=screenshot_path)
            
            if "login" not in page.url.lower():
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 🔎 Robust Data Scraping (ပိုမိုတိကျအောင် ပြင်ထားတယ်)
                try:
                    # 1. Nickname (Class ထဲမှာ 'nickname' ပါတာ အကုန်ရှာမယ်)
                    nickname_el = await page.query_selector('.userInfo__container-content-nickname h3, [class*="nickname"] h3, h3')
                    nickname = await nickname_el.inner_text() if nickname_el else "Unknown"
                    
                    # 2. User ID (id="customerId" နဲ့ မတွေ့ရင် Text နဲ့ရှာမယ့် Logic)
                    user_id = "N/A"
                    uid_el = await page.query_selector('#customerId')
                    if uid_el:
                        user_id = await uid_el.inner_text()
                    else:
                        # Page ထဲမှာ "User ID:" ဆိုတဲ့ စာသားနောက်က နံပါတ်ကို ဆွဲမယ်
                        content = await page.content()
                        uid_match = re.search(r'User ID[:\s]*(\d+)', content)
                        if uid_match: user_id = uid_match.group(1)
                    
                    # 3. Balance (ပိုမိုတိကျအောင်)
                    balance_text = "0.00 Ks"
                    balance_el = await page.query_selector('[class*="balance"], .userInfo__container-content [class*="money"]')
                    if balance_el:
                        balance_text = await balance_el.inner_text()
                    else:
                        content = await page.content()
                        bal_match = re.search(r'(\d+\.?\d*)\s*Ks', content)
                        if bal_match: balance_text = f"{bal_match.group(1)} Ks"

                except Exception as e:
                    nickname, user_id, balance_text = "Error", "Error", "0.00 Ks"

                nickname = nickname.strip()
                user_id = user_id.strip()

                success_text = (
                    "✅ <b>LOGIN SUCCESSFUL</b>\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    "🌍 <b>Site:</b> 777BIGWIN\n"
                    "👤 <b>User Information:</b>\n"
                    "├─ 🆔 <b>User ID:</b> {user_id}\n"
                    "├─ 📱 <b>Username:</b> {username}\n"
                    "├─ 🏷️ <b>Nickname:</b> <i>{nickname}</i>\n"
                    "├─ 💰 <b>Balance:</b> <i>{balance}</i>\n"
                    "├─ 📅 <b>Login Date:</b> <i>{current_time}</i>\n"
                    "└─ ✅ <b>Allow Withdraw:</b> Yes\n"
                    "━━━━━━━━━━━━━━━━━━\n"
                    "💎 Auto Bet is available.\n"
                    "Upgrade to Premium for Manual Bet, AI Prediction!\n\n"
                    "⚡ <b>Select your betting mode below:</b>"
                ).format(user_id=user_id, username=username, nickname=nickname, balance=balance_text, current_time=current_time)

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
    await message.answer(f"🎮 သင်ရွေးချယ်ထားသော Game: {message.text}", reply_markup=get_main_keyboard())
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
