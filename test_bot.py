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
            [KeyboardButton(text="📋 Info")], 
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
    
    loading_msg = await message.answer("🔄 <b>အကောင့်ဝင်နေပါသည်... ခဏစောင့်ပါ...</b>")
    
    async with async_playwright() as p:
        # Docker တွင် အဆင်ပြေစေရန် args များ ထည့်သွင်းထားပါသည်
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
                
                # Info စာမျက်နှာ (#/main) သို့ တိုက်ရိုက်သွားရန်
                try:
                    await page.goto("https://www.777bigwingame.app/#/main", wait_until="networkidle")
                    await page.wait_for_timeout(3000)
                except Exception as e:
                    print(f"Info Page သို့ သွားရာတွင် Error: {e}")

                # ၅။ DOM ထဲမှ Data များကို အတိအကျ ဆွဲထုတ်ခြင်း
                user_id = "N/A"
                nickname = "Unknown"
                balance_text = "0.00 Ks"
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
                        
                    time_el = page.locator('.userInfo__container-content-logintime span:nth-child(2)').first
                    if await time_el.is_visible(timeout=2000):
                        site_login_time = await time_el.inner_text()

                except Exception as e:
                    print(f"Scraping Error: {e}")

                # ၆။ State ထဲမှာ Data တွေကို သိမ်းဆည်းခြင်း
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
                await message.answer("❌ <b>Login မအောင်မြင်ပါ။ စကားဝှက် မှားယွင်းနေနိုင်ပါသည်။</b>", reply_markup=get_main_keyboard())
                await state.clear()

            await loading_msg.delete()

        except Exception as e:
            await message.answer(f"⚠️ <b>Error:</b> {html.escape(str(e))}", reply_markup=get_main_keyboard())
            await state.clear()
            await loading_msg.delete()
        finally:
            await browser.close()

# ==========================================================
# 📋 Info Button (State ထဲက Data ပြသရန်)
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
        user_id=user_id, 
        username=username, 
        nickname=nickname, 
        balance=balance, 
        login_time=login_time
    )
    
    await message.answer(info_text, reply_markup=get_logged_in_keyboard())

# ==========================================================
# 🔐 Logout
# ==========================================================
@dp.message(LoginForm.main_menu, F.text == "🔐 Logout")
async def logout(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("👋 အကောင့်ထွက်ပြီးပါပြီ။", reply_markup=get_main_keyboard())

# ==========================================================
# 🎰 Games
# ==========================================================
@dp.message(F.text == "🎰 Games")
async def games(message: types.Message):
    await message.answer("🎮 <b>Game ရွေးချယ်ရန်:</b>\n(ဤအပိုင်းကို နောက်ပိုင်းတွင် ထပ်မံဖြည့်စွက်နိုင်ပါသည်)", reply_markup=get_main_keyboard())

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
