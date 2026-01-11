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
ADMIN_GIVE_SUB_USER, ADMIN_GIVE_SUB_DAYS = range(2, 4)
ADMIN_RESET_HWID_USER = 4
ADMIN_BAN_USER = 5

ADMIN_IDS = [int(os.getenv("ADMIN_ID", "7463401648"))]

def is_admin(user_id: int) -> bool:
    return user_id in ADMIN_IDS

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    
    keyboard = [
        [InlineKeyboardButton("📝 Регистрация", callback_data="register")],
        [InlineKeyboardButton("👤 Мой профиль", callback_data="profile")],
        [InlineKeyboardButton("🔄 Сбросить HWID", callback_data="reset_hwid")],
        [InlineKeyboardButton("📥 Скачать лоадер", callback_data="download_loader")],
    ]
    
    # Админ кнопки
    if is_admin(user_id):
        keyboard.append([InlineKeyboardButton("⚙️ Админ панель", callback_data="admin_panel")])
    
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
            await query.edit_message_text("❌ Вы не зарегистрированы\n\nНажмите /start и выберите Регистрация")
            return ConversationHandler.END
        
        sub_status = "✅ Активна" if await database.check_subscription(user['username']) else "❌ Истекла"
        hwid_status = "✅ Привязан" if user['hwid'] else "❌ Не привязан"
        
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_main")]]
        
        await query.edit_message_text(
            f"👤 *Ваш профиль*\n\n"
            f"Логин: `{user['username']}`\n"
            f"Подписка: {sub_status}\n"
            f"До: {user['subscription_end'] or 'N/A'}\n"
            f"HWID: {hwid_status}",
            parse_mode="Markdown",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END
    
    elif query.data == "reset_hwid":
        user = await database.get_user_by_telegram_id(query.from_user.id)
        if not user:
            await query.edit_message_text("❌ Вы не зарегистрированы")
            return ConversationHandler.END
        
        await database.reset_hwid(user['username'])
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_main")]]
        await query.edit_message_text(
            "✅ HWID сброшен!\n\nПри следующем входе привяжется новый компьютер.",
            reply_markup=InlineKeyboardMarkup(keyboard)
        )
        return ConversationHandler.END
    
    elif query.data == "back_main":
        user_id = query.from_user.id
        keyboard = [
            [InlineKeyboardButton("📝 Регистрация", callback_data="register")],
            [InlineKeyboardButton("👤 Мой профиль", callback_data="profile")],
            [InlineKeyboardButton("🔄 Сбросить HWID", callback_data="reset_hwid")],
            [InlineKeyboardButton("📥 Скачать лоадер", callback_data="download_loader")],
        ]
        if is_admin(user_id):
            keyboard.append([InlineKeyboardButton("⚙️ Админ панель", callback_data="admin_panel")])
        
        await query.edit_message_text(
            "🎮 *Matrix Client*\n\n"
            "Добро пожаловать в бот управления подпиской!\n\n"
            "Выберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    elif query.data == "download_loader":
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="back_main")]]
        
        # Ссылка на лоадер (обнови когда загрузишь .exe на GitHub)
        loader_url = os.getenv("LOADER_DOWNLOAD_URL", "")
        
        if loader_url:
            await query.edit_message_text(
                "📥 *Скачать Matrix Loader*\n\n"
                f"[Нажми чтобы скачать]({loader_url})\n\n"
                "После скачивания запусти и войди с логином/паролем.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text(
                "📥 *Скачать Matrix Loader*\n\n"
                "Лоадер пока недоступен. Обратитесь к администратору.",
                parse_mode="Markdown",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        return ConversationHandler.END
    
    # Админ панель
    elif query.data == "admin_panel":
        if not is_admin(query.from_user.id):
            await query.edit_message_text("❌ Нет доступа")
            return ConversationHandler.END
        
        keyboard = [
            [InlineKeyboardButton("🎁 Выдать подписку", callback_data="admin_give_sub")],
            [InlineKeyboardButton("🔄 Сбросить HWID", callback_data="admin_reset_hwid")],
            [InlineKeyboardButton("📋 Список юзеров", callback_data="admin_list_users")],
            [InlineKeyboardButton("🚫 Забанить", callback_data="admin_ban")],
            [InlineKeyboardButton("◀️ Назад", callback_data="back_main")],
        ]
        
        await query.edit_message_text(
            "⚙️ *Админ панель*\n\n"
            "Выберите действие:",
            reply_markup=InlineKeyboardMarkup(keyboard),
            parse_mode="Markdown"
        )
        return ConversationHandler.END
    
    elif query.data == "admin_give_sub":
        if not is_admin(query.from_user.id):
            return ConversationHandler.END
        
        await query.edit_message_text(
            "🎁 *Выдача подписки*\n\n"
            "Введите логин пользователя:",
            parse_mode="Markdown"
        )
        return ADMIN_GIVE_SUB_USER
    
    elif query.data == "admin_reset_hwid":
        if not is_admin(query.from_user.id):
            return ConversationHandler.END
        
        await query.edit_message_text(
            "🔄 *Сброс HWID*\n\n"
            "Введите логин пользователя:",
            parse_mode="Markdown"
        )
        return ADMIN_RESET_HWID_USER
    
    elif query.data == "admin_list_users":
        if not is_admin(query.from_user.id):
            return ConversationHandler.END
        
        users = await database.get_all_users()
        if not users:
            text = "📋 Пользователей нет"
        else:
            text = "📋 *Список пользователей:*\n\n"
            for u in users[:20]:  # Максимум 20
                sub_ok = "✅" if await database.check_subscription(u['username']) else "❌"
                text += f"{sub_ok} `{u['username']}`\n"
        
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data="admin_panel")]]
        await query.edit_message_text(text, parse_mode="Markdown", reply_markup=InlineKeyboardMarkup(keyboard))
        return ConversationHandler.END
    
    elif query.data == "admin_ban":
        if not is_admin(query.from_user.id):
            return ConversationHandler.END
        
        await query.edit_message_text(
            "🚫 *Бан пользователя*\n\n"
            "Введите логин пользователя:",
            parse_mode="Markdown"
        )
        return ADMIN_BAN_USER
    
    return ConversationHandler.END

# Регистрация
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
            f"Для активации подписки обратитесь к администратору.\n\n"
            f"Нажмите /start для возврата в меню.",
            parse_mode="Markdown"
        )
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка регистрации: {e}")
    
    return ConversationHandler.END

# Админ: выдача подписки
async def admin_give_sub_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    user = await database.get_user_by_username(username)
    
    if not user:
        await update.message.reply_text("❌ Пользователь не найден. Попробуйте ещё раз:")
        return ADMIN_GIVE_SUB_USER
    
    context.user_data['admin_target_user'] = username
    await update.message.reply_text(f"Пользователь: `{username}`\n\nВведите количество дней подписки:", parse_mode="Markdown")
    return ADMIN_GIVE_SUB_DAYS

async def admin_give_sub_days(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        days = int(update.message.text.strip())
    except ValueError:
        await update.message.reply_text("❌ Введите число")
        return ADMIN_GIVE_SUB_DAYS
    
    username = context.user_data['admin_target_user']
    end_date = datetime.now() + timedelta(days=days)
    await database.set_subscription(username, end_date)
    
    await update.message.reply_text(
        f"✅ Подписка выдана!\n\n"
        f"Пользователь: `{username}`\n"
        f"До: {end_date.strftime('%Y-%m-%d')}\n\n"
        f"/start - вернуться в меню",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# Админ: сброс HWID
async def admin_reset_hwid_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    user = await database.get_user_by_username(username)
    
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return ConversationHandler.END
    
    await database.reset_hwid(username)
    await update.message.reply_text(
        f"✅ HWID сброшен для `{username}`\n\n/start - вернуться в меню",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

# Админ: бан
async def admin_ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    username = update.message.text.strip()
    user = await database.get_user_by_username(username)
    
    if not user:
        await update.message.reply_text("❌ Пользователь не найден")
        return ConversationHandler.END
    
    await database.ban_user(username)
    await update.message.reply_text(
        f"🚫 Пользователь `{username}` забанен\n\n/start - вернуться в меню",
        parse_mode="Markdown"
    )
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Отменено. /start - вернуться в меню")
    return ConversationHandler.END

def main():
    app = Application.builder().token(BOT_TOKEN).build()
    
    # Главный обработчик диалогов
    conv_handler = ConversationHandler(
        entry_points=[
            CallbackQueryHandler(button_handler),
        ],
        states={
            REGISTER_USERNAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_username)],
            REGISTER_PASSWORD: [MessageHandler(filters.TEXT & ~filters.COMMAND, register_password)],
            ADMIN_GIVE_SUB_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_give_sub_user)],
            ADMIN_GIVE_SUB_DAYS: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_give_sub_days)],
            ADMIN_RESET_HWID_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_reset_hwid_user)],
            ADMIN_BAN_USER: [MessageHandler(filters.TEXT & ~filters.COMMAND, admin_ban_user)],
        },
        fallbacks=[CommandHandler("cancel", cancel), CommandHandler("start", start)],
    )
    
    app.add_handler(CommandHandler("start", start))
    app.add_handler(conv_handler)
    
    print("Bot started!")
    app.run_polling()

if __name__ == "__main__":
    asyncio.run(database.init_db())
    main()
