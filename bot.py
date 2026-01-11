import asyncio
import os
from datetime import datetime, timedelta
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackQueryHandler, ContextTypes, filters, ConversationHandler
from passlib.context import CryptContext

import database
from config import BOT_TOKEN

pwd_context = CryptContext(schemes=["bcrypt"], deprecated="auto")

# States
REGISTER_USERNAME, REGISTER_PASSWORD = range(2)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    keyboard = [
        [InlineKeyboardButton("📝 Регистрация", callback_data="register")],
        [InlineKeyboardButton("👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton("🔄 Сбросить HWID", callback_data="reset_hwid")],
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await update.message.reply_text(
        "🎮 *Matrix Client*\n\n"
        "Добро пожаловать в бот управления подпиской!\n\n"
        "Выберите действие:",
        reply_markup=reply_markup,
        parse_mode="Markdown"
    )

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    if query.data == "register":
        await query.edit_message_text(
            "📝 *Регистрация*\n\n"
            "Введите желаемый логин:",
            parse_mode="Markdown"
        )
        return REGISTER_USERNAME
    
    elif query.data == "profile":
        user = await database.get_user_by_telegram_id(query.from_user.id)
        if not user:
            await query.edit_message_text("❌ Вы не зарегистрированы")
            return
        
        sub_status = "✅ Активна" if await database.check_subscription(user['username']) else "❌ Истекла"
        hwid_status = "✅ Привязан" if user['hwid'] else "❌ Не привязан"
        
        await query.edit_message_text(
            f"👤 *Ваш профиль*\n\n"
            f"Логин: `{user['username']}`\n"
            f"Подписка: {sub_status}\n"
            f"До: {user['subscription_end'] or 'N/A'}\n"
            f"HWID: {hwid_status}",
            parse_mode="Markdown"
        )
    
    elif query.data == "reset_hwid":
        user = await database.get_user_by_telegram_id(query.from_user.id)
        if not user:
            await query.edit_message_text("❌ Вы не зарегистрированы")
            return
        
        await database.reset_hwid(user['username'])
        await query.edit_message_text("✅ HWID сброшен. При следующем входе привяжется новый компьютер.")

async def register_username(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    
    if len(username) < 3 or len(username) > 20:
        await update.message.reply_text("❌ Логин должен быть от 3 до 20 символов")
        return REGISTER_USERNAME
    
    existing = await database.get_user_by_username(username)
    if existing:
        await update.message.reply_text("❌ Этот логин уже занят")
        return REGISTER_USERNAME
    
    context.user_data['reg_username'] = username
    await update.message.reply_text("Введите пароль (минимум 6 символов):")
    return REGISTER_PASSWORD

async def register_password(update: Update, context: ContextTypes.DEFAULT_TYPE):
    password = update.message.text
    
    if len(password) < 6:
        await update.message.reply_text("❌ Пароль должен быть минимум 6 символов")
        return REGISTER_PASSWORD
    
    username = context.user_data['reg_username']
    password_hash = pwd_context.hash(password)
    
    try:
        await database.create_user(
            telegram_id=update.effective_user.id,
            username=username,
            password_hash=password_hash
        )
        
        await update.message.reply_text(
            f"✅ *Регистрация успешна!*\n\n"
            f"Логин: `{username}`\n\n"
            f"Для активации подписки обратитесь к администратору.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка регистрации: {e}")
    
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено")
    return ConversationHandler.END

# Админ команды
async def give_sub(update: Update, context: ContextTypes.DEFAULT_TYPE):
    # Проверка что это админ
    ADMIN_IDS = [int(os.getenv("ADMIN_ID", "7463401648"))]
    
    if update.effective_user.id not in ADMIN_IDS:
        return
    
    if len(context.args) < 2:
        await update.message.reply_text("Использование: /givesub username days")
        return
    
    username = context.args[0]
    days = int(context.args[1])
    
    end_date = datetime.now() + timedelta(days=days)
    await database.set_subscription(username, end_date)
    
    await update.message.reply_text(f"✅ Подписка выдана {username} до {end_date.strftime('%Y-%m-%d')}")

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Регистрация
    conv_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(button_handler, pattern="^register$")],
        states={
            REGISTER_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_username)],
            REGISTER_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_password)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    app.add_handler(CallbackQueryHandler(button_handler))
    app.add_handler(CommandHandler("givesub", give_sub))
    
    print("Bot started!")
    app.run_polling()

if __name__ == "__main__":
    asyncio.run(database.init_db())
    main()
