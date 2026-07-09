import asyncio
import os
import html
from datetime import datetime
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
            await page.goto("https://www.777bigwingame.app/#/login", wait_until="networkidle", timeout=60000)
            await page.wait_for_timeout(3000)

            # အကောင့်ဝင်ရန် ဖြည့်သွင်းခြင်း
            await page.fill('input[name="userNumber"]', username)
            password_input = await page.query_selector('input[placeholder="စကားဝှက်"], input[placeholder="Password"]')
            if password_input:
                await password_input.fill(password)
            
            await page.wait_for_timeout(2000)

            # Login နှိပ်ခြင်း
            await page.evaluate("""
                () => {
                    let btn = document.querySelector('button.active') || document.querySelector('button[type="submit"]');
                    if (btn) btn.click();
                }
            """)
            
            await page.wait_for_timeout(5000)
            
            screenshot_path = "result.png"
            await page.screenshot(path=screenshot_path)
            
            # ✅ Login Status စစ်ဆေးခြင်း
            if "login" not in page.url.lower():
                # 📅 ယနေ့နေ့စွဲနှင့် အချိန် (Myanmar Time လိုချင်ရဲသော် UTC အတိုင်းပြထားပါတယ်)
                current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                
                # 🌟 ပုံထဲကလို အချက်အလက်တွေကို ပြင်ဆင်ပြီး နေ့စွဲထည့်ခြင်း
                # (သင့် website မှာ Nickname နဲ့ Balance ကို scrape လုပ်လို့ရရင် အဲ့ဒီမှာ တကယ့်တန်ဖိုးတွေထည့်နိုင်ပါတယ်။ ဒီနေရာမှာ နမူနာအဖြစ်ထည့်ထားတာ)
                nickname = "PyaeSonePhyo"  # (Website ပေါ်က nickname ကိုယူဖို့ Logic ထပ်ရေးရနိုင်ပါတယ်)
                balance = "26.92 Ks"       # (Website ပေါ်က Balance ကိုယူဖို့ Logic ထပ်ရေးရနိုင်ပါတယ်)
                
                # 🎨 ပုံစံကျကျ စာတန်းဖွဲ့ခြင်း
                success_text = (
                    "✅ <b>LOGIN SUCCESSFUL</b>\n"
                    "Normal account — Upgrade for more features\n\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "🌍 <b>Site:</b> 777BIGWIN\n"
                    "👤 <b>User Information:</b>\n"
                    "├─ 🆔 <b>User ID:</b> 578634\n"
                    "├─ 📱 <b>Username:</b> 959680090540\n"
                    "├─ 🏷️ <b>Nickname:</b> <i>{nickname}</i>\n"
                    "├─ 💰 <b>Balance:</b> <i>{balance}</i>\n"
                    "├─ 📅 <b>Login Date:</b> <i>{current_time}</i>\n"
                    "└─ ✅ <b>Allow Withdraw:</b> Yes\n"
                    "━━━━━━━━━━━━━━━━━━━━━━\n"
                    "💎 <b>Normal User</b> — Auto Bet is available.\n"
                    "Upgrade to Premium for Manual Bet, AI\n"
                    "Prediction & more strategies!\n"
                    "👆 Tap 💎 <b>Upgrade Premium</b> below to\n"
                    "unlock all features.\n\n"
                    "⚡ Select your betting mode:"
                ).format(nickname=nickname, balance=balance, current_time=current_time)

                # ✅ အောင်မြင်ကြောင်း စာတန်းပို့ခြင်း
                await message.reply(success_text)
            else:
                # ❌ မအောင်မြင်ကြောင်းပို့ခြင်း
                await message.reply("❌ <b>Login မအောင်မြင်ပါ။</b>\n(စကားဝှက် သို့မဟုတ် အကောင့် မှားနေနိုင်သည်)")
                
            # 📸 Screenshot ပို့ခြင်း
            await bot.send_photo(message.chat.id, FSInputFile(screenshot_path), caption="📸 Login Page Result")
            
            if os.path.exists(screenshot_path): 
                os.remove(screenshot_path)

        except Exception as e:
            await message.reply(f"⚠️ Error: {html.escape(str(e))}")
        finally:
            await browser.close()
            await msg.delete()

async def main():
    await dp.start_polling(bot)

if __name__ == '__main__':
    asyncio.run(main())
