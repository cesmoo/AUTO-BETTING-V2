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

# ==========================================
# 1. Config & Bot Setup
# ==========================================
load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
storage = MemoryStorage()
dp = Dispatcher(storage=storage)

# ==========================================
# 2. FSM States (အဆင့်အလိုက် လုပ်ဆောင်မှုများ)
# ==========================================
class LoginForm(StatesGroup):
    select_site = State()
    enter_phone = State()
    enter_password = State()
    select_game = State()

# ==========================================
# 3. Custom Keyboards (အောက်ခြေ ခလုတ်ခုံများ)
# ==========================================
def get_main_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🔐 Login")],
            [KeyboardButton(text="🎰 Games")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_site_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="777BIGWIN")],
            [KeyboardButton(text="🔙 နောက်သို့")]
        ],
        resize_keyboard=True
    )
    return keyboard

def get_game_keyboard():
    keyboard = ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🟢 Win Go")],
            [KeyboardButton(text="🔴 K3")],
            [KeyboardButton(text="🔙 နောက်သို့")]
        ],
        resize_keyboard=True
    )
    return keyboard

# ==========================================
# 4. Command Handlers
# ==========================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "👋 <b>မင်္ဂလာပါ!</b>\nအောက်ပါ button များမှ ရွေးချယ်ပါ။",
        reply_markup=get_main_keyboard()
    )

@dp.message(F.text == "🔐 Login")
async def login_start(message: types.Message, state: FSMContext):
    await state.set_state(LoginForm.select_site)
    await message.answer(
        "🌐 <b>Please select a site to login:</b>",
        reply_markup=get_site_keyboard()
    )

@dp.message(LoginForm.select_site)
async def process_site(message: types.Message, state: FSMContext):
    if message.text == "🔙 နောက်သို့":
        await state.clear()
        await message.answer("Cancelled.", reply_markup=get_main_keyboard())
        return
    
    await state.update_data(site=message.text)
    await state.set_state(LoginForm.enter_phone)
    await message.answer(
        "📞 <b>Please enter your phone:</b>",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(LoginForm.enter_phone)
async def process_phone(message: types.Message, state: FSMContext):
    await state.update_data(phone=message.text)
    await state.set_state(LoginForm.enter_password)
    await message.answer(
        "🔑 <b>Please enter your password:</b>",
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(LoginForm.enter_password)
async def process_password(message: types.Message, state: FSMContext):
    password = message.text
    data = await state.get_data()
    username = data.get('phone')
    loading_msg = await message.answer("🔄 <b>အကောင့်ဝင်နေပါသည်... ခဏစောင့်ပါ...</b>", reply_markup=get_main_keyboard())
    asyncio.create_task(run_playwright_login_func(message, username, password, state, loading_msg))

# ==========================================
# 5. Playwright Logic (🔥 Data Scraping ကို အာမခံချက်ရှိအောင် ပြင်ထားသည်)
# ==========================================
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
            
            # 🔥 Data တွေ Load ဖို့ ၁၀ စက္ကန့် စောင့်မယ်
            await page.wait_for_timeout(10000)
            
            screenshot_path = "result.png"
            await page.screenshot(path=screenshot_path)
            
            if "login" not in page.url.lower():
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # ==========================================
                # 🔥 DATA SCRAPING (ပုံထဲက ကွက်လပ်တွေကို ဖြည့်ဖို့ Robust နည်းလမ်းသုံးထားတယ်)
                # ==========================================
                try:
                    # 1. Nickname ရှာခြင်း (DOM Class နဲ့ မရရင် Page Text ကနေ Regex နဲ့ရှာမယ်)
                    nickname = "Unknown"
                    nickname_el = await page.query_selector('.userInfo__container-content-nickname h3, [class*="nickname"] h3')
                    if nickname_el:
                        nickname = await nickname_el.inner_text()
                    else:
                        content = await page.content()
                        # "Nickname:" နောက်က စာသားကို ဆွဲမယ်
                        nick_match = re.search(r'Nickname[:\s]*([^\n<]+)', content)
                        if nick_match:
                            nickname = nick_match.group(1).strip()
                    
                    # 2. User ID ရှာခြင်း (DOM ID နဲ့ မရရင် Page Text ကနေ Regex နဲ့ရှာမယ်)
                    user_id = "N/A"
                    uid_el = await page.query_selector('#customerId')
                    if uid_el:
                        user_id = await uid_el.inner_text()
                    else:
                        content = await page.content()
                        # "User ID:" နောက်က နံပါတ်ကို ဆွဲမယ်
                        uid_match = re.search(r'User ID[:\s]*(\d+)', content)
                        if uid_match:
                            user_id = uid_match.group(1)
                    
                    # 3. Balance ရှာခြင်း
                    balance_text = "0.00 Ks"
                    balance_el = await page.query_selector('[class*="balance"], .userInfo__container-content [class*="money"]')
                    if balance_el:
                        balance_text = await balance_el.inner_text()
                    else:
                        content = await page.content()
                        bal_match = re.search(r'(\d+\.?\d*)\s*Ks', content)
                        if bal_match:
                            balance_text = f"{bal_match.group(1)} Ks"
                            
                except Exception:
                    nickname, user_id, balance_text = "Unknown", "N/A", "0.00 Ks"
                
                # Data တွေကို သန့်ရှင်းခြင်း
                nickname = nickname.strip()
                user_id = user_id.strip()

                # ==========================================
                # 🎨 Result Card Formatting (ပုံထဲကအတိုင်း Emoji နဲ့ Format ချမယ်)
                # ==========================================
                success_text = (
                    "✅ <b>LOGIN SUCCESSFUL</b>\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "🌍 <b>Site:</b> 777BIGWIN\n"
                    "👤 <b>User Information:</b>\n"
                    "├─ 🆔 <b>User ID:</b> {user_id}\n"
                    "├─ 📱 <b>Username:</b> {username}\n"
                    "├─ 🏷️ <b>Nickname:</b> <i>{nickname}</i>\n"
                    "├─ 💰 <b>Balance:</b> <i>{balance}</i>\n"
                    "├─ 📅 <b>Login Date:</b> <i>{current_time}</i>\n"
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
                    current_time=current_time
                )

                # Success Message ပို့ခြင်း
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

# ==========================================
# 6. Game Selection Handler
# ==========================================
@dp.message(LoginForm.select_game)
async def process_game_selection(message: types.Message, state: FSMContext):
    if message.text == "🔙 နောက်သို့":
        await state.clear()
        await message.answer("ပင်မစာမျက်နှာသို့ ပြန်သွားပါပြီ။", reply_markup=get_main_keyboard())
        return
        
    await message.answer(f"🎮 <b>သင်ရွေးချယ်ထားသော Game:</b> {message.text}\n\n(နောက်ပိုင်း ဒီနေရာမှာ Game Logic ထည့်သွင်းသွားမှာပါ)", reply_markup=get_main_keyboard())
    await state.clear()

# ==========================================
# 7. Main Execution
# ==========================================
async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
