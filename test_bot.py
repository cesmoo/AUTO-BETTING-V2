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
            "<code>/testlogin 09680090540 Mitheint11</code>"
        )
        
    username = parts[1]
    password = parts[2]
    
    asyncio.create_task(run_playwright_login(message, username, password))

# ==========================================
# 🤖 3. PLAYWRIGHT LOGIN LOGIC (TYPERROR FIXED)
# ==========================================
async def run_playwright_login(message: types.Message, username, password):
    await message.reply("🔄 <b>၁. Browser စတင်ဖွင့်နေပါသည်...</b>")
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=['--no-sandbox', '--disable-setuid-sandbox', '--disable-dev-shm-usage']
            )
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Linux; Android 10; K) AppleWebKit/537.36",
                viewport={'width': 390, 'height': 844}, 
                is_mobile=True, 
                has_touch=True  
            )
            page = await context.new_page()
            
            try:
                await message.reply("🌐 <b>၂. ဝဘ်ဆိုဒ်သို့ သွားနေပါသည်...</b>")
                await page.goto("https://www.777bigwingame.app/#/login", wait_until="networkidle", timeout=60000)
                await page.wait_for_timeout(3000)

                await message.reply("📱 <b>၃. အချက်အလက်များ ရိုက်ထည့်နေပါသည်...</b>")
                
                # 🔧 Fix: TypeError မတက်စေရန် window.HTMLInputElement.prototype မှတစ်ဆင့် Native Setter ကို တိုက်ရိုက်ယူပါမည်
                js_code = """
                ([user, pwd]) => {
                    function fillVueInput(element, value) {
                        if (!element) return false;
                        
                        // Native DOM setter ကို တိုက်ရိုက်လှမ်းခေါ်ခြင်း (TypeError ကို ရှောင်ရှားရန်)
                        const nativeSetter = Object.getOwnPropertyDescriptor(window.HTMLInputElement.prototype, 'value').set;
                        nativeSetter.call(element, value);
                        
                        // Vue.js အား အသိပေးခြင်း
                        element.dispatchEvent(new Event('input', { bubbles: true }));
                        element.dispatchEvent(new Event('change', { bubbles: true }));
                        return true;
                    }

                    let phone = document.querySelector('input[name="userNumber"]');
                    fillVueInput(phone, user);

                    let pass = document.querySelector('input[placeholder="စကားဝှက်"]') || 
                               document.querySelector('.passwordInput__container-input input') || 
                               document.querySelector('input[type="password"]');
                    fillVueInput(pass, pwd);
                }
                """
                
                await page.evaluate(js_code, [username, password])
                await page.wait_for_timeout(1000)

                await message.reply("🖱️ <b>၄. 'လော့ဂ်အင်' ခလုတ်ကို နှိပ်နေပါသည်...</b>")
                
                await page.evaluate("""
                () => {
                    let buttons = document.querySelectorAll('button.active, .signIn__container-button button, .signIn__container-button');
                    for (let btn of buttons) {
                        if (btn.innerText.includes('လော့ဂ်အင်') || btn.innerText.includes('Log in')) {
                            btn.click();
                            break;
                        } else if (btn.tagName === 'DIV') {
                            btn.click();
                        }
                    }
                }
                """)
                
                await message.reply("⏳ <b>၅. ဝင်သွားရန် ၅ စက္ကန့် စောင့်နေပါသည်...</b>")
                await page.wait_for_timeout(5000)

                await message.reply("📸 <b>၆. Screenshot ရိုက်ကူးနေပါသည်...</b>")
                await page.screenshot(path="test_result.png")
                
                if "login" not in page.url.lower():
                    await message.reply(f"✅ <b>ဝင်သွားပါပြီ! Login အောင်မြင်ပါသည်။</b>\nလက်ရှိ URL: {page.url}")
                else:
                    await message.reply("❌ <b>Login မအောင်မြင်သေးပါ။ Screenshot ကို စစ်ဆေးကြည့်ပါ။</b>\nလက်ရှိ URL: " + page.url)
                    
                if os.path.exists("test_result.png"):
                    photo = FSInputFile("test_result.png")
                    await bot.send_photo(message.chat.id, photo, caption="📸 နောက်ဆုံး ရောက်ရှိနေသော မျက်နှာပြင်")
                    os.remove("test_result.png")

            except Exception as inner_e:
                safe_error = html.escape(str(inner_e))
                await bot.send_message(message.chat.id, f"⚠️ <b>အတွင်းပိုင်း Error ဖြစ်သွားပါသည်:</b>\n<pre>{safe_error}</pre>")
                
                try:
                    await page.screenshot(path="test_error.png")
                    if os.path.exists("test_error.png"):
                        photo = FSInputFile("test_error.png")
                        await bot.send_photo(message.chat.id, photo, caption="📸 Error တက်သွားသော မျက်နှာပြင်")
                        os.remove("test_error.png")
                except:
                    pass
                
            finally:
                await browser.close()
                await message.reply("🏁 <b>စမ်းသပ်မှု ပြီးဆုံးပါပြီ။ Browser ပိတ်လိုက်ပါပြီ။</b>")

    except Exception as e:
        safe_error = html.escape(str(e))
        await bot.send_message(message.chat.id, f"🚨 <b>Browser စတင်ရန် ပျက်ကွက်ပါသည်:</b>\n<pre>{safe_error}</pre>")

async def main():
    print("🚀 Login Test Bot စတင်နေပါပြီ...")
    await bot.delete_webhook(drop_pending_updates=True)
    await dp.start_polling(bot)

if __name__ == '__main__':
    try: asyncio.run(main())
    except KeyboardInterrupt: pass
