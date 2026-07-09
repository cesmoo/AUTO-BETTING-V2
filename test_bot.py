import asyncio
import os
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import FSInputFile
from playwright.async_api import async_playwright

load_dotenv()

# ==========================================
# ⚙️ 1. CONFIGURATION
# ==========================================
# .env ဖိုင်ထဲတွင် BOT_TOKEN ကို ထည့်ထားပေးရန် လိုအပ်ပါသည်
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ==========================================
# 🎮 2. TELEGRAM COMMAND HANDLER
# ==========================================
@dp.message(Command("testlogin"))
async def start_login_test(message: types.Message):
    # Command ပုံစံ: /testlogin 09680090540 Mitheint11
    parts = message.text.strip().split()
    
    if len(parts) != 3:
        return await message.reply(
            "⚠️ ပုံစံမှားယွင်းနေပါသည်။ ကျေးဇူးပြု၍ အောက်ပါအတိုင်း ရိုက်ထည့်ပါ။\n\n"
            "<code>/testlogin ဖုန်းနံပါတ် Password</code>\n\n"
            "ဥပမာ - <code>/testlogin 09680090540 Mitheint11</code>"
        )
        
    username = parts[1]
    password = parts[2]
    
    # နောက်ကွယ်မှ Playwright ကို စတင် Run မည်
    asyncio.create_task(run_playwright_login(message, username, password))

# ==========================================
# 🤖 3. PLAYWRIGHT LOGIN LOGIC
# ==========================================
async def run_playwright_login(message: types.Message, username, password):
    status_msg = await message.reply("🔄 <b>Browser ဖွင့်၍ Login စမ်းသပ်နေပါသည်...</b>")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
            viewport={'width': 390, 'height': 844}, 
            is_mobile=True, 
            has_touch=True  
        )
        page = await context.new_page()
        
        try:
            await status_msg.edit_text("🌐 <b>ဝဘ်ဆိုဒ်သို့ သွားနေပါသည်...</b>")
            await page.goto("https://www.777bigwingame.app/#/login", wait_until="networkidle")
            await page.wait_for_timeout(3000)

            await status_msg.edit_text("📱 <b>ဖုန်းနံပါတ် ရိုက်ထည့်နေပါသည်...</b>")
            phone_input = page.locator('input[name="userNumber"]')
            await phone_input.click()
            await phone_input.clear()
            await phone_input.press_sequentially(username, delay=150)
            await page.wait_for_timeout(500)

            await status_msg.edit_text("🔑 <b>Password ရိုက်ထည့်နေပါသည်...</b>")
            # Screenshot အသစ်အရ placeholder="Password" ကို ပြောင်းလဲအသုံးပြုထားသည်
            pwd_input = page.locator('input[placeholder="Password"]')
            await pwd_input.click()
            await pwd_input.clear()
            await pwd_input.press_sequentially(password, delay=150)
            await page.wait_for_timeout(500)

            await status_msg.edit_text("🖱️ <b>Login ခလုတ်ကို နှိပ်နေပါသည်...</b>")
            # Screenshot အသစ်အရ button class="active" ကို အသုံးပြုထားသည်
            login_btn = page.locator('.signIn__container-button button.active')
            await login_btn.tap(force=True) 
            
            await status_msg.edit_text("⏳ <b>ဝင်သွားရန် ၅ စက္ကန့် စောင့်နေပါသည်...</b>")
            await page.wait_for_timeout(5000)

            # နောက်ဆုံးအခြေအနေကို Screenshot ရိုက်မည်
            await page.screenshot(path="test_result.png")
            
            if "login" not in page.url.lower():
                await message.reply(f"✅ <b>ဝင်သွားပါပြီ! Login အောင်မြင်ပါသည်။</b>\nလက်ရှိ URL: {page.url}")
            else:
                await message.reply("❌ <b>Login မအောင်မြင်သေးပါ။ Screenshot ကို စစ်ဆေးကြည့်ပါ။</b>")
                
            # Screenshot ကို Telegram သို့ ပို့မည်
            photo = FSInputFile("test_result.png")
            await bot.send_photo(message.chat.id, photo, caption="📸 နောက်ဆုံး ရောက်ရှိနေသော မျက်နှာပြင်")
            if os.path.exists("test_result.png"):
                os.remove("test_result.png")

        except Exception as e:
            await message.reply(f"⚠️ <b>Error ဖြစ်သွားပါသည်:</b> {e}")
            await page.screenshot(path="test_error.png")
            photo = FSInputFile("test_error.png")
            await bot.send_photo(message.chat.id, photo, caption="📸 Error တက်သွားသော မျက်နှာပြင်")
            if os.path.exists("test_error.png"):
                os.remove("test_error.png")
            
        finally:
            await browser.close()
            await status_msg.delete() # ပြီးသွားပါက status စာသားကို ဖျက်မည်

async def main():
    print("🚀 Login Test Bot စတင်နေပါပြီ...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
