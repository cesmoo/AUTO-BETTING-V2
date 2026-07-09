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

# State (အဆင့်တွေ) သိမ်းဖို့ storage
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# === အဆင့်များ သတ်မှတ်ခြင်း ===
class LoginForm(StatesGroup):
    select_site = State()
    enter_phone = State()
    enter_password = State()
    select_game = State()  # နောက်ပိုင်း Game ၂ခုအတွက်

# === Keyboards (အောက်ခြေခလုတ်ခုံများ) ===
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔐 Login")],
            [KeyboardButton(text="🎰 Games")] # Game ၂ခုထည့်မယ့်နေရာ
        ],
        resize_keyboard=True
    )
    return keyboard

def get_site_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="777BIGWIN")],
            [KeyboardButton(text="အခြား Site")], # နောက်ပိုင်း ထပ်ထည့်လို့ရ
            [KeyboardButton(text="🔙 နောက်သို့")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_game_keyboard():
    # နောက်ပိုင်း Game နှစ်ခုထပ်ထည့်ဖို့
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🟢 Win Go")],
            [KeyboardButton(text="🔴 K3")],
            [KeyboardButton(text="🔙 နောက်သို့")]
        ],
        resize_keyboard=True
    )
    return keyboard

# === Command Handlers ===
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 <b>မင်္ဂလာပါ!</b>\nအောက်ပါ button များမှ ရွေးချယ်ပါ။",
        reply_markup=get_main_keyboard()
    )

# === Login Flow (Step 1: Site ရွေးပါ) ===
@dp.message(F.text == "🔐 Login")
async def login_start(message: types.Message, state: FSMContext):
    await state.set_state(LoginForm.select_site)
    await message.answer(
        "🌐 <b>Please select a site to login:</b>",
        reply_markup=get_site_keyboard()
    )

# === Login Flow (Step 2: Phone ထည့်ပါ) ===
@dp.message(LoginForm.select_site)
async def process_site(message: types.Message, state: FSMContext):
    if message.text == "🔙 နောက်သို့":
        await state.clear()
        await message.answer("Cancelled.", reply_markup=get_main_keyboard())
        return
    
    # ဒီမှာ site ကို သိမ်းထားနိုင်ပါတယ်
    await state.update_data(site=message.text)
    await state.set_state(LoginForm.enter_phone)
    
    await message.answer(
        "📞 <b>Please enter your phone (or email):</b>\n\n"
        "<i>(Example: 959680090540)</i>",
        reply_markup=ReplyKeyboardRemove() # Keyboard ဖျောက်ပြီး စာရိုက်ခိုင်းမယ်
    )

# === Login Flow (Step 3: Password ထည့်ပါ) ===
@dp.message(LoginForm.enter_phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(LoginForm.enter_password)
    
    await message.answer(
        "🔑 <b>Please enter your password:</b>",
        reply_markup=ReplyKeyboardRemove()
    )

# === Login Flow (Step 4: Run Playwright & Show Result) ===
@dp.message(LoginForm.enter_password)
async def process_password(message: types.Message, state: FSMContext):
    password = message.text
    data = await state.get_data()
    username = data.get('phone')
    
    # Keyboard ပြန်ပေါ်လာအောင်
    await message.answer("🔄 <b>အကောင့်ဝင်နေပါသည်... ခဏစောင့်ပါ...</b>", reply_markup=get_main_keyboard())
    
    # Playwright Login Logic ကို run မယ်
    asyncio.create_task(run_playwright_login_func(message, username, password, state))

# === Playwright Logic (အဓိက စစ်ဆေးတဲ့အပိုင်း) ===
async def run_playwright_login_func(message: types.Message, username, password, state: FSMContext):
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
            await page.wait_for_timeout(3000)

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
            
            await page.wait_for_timeout(5000)
            
            screenshot_path = "result.png"
            await page.screenshot(path=screenshot_path)
            
            if "login" not in page.url.lower():
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                success_text = (
                    "✅ <b>LOGIN SUCCESSFUL</b>\n"
                    "Normal account — Upgrade for more features\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "🌍 <b>Site:</b> 777BIGWIN\n"
                    "👤 <b>User Information:</b>\n"
                    "├─ 🆔 <b>User ID:</b> 578634\n"
                    "├─ 📱 <b>Username:</b> {username}\n"
                    "├─ 🏷️ <b>Nickname:</b> <i>PyaeSonePhyo</i>\n"
                    "├─ 💰 <b>Balance:</b> <i>26.92 Ks</i>\n"
                    "├─ 📅 <b>Login Date:</b> <i>{current_time}</i>\n"
                    "└─ ✅ <b>Allow Withdraw:</b> Yes\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "💎 <b>Normal User</b> — Auto Bet is available.\n"
                    "Upgrade to Premium for Manual Bet, AI Prediction!\n\n"
                    "⚡ <b>Select your betting mode below:</b>"
                ).format(username=username, current_time=current_time)

                await message.answer(success_text, reply_markup=get_game_keyboard()) # ပြီးရင် Game Keyboard ပြမယ်
                await bot.send_photo(message.chat.id, FSInputFile(screenshot_path), caption="📸 Result")
                
                # Login ပြီးသွားလို့ State ကို Game ရွေးတဲ့အဆင့်ပြောင်းမယ်
                await state.set_state(LoginForm.select_game)
                
            else:
                await message.answer("❌ <b>Login မအောင်မြင်ပါ။</b> (စကားဝှက် မှားနေနိုင်သည်)", reply_markup=get_main_keyboard())
                await state.clear() # State ရှင်းလိုက်မယ်

            if os.path.exists(screenshot_path): os.remove(screenshot_path)

        except Exception as e:
            await message.answer(f"⚠️ Error: {html.escape(str(e))}", reply_markup=get_main_keyboard())
            await state.clear()
        finally:
            await browser.close()

# === နောက်ပိုင်းမှာ Game နှစ်ခု ထပ်ထည့်မယ့် Handler ===
@dp.message(LoginForm.select_game)
async def process_game_selection(message: types.Message, state: FSMContext):
    if message.text == "🔙 နောက်သို့":
        await state.clear()
        await message.answer("ပင်မစာမျက်နှာသို့ ပြန်သွားပါပြီ။", reply_markup=get_main_keyboard())
        return
        
    await message.answer(f"🎮 <b>သင်ရွေးချယ်ထားသော Game:</b> {message.text}\n\n(နောက်ပိုင်း ဒီနေရာမှာ Game Logic ထည့်သွင်းသွားမှာပါ)", reply_markup=get_main_keyboard())
    await state.clear()

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
