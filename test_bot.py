import asyncio
import os
import html
from dotenv import load_dotenv
from aiogram import Bot, Dispatcher, types
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.client.default import DefaultBotProperties
from aiogram.types import FSInputFile
from playwright.async_api import async_playwright

load_dotenv()
BOT_TOKEN = os.getenv("BOT_TOKEN")
bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

@dp.message(Command("testlogin"))
async def start_login_test(message: types.Message):
    parts = message.text.strip().split()
    if len(parts) != 3:
        return await message.reply("⚠️ ပုံစံ - <code>/testlogin ဖုန်းနံပါတ် Password</code>")
    
    # Bot မအေးအောင် background မှာ run ခိုင်းထားတယ်
    asyncio.create_task(run_playwright_login(message, parts[1], parts[2]))

async def run_playwright_login(message: types.Message, username, password):
    msg = await message.reply("🔄 <b>Browser စတင်နေပါသည်...</b>")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True, 
            args=['--no-sandbox', '--disable-setuid-sandbox']
        )
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36", 
            viewport={'width': 390, 'height': 844}, 
            is_mobile=True
        )
        page = await context.new_page()
        
        try:
            # စာမျက်နှာကို ဝင်ရောက်ခြင်း
            await page.goto("https://www.777bigwingame.app/#/login", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(3000)

            # 🔐 Username နဲ့ Password ကို safe နည်းနဲ့ ဖြည့်ခြင်း
            await page.fill('input[name="userNumber"]', username)
            
            # Password box ကိုရှာပြီးဖြည့်ခြင်း (Placeholder ၂မျိုးစမ်းကြည့်ထားတယ်)
            password_input = await page.query_selector('input[placeholder="စကားဝှက်"], input[placeholder="Password"]')
            if password_input:
                await password_input.fill(password)
            
            await page.wait_for_timeout(2000)

            # Login ခလုတ်ကိုနှိပ်ခြင်း (active မရှိရင် submit ကိုစမ်းနှိပ်)
            await page.evaluate("""
                () => {
                    let btn = document.querySelector('button.active') || document.querySelector('button[type="submit"]');
                    if (btn) btn.click();
                }
            """)
            
            await page.wait_for_timeout(5000)
            
            # Screenshot ရိုက်ခြင်း
            screenshot_path = "result.png"
            await page.screenshot(path=screenshot_path)
            
            # URL ကိုကြည့်ပြီး အောင်မြင်မအောင်မြင်စစ်ခြင်း
            if "login" not in page.url.lower():
                await message.reply("✅ <b>Login အောင်မြင်ပါသည်။</b>")
            else:
                await message.reply("❌ <b>Login မအောင်မြင်ပါ။</b> (Password မှားနေနိုင်သည်)")
                
            # Screenshot ပို့ပြီး ဖိုင်ကိုဖျက်ခြင်း
            await bot.send_photo(message.chat.id, FSInputFile(screenshot_path), caption="📸 ရလဒ်")
            if os.path.exists(screenshot_path): 
                os.remove(screenshot_path)

        except Exception as e:
            await message.reply(f"⚠️ Error: {html.escape(str(e))}")
        finally:
            # Browser ကိုပိတ်ပြီး Loading message ကိုဖျက်ခြင်း
            await browser.close()
            await msg.delete()

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
