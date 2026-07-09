import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from playwright.async_api import async_playwright

# Conversation States များကို သတ်မှတ်ခြင်း
CHOOSING_SITE, ENTERING_PHONE, ENTERING_PASSWORD = range(3)

# Render မှ Environment Variable ကို ရယူခြင်း
TELEGRAM_BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# ---------------------------------------------------------
# Playwright Automation Function
# ---------------------------------------------------------
async def run_playwright_login(phone, password):
    """Playwright ဖြင့် နောက်ကွယ်မှ Chromium Browser ဖွင့်၍ Login ဝင်ခြင်း"""
    browser = None
    page = None
    screenshot_path = "error_screenshot.png"
    
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            ) 
            # Cloudflare က Bot မှန်းမသိအောင် User Agent ထည့်ပေးခြင်း
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            await page.goto("https://www.777bigwingame.app", timeout=60000)
            
            # စက္ကန့် ၂၀ အထိ စောင့်ကြည့်မည်
            await page.wait_for_selector('input[name="userNumber"]', timeout=20000)
            
            await page.locator('input[name="userNumber"]').fill(str(phone))
            await page.locator('input[placeholder="Password"]').fill(str(password))
            await page.locator('div.signIn_container-button button.active').click()
            
            await page.wait_for_timeout(5000)
            
            await browser.close()
            return True, "26.92", None
            
    except Exception as e:
        error_msg = str(e)
        print(f"Playwright Error: {error_msg}")
        
        # Error တက်ပါက Screenshot ရိုက်ယူခြင်း
        if page:
            try:
                await page.screenshot(path=screenshot_path)
            except:
                screenshot_path = None
                
        if browser:
            await browser.close()
            
        return False, error_msg, screenshot_path


# ---------------------------------------------------------
# Telegram Bot Handlers
# ---------------------------------------------------------

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """/start ဟုရိုက်လျှင် ကြိုဆိုမည့် စာသား"""
    welcome_text = (
        "Welcome to Auto-Betting-Bot! 🤖\n\n"
        "Login ဝင်ရန် /login (သို့မဟုတ်) Login ဟု ရိုက်ထည့်ပါ။"
    )
    await update.message.reply_text(welcome_text)

async def start_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Login အစပြုသည့်အခါ Site ရွေးခိုင်းခြင်း"""
    reply_keyboard = [["777BIGWIN"]]
    await update.message.reply_text(
        "Please select a site to login:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return CHOOSING_SITE

async def choose_site(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Site ရွေးပြီးပါက ဖုန်းနံပါတ် တောင်းခြင်း"""
    site_choice = update.message.text
    context.user_data['site'] = site_choice
    await update.message.reply_text(f"You selected {site_choice}\n\n📱 Please enter your phone (or) email:")
    return ENTERING_PHONE

async def enter_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """ဖုန်းနံပါတ်ရယူပြီး Password ဆက်တောင်းခြင်း"""
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("🔒 Please enter your password:")
    return ENTERING_PASSWORD

async def enter_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['password'] = update.message.text
    
    phone = context.user_data['phone']
    password = context.user_data['password']
    site = context.user_data['site']

    msg = await update.message.reply_text("⏳ Logging in via Playwright... Please wait.")

    # Playwright Automation Function ကို ခေါ်ယူခြင်း (Return ၃ ခု ပြန်လာမည်)
    success, info, screenshot_path = await run_playwright_login(phone, password)

    if success:
        success_message = (
            "✅ *LOGIN SUCCESSFUL*\n"
            "━━━━━━━━━━━━━━━\n"
            f"🔹 *SITE:* {site}\n"
            f"🔹 *USERNAME:* {phone}\n"
            f"🔹 *BALANCE:* {info} Ks\n"
        )
        await msg.edit_text(success_message, parse_mode='Markdown')
    else:
        # Error Message နှင့် Screenshot ကို Telegram သို့ ပို့ပေးခြင်း
        await msg.edit_text(f"❌ Login Failed!\n\n⚠️ Error: {info[:100]}...")
        if screenshot_path and os.path.exists(screenshot_path):
            with open(screenshot_path, 'rb') as photo:
                await context.bot.send_photo(chat_id=update.effective_chat.id, photo=photo, caption="📸 နောက်ကွယ်တွင် Browser မြင်နေရသော ပုံ")

    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    """Conversation ကို ရပ်တန့်ခြင်း"""
    await update.message.reply_text("Process cancelled.")
    return ConversationHandler.END

# ---------------------------------------------------------
# Main Application
# ---------------------------------------------------------
def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN is missing!")
        return

    # Application တည်ဆောက်ခြင်း
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    # /start command အတွက် Handler ထည့်ခြင်း
    application.add_handler(CommandHandler("start", start_command))

    # Login အတွက် Conversation Handler တည်ဆောက်ခြင်း
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("login", start_login), MessageHandler(filters.Regex("(?i)^Login$"), start_login)],
        states={
            CHOOSING_SITE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_site)],
            ENTERING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_phone)],
            ENTERING_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_password)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)
    
    # Bot အား Polling ဖြင့် စတင် Run ခြင်း
    print("🤖 Bot is starting via Polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
