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
    asyncio.create_task(run_playwright_login(message, parts[1], parts[2]))

async def run_playwright_login(message: types.Message, username, password):
    msg = await message.reply("🔄 <b>Browser စတင်နေပါသည်...</b>")
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, args=['--no-sandbox', '--disable-setuid-sandbox'])
        context = await browser.new_context(user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36", viewport={'width': 390, 'height': 844}, is_mobile=True)
        page = await context.new_page()
        
        try:
            await page.goto("https://www.777bigwingame.app/#/login", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(3000)

            # 🔧 JavaScript Injection ပိုမိုခိုင်မာအောင် ရေးသားခြင်း
            await page.evaluate(f"""
                async () => {{
                    const fill = (sel, val) => {{
                        let el = document.querySelector(sel);
                        if (!el) return;
                        el.focus();
                        el.value = val;
                        el.dispatchEvent(new Event('input', {{ bubbles: true }}));
                        el.dispatchEvent(new Event('change', {{ bubbles: true }}));
                        el.blur();
                    }};
                    fill('input[name="userNumber"]', '{username}');
                    fill('input[placeholder="စကားဝှက်"], input[placeholder="Password"]', '{password}');
                }}
            """)
            await page.wait_for_timeout(2000)

            # ခလုတ်ကို နှိပ်ခြင်း
            await page.evaluate("""
                () => {
                    let btn = document.querySelector('button.active');
                    if (btn) btn.click();
                }
            """)
            
            await page.wait_for_timeout(5000)
            await page.screenshot(path="result.png")
            
            if "login" not in page.url.lower():
                await message.reply("✅ <b>Login အောင်မြင်ပါသည်။</b>")
            else:
                await message.reply("❌ <b>Login မအောင်မြင်ပါ။</b>")
                
            await bot.send_photo(message.chat.id, FSInputFile("result.png"), caption="📸 ရလဒ်")
            if os.path.exists("result.png"): os.remove("result.png")

        except Exception as e:
            await message.reply(f"⚠️ Error: {html.escape(str(e))}")
        finally:
            await browser.close()
            await msg.delete()

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
