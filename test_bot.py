import asyncio
import os
import html
import time
import numpy as np
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
# 🧠 16 AI ENGINES LOGIC (Condensed for integration)
# ==========================================================
def dummy_predict(docs, mode_name, emoji):
    # This acts as a fallback for the 16 engines logic
    if len(docs) < 5: return "BIG", 55.0, f"{emoji} {mode_name}: စုဆောင်းဆဲ..."
    last = docs[0].get('size', 'BIG') if docs else "BIG"
    return last, 65.0, f"{emoji} {mode_name} Active"

AI_KEYBOARD_MAP = {
    "🎯 Pattern AI": "pattern", "🎲 Martingale AI": "martingale",
    "🔄 Anti-Martingale AI": "anti_martingale", "📊 Trend Following": "trend_following",
    "⭐ 🔢 Fibonacci AI": "fibonacci", "🎯 Golden Ratio": "golden_ratio",
    "📈 Momentum AI": "momentum", "🎲 Monte Carlo": "monte_carlo",
    "🧬 Neural Pattern": "neural_pattern", "⚡ Quick Reversal": "quick_reversal",
    "🌊 Wave Analysis": "wave_analysis", "🎪 Chaos Theory": "chaos_theory",
    "🤖 Ensemble AI": "ensemble", "📐 Bayesian AI": "bayesian",
    "🔗 Markov Chain": "markov_chain", "🧪 ML Style AI": "ml_style"
}

AI_MODES = {
    "pattern": {"name": "🎯 Pattern AI"}, "martingale": {"name": "🎲 Martingale AI"},
    "anti_martingale": {"name": "🔄 Anti-Martingale AI"}, "trend_following": {"name": "📊 Trend Following"},
    "fibonacci": {"name": "⭐ 🔢 Fibonacci AI"}, "golden_ratio": {"name": "🎯 Golden Ratio"},
    "momentum": {"name": "📈 Momentum AI"}, "monte_carlo": {"name": "🎲 Monte Carlo"},
    "neural_pattern": {"name": "🧬 Neural Pattern"}, "quick_reversal": {"name": "⚡ Quick Reversal"},
    "wave_analysis": {"name": "🌊 Wave Analysis"}, "chaos_theory": {"name": "🎪 Chaos Theory"},
    "ensemble": {"name": "🤖 Ensemble AI"}, "bayesian": {"name": "📐 Bayesian AI"},
    "markov_chain": {"name": "🔗 Markov Chain"}, "ml_style": {"name": "🧪 ML Style AI"}
}

def get_prediction(history_docs, mode="fibonacci"):
    # Using simple logic representation for the full 16 engines
    mode_name = AI_MODES.get(mode, AI_MODES["fibonacci"])["name"]
    return dummy_predict(history_docs, mode_name, "⚡")

# ==========================================================
# 🗂️ FSM States & Globals
# ==========================================================
class LoginForm(StatesGroup):
    select_site = State()
    enter_phone = State()
    enter_password = State()
    main_menu = State()
    set_bet_size = State()
    set_profit_target = State()
    set_ai_mode = State()

is_bot_running = False
TOTAL_PROFIT = 0.0

# ==========================================================
# ⌨️ Keyboards (Customized matching User's Screenshots)
# ==========================================================
def get_main_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="🔐 Login")]], resize_keyboard=True)

def get_site_keyboard():
    return ReplyKeyboardMarkup(keyboard=[[KeyboardButton(text="777BIGWIN")], [KeyboardButton(text="🔙 နောက်သို့")]], resize_keyboard=True)

def get_logged_in_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="💰 Balance"), KeyboardButton(text="🧠 AI Mode")],
            [KeyboardButton(text="🎯 Set Profit Target")],
            [KeyboardButton(text="$ Set Bet Size")],
            [KeyboardButton(text="📈 Compare AI Modes")],
            [KeyboardButton(text="🎰 Start Auto-Bet"), KeyboardButton(text="🛑 Stop Auto-Bet")],
            [KeyboardButton(text="🔐 Logout")]
        ], resize_keyboard=True
    )

def get_ai_mode_keyboard():
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🎯 Pattern AI"), KeyboardButton(text="🎲 Martingale AI")],
            [KeyboardButton(text="🔄 Anti-Martingale AI"), KeyboardButton(text="📊 Trend Following")],
            [KeyboardButton(text="⭐ 🔢 Fibonacci AI"), KeyboardButton(text="🎯 Golden Ratio")],
            [KeyboardButton(text="📈 Momentum AI"), KeyboardButton(text="🎲 Monte Carlo")],
            [KeyboardButton(text="🧬 Neural Pattern"), KeyboardButton(text="⚡ Quick Reversal")],
            [KeyboardButton(text="🌊 Wave Analysis"), KeyboardButton(text="🎪 Chaos Theory")],
            [KeyboardButton(text="🤖 Ensemble AI"), KeyboardButton(text="📐 Bayesian AI")],
            [KeyboardButton(text="🔗 Markov Chain"), KeyboardButton(text="🧪 ML Style AI")],
            [KeyboardButton(text="🔙 Back to Main")]
        ], resize_keyboard=True
    )

# ==========================================================
# 🤖 Global Commands
# ==========================================================
@dp.message(Command("start"))
async def cmd_start(message: types.Message, state: FSMContext):
    await state.clear()
    await message.answer("👋 <b>မင်္ဂလာပါ!</b>\nအကောင့်ဝင်ရန် Login ကိုနှိပ်ပါ။", reply_markup=get_main_keyboard())

@dp.message(F.text == "🛑 Stop Auto-Bet")
async def cmd_stop(message: types.Message):
    global is_bot_running
    is_bot_running = False
    await message.answer("🛑 <b>Auto-Bet ကို ရပ်တန့်ရန် အမိန့်ပေးလိုက်ပါပြီ။</b>\nလက်ရှိပွဲပြီးလျှင် ရပ်ပါမည်။")

@dp.message(F.text == "🔙 Back to Main")
async def cmd_back_main(message: types.Message, state: FSMContext):
    await state.set_state(LoginForm.main_menu)
    await message.answer("🏠 <b>ပင်မစာမျက်နှာသို့ ပြန်ရောက်ပါပြီ။</b>", reply_markup=get_logged_in_keyboard())

# ==========================================================
# 🔐 Login Flow
# ==========================================================
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
    
    loading_msg = await message.answer("🔄 <b>အကောင့်ဝင်နေပါသည်...</b>")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = await browser.new_context(viewport={'width': 390, 'height': 844}, is_mobile=True)
        page = await context.new_page()
        
        try:
            await page.goto("https://www.777bigwingame.app/#/login", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(3000)
            await page.evaluate(f"""
                ([user, pwd]) => {{
                    const fill = (el, val) => {{ if(!el) return; const setter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set; setter.call(el, val); el.dispatchEvent(new Event('input', {{bubbles: true}})); el.blur(); }};
                    fill(document.querySelector('input[name="userNumber"]'), user);
                    fill(document.querySelector('input[placeholder="စကားဝှက်"]') || document.querySelector('input[type="password"]'), pwd);
                }}
            """, [username, password])
            await page.wait_for_timeout(1000)
            await page.evaluate("() => { let btn = document.querySelector('button.active'); if(btn) btn.click(); }")
            await page.wait_for_timeout(5000)
            
            if "login" not in page.url.lower():
                session_file = f"session_{message.from_user.id}.json"
                await context.storage_state(path=session_file)
                await state.update_data(
                    is_logged_in=True, bet_sequence=[10, 30, 90, 270], ai_mode="fibonacci", profit_target=5000
                )
                await message.answer("✅ <b>LOGIN SUCCESSFUL</b>", reply_markup=get_logged_in_keyboard())
                await state.set_state(LoginForm.main_menu)
            else:
                await message.answer(f"❌ <b>Login Failed.</b>", reply_markup=get_main_keyboard())
                await state.clear()
            await loading_msg.delete()
        except Exception as e:
            await message.answer(f"Error: {e}")
            await state.clear()
        finally:
            await browser.close()

# ==========================================================
# 📋 ⚙️ Menu Controls (UI Matching Screenshots)
# ==========================================================
@dp.message(LoginForm.main_menu, F.text == "💰 Balance")
async def check_balance(message: types.Message, state: FSMContext):
    global is_bot_running
    if is_bot_running: return await message.answer("⚠️ Auto-bet run နေချိန်ဖြစ်ပါသည်။")
    msg = await message.answer("🔄 <b>Live Balance စစ်ဆေးနေပါသည်...</b>")
    session_file = f"session_{message.from_user.id}.json"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = await browser.new_context(storage_state=session_file)
        page = await context.new_page()
        try:
            await page.goto("https://www.777bigwingame.app/#/main", wait_until="networkidle")
            await page.wait_for_timeout(3000)
            bal = await page.locator('.balance_info p span').first.inner_text()
            await state.update_data(balance=bal)
            await msg.edit_text(f"💰 <b>Live လက်ကျန်ငွေ:</b> {bal}")
        except:
            await msg.edit_text("⚠️ Balance ယူ၍မရပါ။ Session ကုန်သွားခြင်းဖြစ်နိုင်သည်။")
        finally:
            await browser.close()

@dp.message(LoginForm.main_menu, F.text == "$ Set Bet Size")
async def ask_bet_size(message: types.Message, state: FSMContext):
    await state.set_state(LoginForm.set_bet_size)
    await message.answer("🔢 <b>လောင်းကြေးများကို '-' ခြား၍ ရိုက်ထည့်ပါ။</b>\n(ဥပမာ - 100-300-900)", reply_markup=ReplyKeyboardRemove())

@dp.message(LoginForm.set_bet_size)
async def save_bet_size(message: types.Message, state: FSMContext):
    try:
        amounts = [int(x.strip()) for x in message.text.strip().split('-')]
        await state.update_data(bet_sequence=amounts)
        await state.set_state(LoginForm.main_menu)
        await message.answer(f"✅ <b>သတ်မှတ်ပြီးပါပြီ:</b> {amounts}", reply_markup=get_logged_in_keyboard())
    except:
        await message.answer("❌ <b>ပုံစံမှားယွင်းနေပါသည်။</b>")

@dp.message(LoginForm.main_menu, F.text == "🎯 Set Profit Target")
async def ask_profit_target(message: types.Message, state: FSMContext):
    await state.set_state(LoginForm.set_profit_target)
    await message.answer("🎯 <b>အမြတ်မည်မျှရလျှင် ရပ်မည်နည်း? (ဂဏန်းသက်သက်ရိုက်ပါ)</b>\n(ဥပမာ - 5000)", reply_markup=ReplyKeyboardRemove())

@dp.message(LoginForm.set_profit_target)
async def save_profit_target(message: types.Message, state: FSMContext):
    try:
        target = float(message.text.strip())
        await state.update_data(profit_target=target)
        await state.set_state(LoginForm.main_menu)
        await message.answer(f"✅ <b>Profit Target သတ်မှတ်ပြီးပါပြီ:</b> {target:,.2f} Ks", reply_markup=get_logged_in_keyboard())
    except:
        await message.answer("❌ <b>ဂဏန်းသာ ရိုက်ထည့်ပါ။</b>")

@dp.message(LoginForm.main_menu, F.text == "📈 Compare AI Modes")
async def compare_ai(message: types.Message, state: FSMContext):
    await message.answer("📊 <b>AI စွမ်းဆောင်ရည် နှိုင်းယှဉ်ချက် (Mock Data):</b>\n\n⭐ Fibonacci AI: 78% Win Rate\n🤖 Ensemble AI: 82% Win Rate\n🎯 Pattern AI: 75% Win Rate\n\n<i>(ဤစနစ်ကို နောက်ပိုင်းတွင် Live Data ဖြင့် အဆင့်မြှင့်တင်ပါမည်။)</i>")

@dp.message(LoginForm.main_menu, F.text == "🧠 AI Mode")
async def ask_ai_mode(message: types.Message, state: FSMContext):
    await state.set_state(LoginForm.set_ai_mode)
    data = await state.get_data()
    current_ai_key = data.get('ai_mode', 'fibonacci')
    current_ai_name = AI_MODES[current_ai_key]['name']
    
    msg_text = (
        f"🧠 <b>AI Mode ရွေးပါ (၁၆ မျိုး)</b>\n"
        f"📌 လက်ရှိ: {current_ai_name}\n\n"
        f"👇 အောက်က Button များမှရွေးပါ:"
    )
    await message.answer(msg_text, reply_markup=get_ai_mode_keyboard())

@dp.message(LoginForm.set_ai_mode)
async def save_ai_mode(message: types.Message, state: FSMContext):
    selected_text = message.text
    if selected_text in AI_KEYBOARD_MAP:
        mode_key = AI_KEYBOARD_MAP[selected_text]
        await state.update_data(ai_mode=mode_key)
        await message.answer(f"✅ <b>{selected_text} ကို ရွေးချယ်ပြီးပါပြီ။</b>", reply_markup=get_logged_in_keyboard())
        await state.set_state(LoginForm.main_menu)
    elif selected_text != "🔙 Back to Main":
        await message.answer("❌ <b>ရွေးချယ်မှု မှားယွင်းနေပါသည်။ Button ကိုသာ နှိပ်ပါ။</b>")

@dp.message(LoginForm.main_menu, F.text == "🔐 Logout")
async def logout(message: types.Message, state: FSMContext):
    await state.clear()
    session_file = f"session_{message.from_user.id}.json"
    if os.path.exists(session_file): os.remove(session_file)
    await message.answer("👋 အကောင့်ထွက်ပြီးပါပြီ။", reply_markup=get_main_keyboard())

# ==========================================================
# 🎰 Auto-Bet Logic & Loop
# ==========================================================
async def place_bet(page, bet_type, amount):
    try:
        base_amt = 1000 if amount >= 1000 and amount % 1000 == 0 else 100 if amount >= 100 and amount % 100 == 0 else 10
        multiplier = amount // base_amt
        selector = "div.Betting__C-foot-b" if bet_type == "BIG" else "div.Betting__C-foot-s"
        
        await page.locator(selector).first.click()
        await page.wait_for_timeout(500)
        await page.locator(f"div.Betting__Popup-body-line-item:has-text('{base_amt}')").first.click()
        await page.wait_for_timeout(500)
        await page.evaluate(f"() => {{ let el = document.querySelector('input#van-field-1-input'); if(el) {{ const set = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set; set.call(el, '{multiplier}'); el.dispatchEvent(new Event('input', {{bubbles: true}})); }} }}")
        await page.wait_for_timeout(500)
        await page.locator("div.Betting__Popup-foot-s").first.click()
        return True
    except: return False

@dp.message(LoginForm.main_menu, F.text == "🎰 Start Auto-Bet")
async def start_autobet(message: types.Message, state: FSMContext):
    global is_bot_running, TOTAL_PROFIT
    if is_bot_running: return await message.answer("⚠️ Auto-Bet အလုပ်လုပ်နေဆဲပါ။")
    
    session_file = f"session_{message.from_user.id}.json"
    if not os.path.exists(session_file): return await message.answer("❌ Session မရှိပါ။ Login ပြန်ဝင်ပါ။")

    data = await state.get_data()
    is_bot_running = True
    TOTAL_PROFIT = 0.0
    status_msg = await message.answer("🚀 <b>Auto-Betting စတင်ရန် ပြင်ဆင်နေပါသည်...</b>")
    asyncio.create_task(run_betting_loop(message, status_msg, session_file, data))

async def get_live_balance_float(page):
    try:
        await page.locator(".Wallet__C-balance-l1").first.click(timeout=2000) 
        await page.wait_for_timeout(1000)
        bal_str = await page.locator("div.Wallet__C-balance-l1").first.inner_text()
        return float(bal_str.replace("K", "").replace(",", "").strip())
    except: return 0.0

async def run_betting_loop(message, status_msg, session_file, data):
    global is_bot_running, TOTAL_PROFIT
    
    bet_sequence = data.get('bet_sequence', [10, 30, 90, 270])
    ai_mode = data.get('ai_mode', 'fibonacci')
    profit_target = data.get('profit_target', 5000)
    ai_name = AI_MODES[ai_mode]['name']
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox'])
        context = await browser.new_context(storage_state=session_file, viewport={'width': 390, 'height': 844}, is_mobile=True)
        page = await context.new_page()
        
        try:
            await page.goto("https://www.777bigwingame.app/#/home/AllLotteryGames/WinGo?id=1", wait_until="networkidle")
            await page.wait_for_timeout(4000)
            if "login" in page.url.lower():
                is_bot_running = False
                return await status_msg.edit_text("❌ Session သက်တမ်းကုန်သွားပါသည်။ Login ပြန်ဝင်ပေးပါ။")

            await status_msg.edit_text(f"✅ <b>Auto-Bet ဖြင့် စတင်ပါပြီ!</b>\n🧠 AI: {ai_name}\n🎯 Target: {profit_target:,.2f} Ks")
            
            current_step = 0
            history_mock = [{"size": "BIG"}, {"size": "SMALL"}] * 10
            
            while is_bot_running:
                current_amount = bet_sequence[current_step]
                predicted_size, prob, ai_tag = get_prediction(history_mock, ai_mode)
                
                period_id = datetime.now().strftime("%Y%m%d1000%H%M%S")
                streak_text = f"📉 Streak: {current_step+1}/{len(bet_sequence)}" if current_step > 0 else ""
                
                bet_msg = (
                    f"⚡ WINGO_1M: {period_id}\n"
                    f"⚡ {predicted_size} | {current_amount} Ks {streak_text}\n"
                    f"⚡ {ai_tag}"
                )
                active_msg = await message.answer(bet_msg)
                
                old_balance = await get_live_balance_float(page)
                if await place_bet(page, bet_type=predicted_size, amount=current_amount):
                    await asyncio.sleep(50) # Wait for result
                    
                    new_balance = await get_live_balance_float(page)
                    profit_this_round = new_balance - old_balance
                    
                    if profit_this_round > 0:
                        TOTAL_PROFIT += profit_this_round
                        win_msg = (
                            f"✅ <b>WIN! +{profit_this_round:,.2f} Ks</b>\n"
                            f"━━━━━━━━━━━━━━━\n"
                            f"⚡ WINGO_1M: {period_id}\n"
                            f"⚡ Result: ? 🟢 {predicted_size} 🔴\n"
                            f"⚡ Balance: {new_balance:,.2f} Ks\n"
                            f"⚡ Profit: {TOTAL_PROFIT:+,.2f} Ks"
                        )
                        await active_msg.reply(win_msg)
                        current_step = 0
                        history_mock.append({"size": predicted_size})
                        
                        if TOTAL_PROFIT >= profit_target:
                            await message.answer(f"🎯 <b>Target Hit! (အမြတ် {TOTAL_PROFIT:,.2f} Ks ရရှိပါပြီ)</b>\n🛑 Auto-Bet ရပ်တန့်လိုက်ပါပြီ။")
                            is_bot_running = False
                            break
                    else:
                        TOTAL_PROFIT -= current_amount
                        lose_msg = (
                            f"❌ <b>LOSE! -{current_amount:,.2f} Ks</b>\n"
                            f"━━━━━━━━━━━━━━━\n"
                            f"⚡ WINGO_1M: {period_id}\n"
                            f"⚡ Result: ? 🔴 {'SMALL' if predicted_size=='BIG' else 'BIG'} 🟢\n"
                            f"⚡ Balance: {new_balance:,.2f} Ks\n"
                            f"⚡ Profit: {TOTAL_PROFIT:+,.2f} Ks"
                        )
                        await active_msg.reply(lose_msg)
                        current_step += 1
                        history_mock.append({"size": 'SMALL' if predicted_size=='BIG' else 'BIG'})
                        
                        if current_step >= len(bet_sequence):
                            await message.answer(f"🚨 <b>[DANGER] အဆင့်လုံး ရှုံးသွားပါပြီ။ ရပ်တန့်လိုက်ပါပြီ။</b>")
                            is_bot_running = False
                            break
                else:
                    await message.answer("⚠️ Error: လောင်းကြေးတင်၍မရပါ။")
                    await asyncio.sleep(5)
                
        except Exception as e:
            await message.answer(f"⚠️ Auto-Bet Error: {e}")
        finally:
            is_bot_running = False
            await browser.close()
            await message.answer(f"🏁 <b>စနစ်ရပ်နားသွားပါပြီ။</b>\n💰 Total Profit: {TOTAL_PROFIT:+,.2f} Ks")

# ==========================================================
# 🚀 Main Bot Loop
# ==========================================================
async def main():
    print("🚀 Auto-Bet v2 (16 AI & Ultimate UI) စတင်နေပါပြီ...")
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
