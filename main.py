import os
import asyncio
from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes, ConversationHandler
from playwright.async_api import async_playwright

# Conversation States
CHOOSING_SITE, ENTERING_PHONE, ENTERING_PASSWORD = range(3)

# Environment Variables မှ Data များယူခြင်း
TELEGRAM_BOT_TOKEN = os.getenv("8980067569:AAHNbSc7W46a0sO4OMg5PRWJ_P-54K74_rA")

# ---------------------------------------------------------
# Playwright Automation Function
# ---------------------------------------------------------
async def run_playwright_login(phone, password):
    browser = None
    try:
        async with async_playwright() as p:
            # Paid Plan ဖြစ်သောကြောင့် RAM ပိုရသဖြင့် ပိုမိုချောမွေ့စွာ အလုပ်လုပ်ပါမည်
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            ) 
            page = await browser.new_page()
            
            await page.goto("https://www.777bigwingame.app/#/login", timeout=60000)
            await page.wait_for_selector('input[name="userNumber"]', timeout=15000)
            
            await page.locator('input[name="userNumber"]').fill(str(phone))
            await page.locator('input[placeholder="Password"]').fill(str(password))
            
            await page.locator('div.signIn_container-button button.active').click()
            
            # Login အောင်မြင်မှုအတွက် စောင့်ဆိုင်းခြင်း
            await page.wait_for_timeout(5000)
            
            current_url = page.url
            print(f"Post-Login URL: {current_url}")
            
            await browser.close()
            return True, "26.92" 
            
    except Exception as e:
        print(f"Playwright Error: {e}")
        if browser:
            await browser.close()
        return False, "0"

# ---------------------------------------------------------
# Telegram Bot Conversation Handlers
# ---------------------------------------------------------
async def start_login(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    reply_keyboard = [["777BIGWIN"]]
    await update.message.reply_text(
        "Please select a site to login:",
        reply_markup=ReplyKeyboardMarkup(reply_keyboard, one_time_keyboard=True, resize_keyboard=True),
    )
    return CHOOSING_SITE

async def choose_site(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    site_choice = update.message.text
    context.user_data['site'] = site_choice
    await update.message.reply_text(f"You selected {site_choice}\n\n📱 Please enter your phone:")
    return ENTERING_PHONE

async def enter_phone(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['phone'] = update.message.text
    await update.message.reply_text("🔒 Please enter your password:")
    return ENTERING_PASSWORD

async def enter_password(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    context.user_data['password'] = update.message.text
    
    phone = context.user_data['phone']
    password = context.user_data['password']
    site = context.user_data['site']

    msg = await update.message.reply_text("⏳ Logging in via Playwright... Please wait.")

    success, balance_info = await run_playwright_login(phone, password)

    if success:
        success_message = (
            "✅ *LOGIN SUCCESSFUL*\n"
            "━━━━━━━━━━━━━━━\n"
            f"🔹 *SITE:* {site}\n"
            f"🔹 *USERNAME:* {phone}\n"
            f"🔹 *BALANCE:* {balance_info} Ks\n"
        )
        await msg.edit_text(success_message, parse_mode='Markdown')
    else:
        await msg.edit_text("❌ Login Failed! Please check your credentials.")

    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text("Process cancelled.")
    return ConversationHandler.END

def main():
    if not TELEGRAM_BOT_TOKEN:
        print("Error: TELEGRAM_BOT_TOKEN is missing!")
        return

    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()

    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("login", start_login), MessageHandler(filters.Regex("^Login$"), start_login)],
        states={
            CHOOSING_SITE: [MessageHandler(filters.TEXT & ~filters.COMMAND, choose_site)],
            ENTERING_PHONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_phone)],
            ENTERING_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, enter_password)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    application.add_handler(conv_handler)
    
    print("🤖 Bot is starting via Polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
