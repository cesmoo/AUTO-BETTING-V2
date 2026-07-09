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
BOT_TOKEN = os.getenv("BOT_TOKEN")

bot = Bot(token=BOT_TOKEN, default=DefaultBotProperties(parse_mode=ParseMode.HTML))
dp = Dispatcher()

# ==========================================
# 🎮 2. TELEGRAM COMMAND HANDLER
# ==========================================
@dp.message(Command("testlogin"))
async def start_login_test(message: types.Message):
    parts = message.text.strip().split()
    
    if len(parts) != 3:
        return await message.reply(
            "⚠️ ပုံစံမှားယွင်းနေပါသည်။ ကျေးဇူးပြု၍ အောက်ပါအတိုင်း ရိုက်ထည့်ပါ။\n\n"
            "<code>/testlogin ဖုန်းနံပါတ် Password</code>"
        )
        
    username = parts[1]
    password = parts[2]
    
    asyncio.create_task(run_playwright_login(message, username, password))

# ==========================================
# 🤖 3. PLAYWRIGHT LOGIN LOGIC (FIXED)
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

            await status_msg.edit_text("📱 <b>အချက်အလက်များ ရိုက်ထည့်နေပါသည်...</b>")
            
            # 🔧 ဤနေရာတွင် ဘာသာစကားမရွေး အလုပ်လုပ်သော CSS Class ကို အသုံးပြု၍ 
            # Vue.js အား အတင်းအကျပ် အသိအမှတ်ပြုခိုင်းသော နည်းလမ်းကို သုံးထားပါသည်။
            native_js = f"""
                function setNativeValue(element, value) {{
                    const valueSetter = Object.getOwnPropertyDescriptor(element, 'value').set;
                    const prototype = Object.getPrototypeOf(element);
                    const prototypeValueSetter = Object.getOwnPropertyDescriptor(prototype, 'value').set;
                    
                    if (valueSetter && valueSetter !== prototypeValueSetter) {{
                        prototypeValueSetter.call(element, value);
                    }} else {{
                        valueSetter.call(element, value);
                    }}
                    element.dispatchEvent(new Event('input', {{ bubbles: true }}));
                    element.dispatchEvent(new Event('change', {{ bubbles: true }}));
                }}

                // ဖုန်းနံပါတ် (Language Independent)
                let phone = document.querySelector('input[name="userNumber"]');
                if (phone) setNativeValue(phone, '{username}');

                // Password (Language Independent - Class ကိုသာ အသုံးပြုထားသည်)
                let pwd = document.querySelector('.passwordInput__container-input input');
                if (pwd) setNativeValue(pwd, '{password}');
            """
            
            await page.evaluate(native_js)
            await page.wait_for_timeout(1000)

            await status_msg.edit_text("🖱️ <b>Login ခလုတ်ကို နှိပ်နေပါသည်...</b>")
            # ခလုတ်ကိုလည်း ဘာသာစကားမရွေး နှိပ်နိုင်ရန် ပြင်ဆင်ထားသည်
            await page.evaluate("""
                let btn = document.querySelector('.signIn__container-button');
                if (btn) btn.click();
                
                // Fallback အတွက် Button အတိအကျကို ထပ်ရှာ၍နှိပ်မည်
                let innerBtn = document.querySelector('.signIn__container-button button.active');
                if (innerBtn) innerBtn.click();
            """)
            
            await status_msg.edit_text("⏳ <b>ဝင်သွားရန် ၅ စက္ကန့် စောင့်နေပါသည်...</b>")
            await page.wait_for_timeout(5000)

            await page.screenshot(path="test_result.png")
            
            if "login" not in page.url.lower():
                await message.reply(f"✅ <b>ဝင်သွားပါပြီ! Login အောင်မြင်ပါသည်။</b>\nလက်ရှိ URL: {page.url}")
            else:
                await message.reply("❌ <b>Login မအောင်မြင်သေးပါ။ Screenshot ကို စစ်ဆေးကြည့်ပါ။</b>")
                
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
            await status_msg.delete() 

async def main():
    print("🚀 Login Test Bot စတင်နေပါပြီ...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
