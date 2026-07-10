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

# User များ၏ Browser Session များကို ခေတ္တသိမ်းဆည်းထားရန် (Auto Bet အတွက်)
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
    
    # Playwright ကို စတင်ခြင်း
    p = await async_playwright().start()
    browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36", 
        viewport={'width': 390, 'height': 844}, 
        is_mobile=True
    )
    page = await context.new_page()
    
    try:
        # ၁။ Login စာမျက်နှာသို့ သွားခြင်း
        await page.goto("https://www.777bigwingame.app/#/login", wait_until="networkidle", timeout=60000)
        await page.wait_for_timeout(3000)

        # ၂။ Vue.js Reactivity ကို ကျော်ဖြတ်၍ အချက်အလက်များ ထည့်သွင်းခြင်း
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

        # ၃။ Login ခလုတ်ကို နှိပ်ခြင်း
        await page.evaluate("""
            () => {
                let btn = document.querySelector('button.active');
                if (btn) btn.click();
            }
        """)
        
        await page.wait_for_timeout(5000)
        
        # Popup ပိတ်ခြင်း (လိုအပ်ပါက)
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
        
        # ၄။ Login အောင်မြင်မှု စစ်ဆေးခြင်း
        if "login" not in page.url.lower():
            
            # Info စာမျက်နှာ (#/main) သို့ သွား၍ Data ဆွဲထုတ်ခြင်း
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

            # ၅။ Win Go 30s စာမျက်နှာသို့ သွားထားခြင်း (Auto Bet အတွက် အဆင်သင့်ဖြစ်စေရန်)
            await page.goto("https://www.777bigwingame.app/#/home/AllLotteryGames/WinGo?id=1", wait_until="networkidle")
            await page.wait_for_timeout(2000)

            # ၆။ State ထဲမှာ Data တွေကို သိမ်းဆည်းခြင်း
            await state.update_data(
                is_logged_in=True, username=username, user_id=user_id.strip(),
                nickname=nickname.strip(), balance=balance_text.strip(), login_time=site_login_time.strip()
            )

            # Session သိမ်းဆည်းခြင်း (Bot မပိတ်မချင်း Browser ပွင့်နေမည်)
            active_sessions[user_tg_id] = {
                "playwright": p,
                "browser": browser,
                "page": page
            }

            await message.answer(
                "✅ <b>LOGIN SUCCESSFUL</b>\n\n"
                "သင့်အကောင့်အချက်အလက်များကို ကြည့်ရှုရန် အောက်ပါ <b>📋 Info</b> ခလုတ်ကို နှိပ်ပါ။\n"
                "လောင်းကြေးထည့်ရန် <code>/bet [big/small/red/green/violet] [amount]</code> ကို အသုံးပြုပါ။",
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
# 🚀 Auto Bet Function (with Debugging)
# ==========================================================
async def place_auto_bet(page, message: types.Message, bet_type: str, amount: int = 10):
    try:
        await message.answer(f"🔄 Auto Bet စတင်နေပါသည်... ရွေးချယ်မှု: {bet_type.capitalize()}, ပမာဏ: {amount}")

        bet_choice = bet_type.lower()
        
        # ၁။ အရောင် သို့မဟုတ် အကြီး/အသေး ရွေးချယ်ခြင်း
        if bet_choice == "big":
            await page.locator('.Betting__C-foot-b').click(timeout=5000) 
        elif bet_choice == "small":
            await page.locator('.Betting__C-foot-s').click(timeout=5000)
        elif bet_choice == "red":
            await page.locator('.Betting__C-head-r').click(timeout=5000)
        elif bet_choice == "green":
            await page.locator('.Betting__C-head-g').click(timeout=5000)
        elif bet_choice in ["violet", "purple"]:
            await page.locator('.Betting__C-head-p').click(timeout=5000)
        else:
            await message.answer("❌ မှားယွင်းနေပါသည်။ 'big', 'small', 'red', 'green', 'violet' ထဲမှ တစ်ခုရွေးပါ။")
            return False

        await page.wait_for_timeout(1000)

        # ၂။ လောင်းကြေးပမာဏ ရွေးချယ်ခြင်း (10, 100, 1000, 10000)
        amount_locator = page.locator(f"div.Betting__Popup-body-line-item", has_text=str(amount)).first
        await amount_locator.click(timeout=3000)
        await page.wait_for_timeout(500)

        # ၃။ အတည်ပြု (Confirm) ခလုတ်ကို နှိပ်ခြင်း
        confirm_btn = page.locator('.Betting__Popup-foot > div').last
        await confirm_btn.click(timeout=3000)

        await page.wait_for_timeout(2000)
        await message.answer("✅ <b>လောင်းကြေး အောင်မြင်စွာ ထည့်သွင်းပြီးပါပြီ။</b>")
        return True

    except Exception as e:
        # 🐛 DEBUGGING: Error တက်ပါက Screenshot ရိုက်ခြင်း
        error_image_path = f"debug_error_{message.from_user.id}.png"
        try:
            await page.screenshot(path=error_image_path, full_page=True)
            photo = FSInputFile(error_image_path)
            error_text = str(e).split('\n')[0][:200] 
            caption_text = (
                "❌ <b>Auto Bet လုပ်ဆောင်မှု ရပ်တန့်သွားပါသည်!</b>\n\n"
                f"<code>{error_text}</code>"
            )
            await message.answer_photo(photo=photo, caption=caption_text)
            if os.path.exists(error_image_path):
                os.remove(error_image_path)
        except Exception as screenshot_err:
            await message.answer(f"❌ Error ဖြစ်သွားသော်လည်း Screenshot ရိုက်ယူ၍ မရပါ။\n{screenshot_err}")

        return False

# ==========================================================
# 🕹️ Bet Command Handler
# ==========================================================
@dp.message(Command("bet"))
async def cmd_bet(message: types.Message, state: FSMContext):
    user_tg_id = message.from_user.id
    
    # Session ရှိ/မရှိ စစ်ဆေးခြင်း
    if user_tg_id not in active_sessions:
        return await message.answer("⚠️ အရင်ဆုံး Login ဝင်ပေးပါ။")
        
    args = message.text.split()
    if len(args) < 2:
        return await message.answer("⚠️ <b>အသုံးပြုနည်း:</b> /bet [big/small/red/green/violet] [amount]\nဥပမာ: <code>/bet big 100</code>")

    bet_type = args[1]
    amount = 10
    if len(args) >= 3 and args[2].isdigit():
        amount = int(args[2])
        
    # Active Session မှ Page ကို ယူ၍ Auto Bet ထိုးခြင်း
    page = active_sessions[user_tg_id]["page"]
    await place_auto_bet(page, message, bet_type, amount)

# ==========================================================
# 💰 Check Balance (WinGo Page မှ တိုက်ရိုက်ဆွဲထုတ်ခြင်း)
# ==========================================================
@dp.message(LoginForm.main_menu, F.text == "💰 Balance")
async def check_balance(message: types.Message, state: FSMContext):
    user_tg_id = message.from_user.id
    
    # Session ရှိ/မရှိ စစ်ဆေးခြင်း
    if user_tg_id not in active_sessions:
        return await message.answer("⚠️ အရင်ဆုံး Login ဝင်ပေးပါ။")

    loading_msg = await message.answer("🔄 <b>လက်ကျန်ငွေ (Balance) ကို စစ်ဆေးနေပါသည်...</b>")
    page = active_sessions[user_tg_id]["page"]

    try:
        balance_text = "0.00 Ks"
        
        # HTML Structure အရ '.Wallet__C-balance-l1' အောက်က 'div' ကို ဖတ်ပါမည်
        balance_el = page.locator('.Wallet__C-balance-l1 div').first
        
        if await balance_el.is_visible(timeout=3000):
            balance_text = await balance_el.inner_text()

        # နောက်ပိုင်း Info ခလုတ်နှိပ်လျှင်ပါ Balance အသစ်ပေါ်စေရန် State ကို Update လုပ်ပါမည်
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
        "├─ 🆔 <b>User ID:</b> {user_id}\n"
        "├─ 📱 <b>Username:</b> {username}\n"
        "├─ 🏷️ <b>Nickname:</b> {nickname}\n"
        "├─ 💰 <b>Balance:</b> {balance}\n"
        "├─ 📅 <b>Login Date:</b> {login_time}\n"
        "└─ ✅ <b>Allow Withdraw:</b> Yes\n"
    ).format(
        user_id=user_id, username=username, nickname=nickname, 
        balance=balance, login_time=login_time
    )
    
    await message.answer(info_text, reply_markup=get_logged_in_keyboard())

# ==========================================================
# 🔐 Logout
# ==========================================================
@dp.message(LoginForm.main_menu, F.text == "🔐 Logout")
async def logout(message: types.Message, state: FSMContext):
    user_tg_id = message.from_user.id
    
    # Logout လုပ်ချိန်တွင် Browser Session ကို ပိတ်ခြင်း
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
    await message.answer("🎮 <b>Game ရွေးချယ်ရန်:</b>\nWin Go 30s ကို ရွေးချယ်ထားပါသည်။ Auto Bet အတွက် <code>/bet</code> command ကို သုံးပါ။", reply_markup=get_main_keyboard())

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
