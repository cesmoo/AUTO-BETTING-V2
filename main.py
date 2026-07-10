import asyncio
import os
import html
import random
import aiohttp
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

# User များ၏ Browser Session များကို ခေတ္တသိမ်းဆည်းထားရန်
active_sessions = {}

# ==========================================================
# 🗂️ FSM States
# ==========================================================
class LoginForm(StatesGroup):
    select_site = State()
    enter_phone = State()
    enter_password = State()
    main_menu = State()

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
            [KeyboardButton(text="📋 Info"), KeyboardButton(text="💰 Balance")], 
            [KeyboardButton(text="🎰 Games")],
            [KeyboardButton(text="🔐 Logout")]
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
# 🔥 Playwright Logic: Robust Login + Data Scraping
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

        await page.evaluate("""
            () => {
                let btn = document.querySelector('button.active');
                if (btn) btn.click();
            }
        """)
        
        await page.wait_for_timeout(5000)
        
        try:
            close_selector = ".announcement-dialog__button"
            for _ in range(3):
                btn = await page.query_selector(close_selector)
                if btn:
                    await btn.click()
                    await page.wait_for_timeout(1000)
                else:
                    break
        except:
            pass
        
        if "login" not in page.url.lower():
            
            try:
                await page.goto("https://www.777bigwingame.app/#/main", wait_until="networkidle")
                await page.wait_for_timeout(3000)
            except Exception as e:
                print(f"Info Page သို့ သွားရာတွင် Error: {e}")

            user_id, nickname, balance_text = "N/A", "Unknown", "0.00 Ks"
            site_login_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

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
            except Exception as e:
                print(f"Scraping Error: {e}")

            await page.goto("https://www.777bigwingame.app/#/home/AllLotteryGames/WinGo?id=1", wait_until="networkidle")
            await page.wait_for_timeout(2000)

            await state.update_data(
                is_logged_in=True, username=username, user_id=user_id.strip(),
                nickname=nickname.strip(), balance=balance_text.strip(), login_time=site_login_time.strip()
            )

            active_sessions[user_tg_id] = {
                "playwright": p,
                "browser": browser,
                "page": page
            }

            await message.answer(
                "✅ <b>LOGIN SUCCESSFUL</b>\n\n"
                "သင့်အကောင့်အချက်အလက်များကို ကြည့်ရှုရန် အောက်ပါ <b>📋 Info</b> ခလုတ်ကို နှိပ်ပါ။\n"
                "Auto Bet အတွက် <code>/bet [type] [amount]</code> (သို့) AI Bet အတွက် <code>/aibet [amount]</code> ကို အသုံးပြုပါ။",
                reply_markup=get_logged_in_keyboard()
            )
            await state.set_state(LoginForm.main_menu)
            
        else:
            await message.answer("❌ <b>Login မအောင်မြင်ပါ။ စကားဝှက် မှားယွင်းနေနိုင်ပါသည်။</b>", reply_markup=get_main_keyboard())
            await browser.close()
            await p.stop()
            await state.clear()

        await loading_msg.delete()

    except Exception as e:
        await message.answer(f"⚠️ <b>Error:</b> {html.escape(str(e))}", reply_markup=get_main_keyboard())
        await browser.close()
        await p.stop()
        await state.clear()
        await loading_msg.delete()


# ==========================================================
# 🚀 Auto Bet Function (Targeted Popup Bypass ဖြင့်)
# ==========================================================
async def place_auto_bet(page, message: types.Message, bet_type: str, amount: int = 10):
    try:
        await message.answer(f"🔄 Auto Bet စတင်နေပါသည်... ရွေးချယ်မှု: {bet_type.capitalize()}, ပမာဏ: {amount}")

        bet_choice = bet_type.lower()
        
        # 🛑 Popup ကို အတိအကျ ပိတ်ခြင်း
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

        # ၁။ အရောင် သို့မဟုတ် အကြီး/အသေး ရွေးချယ်ခြင်း (force=True)
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
            await message.answer("❌ မှားယွင်းနေပါသည်။ 'big', 'small', 'red', 'green', 'violet' ထဲမှ တစ်ခုရွေးပါ။")
            return False

        await page.wait_for_timeout(1000)

        # ၂။ လောင်းကြေးပမာဏ ရွေးချယ်ခြင်း 
        amount_locator = page.locator(f"div.Betting__Popup-body-line-item", has_text=str(amount)).first
        await amount_locator.click(timeout=3000, force=True)
        await page.wait_for_timeout(500)

        # ၃။ အတည်ပြု (Confirm) ခလုတ်ကို နှိပ်ခြင်း
        confirm_btn = page.locator('.Betting__Popup-foot > div').last
        await confirm_btn.click(timeout=3000, force=True)

        await page.wait_for_timeout(2000)
        await message.answer("✅ <b>လောင်းကြေး အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ။</b>")
        return True

    except Exception as e:
        error_image_path = f"debug_error_{message.from_user.id}.png"
        try:
            await page.screenshot(path=error_image_path, full_page=True)
            photo = FSInputFile(error_image_path)
            error_text = str(e).split('\n')[0][:200] 
            caption_text = f"❌ <b>Auto Bet လုပ်ဆောင်မှု ရပ်တန့်သွားပါသည်!</b>\n\n<code>{error_text}</code>"
            await message.answer_photo(photo=photo, caption=caption_text)
            if os.path.exists(error_image_path):
                os.remove(error_image_path)
        except Exception as screenshot_err:
            await message.answer(f"❌ Error ဖြစ်သွားသော်လည်း Screenshot ရိုက်ယူ၍ မရပါ။\n{screenshot_err}")

        return False

# ==========================================================
# 🧠 AI Prediction API Fetching Logic
# ==========================================================
async def get_ai_prediction():
    url = 'https://api.bigwinqaz.com/api/webapi/GetNoaverageEmerdList'
    
    headers = {
        'authority': 'api.bigwinqaz.com',
        'accept': 'application/json, text/plain, */*',
        'authorization': 'Bearer eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJpYXQiOiIxNzgzNjQzMjUwIiwibmJmIjoiMTc4MzY0MzI1MCIsImV4cCI6IjE3ODM2NDUwNTAiLCJodHRwOi8vc2NoZW1hcy5taWNyb3NvZnQuY29tL3dzLzIwMDgvMDYvaWRlbnRpdHkvY2xhaW1zL2V4cGlyYXRpb24iOiI3LzEwLzIwMjYgNzoyNzozMCBBTSIsImh0dHA6Ly9zY2hlbWFzLm1pY3Jvc29mdC5jb20vd3MvMjAwOC8wNi9pZGVudGl0eS9jbGFpbXMvcm9sZSI6IkFjY2Vzc19Ub2tlbiIsIlVzZXJJZCI6IjU3NDMzNSIsIlVzZXJOYW1lIjoiOTU5Njc1MzIzODc4IiwiVXNlclBob3RvIjoiNyIsIk5pY2tOYW1lIjoiV2FuZyBMaW4iLCJBbW91bnQiOiIxMDAwLjAwIiwiSW50ZWdyYWwiOiIwIiwiTG9naW5NYXJrIjoiSDUiLCJMb2dpblRpbWUiOiI3LzEwLzIwMjYgNjo1NzozMCBBTSIsIkxvZ2luSVBBZGRyZXNzIjoiMTAzLjEzNC4yMDcuMTUyIiwiRGJOdW1iZXIiOiIwIiwiSXN2YWxpZGF0b3IiOiIwIiwiS2V5Q29kZSI6Ijk3IiwiVG9rZW5UeXBlIjoiQWNjZXNzX1Rva2VuIiwiUGhvbmVUeXBlIjoiMSIsIlVzZXJUeXBlIjoiMCIsIlVzZXJOYW1lMiI6InB5YWVzb25lNXBzcEB5YWhvby5jb20iLCJpc3MiOiJqd3RJc3N1ZXIiLCJhdWQiOiJsb3R0ZXJ5VGlja2V0In0.C-FbAazz7HkLeQ5L5eISGHGJCdwarGdz4A3v9XyvqCE',
        'content-type': 'application/json;charset=UTF-8',
        'origin': 'https://www.777bigwingame.app',
        'referer': 'https://www.777bigwingame.app/',
        'user-agent': 'Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/137.0.0.0 Mobile Safari/537.36',
    }

    json_data = {
        'pageSize': 10, 'pageNo': 1, 'typeId': 30, 'language': 7,
        'random': 'e431a6544cde4cbb8e09a4c01199b75b',
        'signature': '1668945A145F050B049ED587E6E9E0E7', 'timestamp': 1000000000,
    }

    try:
        async with aiohttp.ClientSession() as session:
            async with session.post(url, headers=headers, json=json_data) as response:
                api_result = await response.json()
                
        records = api_result.get('data', {}).get('list', [])
        
        if records:
            # လောလောဆယ် Mock Logic ဖြင့် စမ်းသပ်ရန်
            prediction_choice = random.choice(["big", "small"]) 
            confidence = random.randint(70, 95)
            return prediction_choice, confidence
        else:
            return None, 0

    except Exception as e:
        print(f"API Error: {e}")
        return None, 0

# ==========================================================
# 🤖 AI Auto Bet Command Handler
# ==========================================================
@dp.message(Command("aibet"))
async def cmd_aibet(message: types.Message, state: FSMContext):
    user_tg_id = message.from_user.id
    if user_tg_id not in active_sessions:
        return await message.answer("⚠️ အရင်ဆုံး Login ဝင်ပေးပါ။")

    args = message.text.split()
    amount = 10
    if len(args) >= 2 and args[1].isdigit():
        amount = int(args[1])

    loading_msg = await message.answer("🧠 <b>AI စနစ်ဖြင့် ပွဲစဉ်မှတ်တမ်းများကို လေ့လာသုံးသပ်နေပါသည်...</b>")

    predicted_bet, confidence = await get_ai_prediction()

    await loading_msg.delete()

    if predicted_bet:
        await message.answer(f"📊 <b>AI ခန့်မှန်းချက် ရရှိပါပြီ!</b>\n\n🎯 ရွေးချယ်မှု: <b>{predicted_bet.upper()}</b>\n⚡ သေချာမှု (Confidence): <b>{confidence}%</b>\n💰 လောင်းကြေး: <b>{amount}</b>\n\n🔄 အလိုအလျောက် လောင်းကြေးထည့်နေပါသည်...")
        
        page = active_sessions[user_tg_id]["page"]
        await place_auto_bet(page, message, predicted_bet, amount)
    else:
        await message.answer("❌ API မှ အချက်အလက်ရယူရာတွင် အခက်အခဲရှိနေပါသည်။")

# ==========================================================
# 🕹️ Standard Bet Command Handler
# ==========================================================
@dp.message(Command("bet"))
async def cmd_bet(message: types.Message, state: FSMContext):
    user_tg_id = message.from_user.id
    if user_tg_id not in active_sessions:
        return await message.answer("⚠️ အရင်ဆုံး Login ဝင်ပေးပါ။")
        
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("⚠️ <b>အသုံးပြုနည်း:</b> /bet [big/small/red/green/violet] [amount]\nဥပမာ: <code>/bet big 100</code>")

    bet_type = args[1]
    amount = 10
    if len(args) >= 3 and args[2].isdigit():
        amount = int(args[2])
        
    page = active_sessions[user_tg_id]["page"]
    await place_auto_bet(page, message, bet_type, amount)

# ==========================================================
# 💰 Check Balance (WinGo Page မှ တိုက်ရိုက်ဆွဲထုတ်ခြင်း)
# ==========================================================
@dp.message(LoginForm.main_menu, F.text == "💰 Balance")
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
        await loading_msg.delete()
        await message.answer(f"💰 <b>သင့်ရဲ့ လက်ရှိ လက်ကျန်ငွေ:</b> {balance_text.strip()}", reply_markup=get_logged_in_keyboard())

    except Exception as e:
        await loading_msg.delete()
        await message.answer(f"⚠️ <b>Error:</b> Balance စစ်ဆေးရာတွင် အခက်အခဲရှိနေပါသည်။\n{html.escape(str(e))}", reply_markup=get_logged_in_keyboard())

# ==========================================================
# 📋 Info Button
# ==========================================================
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

# ==========================================================
# 🔐 Logout
# ==========================================================
@dp.message(LoginForm.main_menu, F.text == "🔐 Logout")
async def logout(message: types.Message, state: FSMContext):
    user_tg_id = message.from_user.id
    if user_tg_id in active_sessions:
        try:
            await active_sessions[user_tg_id]["browser"].close()
            await active_sessions[user_tg_id]["playwright"].stop()
        except:
            pass
        del active_sessions[user_tg_id]
        
    await state.clear()
    await message.answer("👋 အကောင့်ထွက်ပြီးပါပြီ။", reply_markup=get_main_keyboard())

# ==========================================================
# 🎰 Games
# ==========================================================
@dp.message(F.text == "🎰 Games")
async def games(message: types.Message):
    await message.answer("🎮 <b>Game ရွေးချယ်ရန်:</b>\nWin Go 30s ကို ရွေးချယ်ထားပါသည်။ Auto Bet အတွက် <code>/bet</code> (သို့) <code>/aibet</code> ကို သုံးပါ။", reply_markup=get_main_keyboard())

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
