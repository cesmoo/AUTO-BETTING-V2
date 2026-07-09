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
    set_bet_size = State()

# ==========================================================
# ⚙️ Global Settings
# ==========================================================
is_bot_running = False
CUSTOM_PATTERN = ["BIG", "SMALL", "BIG", "BIG"]

# ==========================================================
# ⌨️ Keyboards
# ==========================================================
def get_main_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="🔐 Login")]],
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
            [KeyboardButton(text="📋 Info"), KeyboardButton(text="⚙️ Set Bet-Size")], 
            [KeyboardButton(text="💰 Balance"), KeyboardButton(text="🎰 Start Auto-Bet")],
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

@dp.message(Command("stop"))
async def cmd_stop(message: types.Message):
    global is_bot_running
    is_bot_running = False
    await message.answer("🛑 <b>Auto-Bet ကို ရပ်တန့်ရန် အမိန့်ပေးလိုက်ပါပြီ။</b> (လက်ရှိပွဲပြီးလျှင် ရပ်ပါမည်)")

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
# 🔧 Initial Login & Session Save
# ==========================================================
@dp.message(LoginForm.enter_password)
async def process_password(message: types.Message, state: FSMContext):
    password = message.text
    data = await state.get_data()
    username = data.get('phone')
    
    loading_msg = await message.answer("🔄 <b>အကောင့်ဝင်နေပါသည်... ခဏစောင့်ပါ...</b>")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = await browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True)
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
            
            if "login" not in page.url.lower():
                # 💾 အရေးကြီးဆုံးအပိုင်း: Login အောင်မြင်ပါက Session (Cookies) ကို သိမ်းဆည်းပါမည်
                session_file = f"session_{message.from_user.id}.json"
                await context.storage_state(path=session_file)

                # Info စာမျက်နှာသို့ ဆက်သွားခြင်း
                try:
                    await page.goto("https://www.777bigwingame.app/#/main", wait_until="networkidle")
                    await page.wait_for_timeout(3000)
                except: pass

                user_id, nickname, balance_text, site_login_time = "N/A", "Unknown", "0.00 Ks", datetime.now().strftime("%Y-%m-%d %H:%M:%S")

                try:
                    if await page.locator('.userInfo__container-content-nickname h3').first.is_visible(timeout=3000):
                        nickname = await page.locator('.userInfo__container-content-nickname h3').first.inner_text()
                    if await page.locator('.userInfo__container-content-uid span:nth-child(3)').first.is_visible():
                        user_id = await page.locator('.userInfo__container-content-uid span:nth-child(3)').first.inner_text()
                    if await page.locator('.balance_info p.totalSavings__container-header__subtitle span').first.is_visible():
                        balance_text = await page.locator('.balance_info p.totalSavings__container-header__subtitle span').first.inner_text()
                    if await page.locator('.userInfo__container-content-logintime span:nth-child(2)').first.is_visible():
                        site_login_time = await page.locator('.userInfo__container-content-logintime span:nth-child(2)').first.inner_text()
                except: pass

                await state.update_data(
                    is_logged_in=True, user_id=user_id.strip(), nickname=nickname.strip(),
                    balance=balance_text.strip(), login_time=site_login_time.strip(),
                    bet_sequence=[10, 30, 90, 270]
                )
                await message.answer("✅ <b>LOGIN SUCCESSFUL</b>", reply_markup=get_logged_in_keyboard())
                await state.set_state(LoginForm.main_menu)
            else:
                await page.screenshot(path="debug_login.png")
                await message.answer("❌ <b>Login မအောင်မြင်ပါ။</b> စကားဝှက် မှားယွင်းနေနိုင်ပါသည်။", reply_markup=get_main_keyboard())
                if os.path.exists("debug_login.png"):
                    await message.answer_photo(FSInputFile("debug_login.png"))
                await state.clear()
            
            await loading_msg.delete()
        except Exception as e:
            await message.answer(f"⚠️ <b>System Error:</b> {html.escape(str(e))}", reply_markup=get_main_keyboard())
            await state.clear()
            await loading_msg.delete()
        finally:
            await browser.close()

# ==========================================================
# 📋 ⚙️ Menu Controls (Info, Balance, Set Bet-Size, Logout)
# ==========================================================
@dp.message(LoginForm.main_menu, F.text == "📋 Info")
async def show_info(message: types.Message, state: FSMContext):
    data = await state.get_data()
    info_text = (
        "👤 <b>User Information:</b>\n"
        f"├─ 🆔 <b>User ID:</b> {data.get('user_id', 'N/A')}\n"
        f"├─ 📱 <b>Username:</b> {data.get('username', 'N/A')}\n"
        f"├─ 🏷️ <b>Nickname:</b> {data.get('nickname', 'Unknown')}\n"
        f"├─ 💰 <b>Balance:</b> {data.get('balance', '0.00 Ks')}\n"
        f"├─ 📅 <b>Login Date:</b> {data.get('login_time', '')}\n"
        f"└─ ✅ <b>Current Bets:</b> {data.get('bet_sequence')}"
    )
    await message.answer(info_text, reply_markup=get_logged_in_keyboard())

@dp.message(LoginForm.main_menu, F.text == "💰 Balance")
async def check_balance_cmd(message: types.Message, state: FSMContext):
    global is_bot_running
    if is_bot_running:
        data = await state.get_data()
        current_bal = data.get('balance', '0.00 Ks')
        return await message.answer(f"💰 <b>လက်ရှိ လက်ကျန်ငွေ (Saved):</b> {current_bal}\n\n⚠️ <i>Auto-bet အလုပ်လုပ်နေချိန်ဖြစ်သဖြင့် နောက်ဆုံးသိမ်းဆည်းထားသော ပမာဏကိုသာ ပြသပါသည်။</i>")

    session_file = f"session_{message.from_user.id}.json"
    if not os.path.exists(session_file):
        return await message.answer("❌ Session မရှိပါ။ ကျေးဇူးပြု၍ Login အရင်ဝင်ပါ။")

    msg = await message.answer("🔄 <b>Live Balance ကို တိုက်ရိုက် စစ်ဆေးနေပါသည်...</b>")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        # 🚀 Session ဖြင့် တိုက်ရိုက်ဝင်ရောက်ခြင်း
        context = await browser.new_context(storage_state=session_file, viewport={'width': 390, 'height': 844}, is_mobile=True)
        page = await context.new_page()
        try:
            await page.goto("https://www.777bigwingame.app/#/main", wait_until="networkidle")
            await page.wait_for_timeout(3000)
            
            bal_el = page.locator('.balance_info p.totalSavings__container-header__subtitle span').first
            if await bal_el.is_visible(timeout=3000):
                live_bal = await bal_el.inner_text()
                await state.update_data(balance=live_bal)
                await msg.edit_text(f"💰 <b>Live လက်ကျန်ငွေ:</b> {live_bal}")
            else:
                await msg.edit_text("⚠️ Balance ရှာမတွေ့ပါ။ Session သက်တမ်းကုန်သွားခြင်း ဖြစ်နိုင်ပါသည်။")
        except Exception as e:
            await msg.edit_text(f"⚠️ Error: {str(e)}")
        finally:
            await browser.close()

@dp.message(LoginForm.main_menu, F.text == "⚙️ Set Bet-Size")
async def ask_bet_size(message: types.Message, state: FSMContext):
    await state.set_state(LoginForm.set_bet_size)
    await message.answer(
        "🔢 <b>လောင်းကြေးပမာဏများကို '-' ခြား၍ ရိုက်ထည့်ပါ။</b>\n\n"
        "(ဥပမာ - <code>100-300-900-2700</code> သို့မဟုတ် <code>10-30-90-270</code>)", 
        reply_markup=ReplyKeyboardRemove()
    )

@dp.message(LoginForm.set_bet_size)
async def save_bet_size(message: types.Message, state: FSMContext):
    try:
        amounts = [int(x.strip()) for x in message.text.strip().split('-')]
        await state.update_data(bet_sequence=amounts)
        await state.set_state(LoginForm.main_menu)
        await message.answer(f"✅ <b>လောင်းကြေးပမာဏများ သတ်မှတ်ပြီးပါပြီ:</b>\n👉 {amounts}", reply_markup=get_logged_in_keyboard())
    except:
        await message.answer("❌ <b>ပုံစံမှားယွင်းနေပါသည်။</b> ဂဏန်းများကို '-' ခြား၍သာ ရိုက်ထည့်ပါ။")

@dp.message(LoginForm.main_menu, F.text == "🔐 Logout")
async def logout(message: types.Message, state: FSMContext):
    await state.clear()
    session_file = f"session_{message.from_user.id}.json"
    if os.path.exists(session_file):
        os.remove(session_file) # Session ကို ဖျက်ပစ်မည်
    await message.answer("👋 အကောင့်ထွက်ပြီးပါပြီ။", reply_markup=get_main_keyboard())

# ==========================================================
# 🎰 Auto-Bet Logic & Loop (DIRECT URL)
# ==========================================================
async def place_bet(page, bet_type, amount):
    try:
        if amount >= 1000 and amount % 1000 == 0: base_amt = 1000
        elif amount >= 100 and amount % 100 == 0: base_amt = 100
        else: base_amt = 10
            
        multiplier = amount // base_amt
        selector = "div.Betting__C-foot-b" if bet_type == "BIG" else "div.Betting__C-foot-s"
        
        await page.locator(selector).first.click()
        await page.wait_for_timeout(1000)
        await page.locator(f"div.Betting__Popup-body-line-item:has-text('{base_amt}')").first.click()
        await page.wait_for_timeout(500)

        js_code = f"""
        () => {{
            let inputField = document.querySelector('input#van-field-1-input');
            if(inputField) {{
                const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                nativeSetter.call(inputField, '{multiplier}');
                inputField.dispatchEvent(new Event('input', {{ bubbles: true }}));
                inputField.dispatchEvent(new Event('change', {{ bubbles: true }}));
            }}
        }}
        """
        await page.evaluate(js_code)
        await page.wait_for_timeout(500)
        await page.locator("div.Betting__Popup-foot-s").first.click()
        return True
    except Exception as e:
        print(f"Bet Error: {e}")
        return False

async def check_win_status(page):
    try:
        if await page.locator("div.WinningTip__C-body-l1:has-text('ဂုဏ်ယူပါတယ်')").is_visible(timeout=5000):
            await page.evaluate("document.body.click()") 
            return True
        return False
    except:
        return False

@dp.message(LoginForm.main_menu, F.text == "🎰 Start Auto-Bet")
async def start_autobet(message: types.Message, state: FSMContext):
    global is_bot_running
    if is_bot_running:
        return await message.answer("⚠️ Auto-Bet အလုပ်လုပ်နေဆဲပါ။ ရပ်ချင်ပါက /stop ကို ရိုက်ထည့်ပါ။")
    
    session_file = f"session_{message.from_user.id}.json"
    if not os.path.exists(session_file):
        return await message.answer("❌ Session မရှိပါ။ ကျေးဇူးပြု၍ Login အရင်ဝင်ပါ။")

    data = await state.get_data()
    bet_sequence = data.get('bet_sequence', [10, 30, 90, 270])
    
    is_bot_running = True
    status_msg = await message.answer("🚀 <b>Auto-Betting စတင်ရန် Browser ဖွင့်နေပါသည်...</b>")
    asyncio.create_task(run_betting_loop(message, status_msg, session_file, bet_sequence))

async def run_betting_loop(message, status_msg, session_file, bet_sequence):
    global is_bot_running
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        # 🚀 Session ဖြင့် တိုက်ရိုက်ဝင်ရောက်ခြင်း
        context = await browser.new_context(storage_state=session_file, viewport={'width': 390, 'height': 844}, is_mobile=True)
        page = await context.new_page()
        
        try:
            await status_msg.edit_text("🎮 <b>WinGo ဂိမ်းစာမျက်နှာသို့ တိုက်ရိုက် သွားနေပါသည်...</b>")
            await page.goto("https://www.777bigwingame.app/#/home/AllLotteryGames/WinGo?id=1", wait_until="networkidle")
            await page.wait_for_timeout(4000)
            
            # ဂိမ်းစာမျက်နှာ ဟုတ်မဟုတ် စစ်ဆေးခြင်း
            if "login" in page.url.lower():
                is_bot_running = False
                return await status_msg.edit_text("❌ Session သက်တမ်းကုန်သွားပါသည်။ ကျေးဇူးပြု၍ Login ပြန်ဝင်ပေးပါ။")

            await status_msg.edit_text(f"✅ <b>Auto-Bet စတင်ပါပြီ!</b>\n👉 အဆင့်များ: {bet_sequence}")
            
            current_step, current_pattern_index = 0, 0
            
            while is_bot_running:
                current_amount = bet_sequence[current_step]
                current_bet_type = CUSTOM_PATTERN[current_pattern_index % len(CUSTOM_PATTERN)]
                display_type = "အကြီး 🔴" if current_bet_type == "BIG" else "အသေး 🟢"
                
                if await place_bet(page, bet_type=current_bet_type, amount=current_amount):
                    await message.answer(f"🎲 {display_type} သို့ <b>{current_amount} ကျပ်</b> လောင်းထားပါသည်။ (အဆင့် {current_step+1})\n⏳ ရလဒ်ကို စောင့်နေပါသည်...")
                    await asyncio.sleep(50) 
                    
                    if await check_win_status(page):
                        await message.answer(f"🎉 <b>နိုင်ပါသည်!</b>\n🔄 အစမှ (<b>{bet_sequence[0]} ကျပ်</b>) ပြန်လောင်းပါမည်။")
                        current_step = 0
                    else:
                        current_step += 1
                        if current_step >= len(bet_sequence):
                            await message.answer(f"🚨 <b>[DANGER] အဆင့် ({len(bet_sequence)}) ဆင့်လုံး ရှုံးသွားပါပြီ။</b>\n🛑 အလိုအလျောက် ရပ်တန့်လိုက်ပါပြီ။")
                            is_bot_running = False
                            break
                        else:
                            await message.answer(f"❌ <b>ရှုံးပါသည်။</b>\nနောက်ပွဲကို <b>{bet_sequence[current_step]} ကျပ်</b> ဖြင့် ဆက်လောင်းပါမည်။")
                    current_pattern_index += 1
                else:
                    await message.answer("⚠️ Error: လောင်းကြေးတင်၍မရပါ။ နောက်တစ်ပွဲကို စောင့်ပါမည်...")
                
                await asyncio.sleep(5)
                
        except Exception as e:
            await message.answer(f"⚠️ Auto-Bet Error: {e}")
        finally:
            is_bot_running = False
            await browser.close()
            await message.answer("🏁 <b>စနစ်ရပ်နားသွားပါပြီ။</b>")

# ==========================================================
# 🚀 Main Bot Loop
# ==========================================================
async def main():
    print("🚀 Auto-Bet v2 (Session Save) စတင်နေပါပြီ...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
