import logging
import sqlite3
import socket
import sys
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes, PreCheckoutQueryHandler, MessageHandler, filters
from datetime import datetime

BOT_TOKEN = "8401230506:AAELlpnPJAHhSfQu1fAUZW7VjvWbXFOQYI8"
ADMIN_ID = 8000395560

logging.basicConfig(level=logging.INFO)

def check_single_instance():
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.bind(('localhost', 12345))
        return True
    except socket.error:
        print("❌ Бот уже запущен! pkill -f python")
        sys.exit(1)

check_single_instance()

def init_db():
    conn = sqlite3.connect('payments.db')
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS payments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            username TEXT,
            first_name TEXT,
            charge_id TEXT,
            amount INTEGER,
            product_name TEXT,
            timestamp DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            username TEXT,
            first_name TEXT,
            is_banned BOOLEAN DEFAULT FALSE,
            has_subscription BOOLEAN DEFAULT FALSE,
            join_date DATETIME DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS admin_settings (
            key TEXT PRIMARY KEY,
            value TEXT
        )
    ''')
    cursor.execute('INSERT OR IGNORE INTO admin_settings (key, value) VALUES ("new_users_notifications", "on")')
    conn.commit()
    conn.close()

init_db()

PRODUCTS = {
    "premium": {"name": "🌟 Premium Подписка", "price": 70, "description": "Доступ к приватному каналу на 30 дней"},
    "video_100": {"name": "🎬 100 Видео", "price": 15, "description": "Пакет из 100 премиум видео"},
    "video_1000": {"name": "📹 1000 Видео", "price": 25, "description": "Пакет из 1000 премиум видео"},
    "video_10000": {"name": "🎥 10000 Видео + Канал", "price": 50, "description": "10000 видео + доступ к каналу"}
}

def get_admin_setting(key):
    conn = sqlite3.connect('payments.db')
    cursor = conn.cursor()
    cursor.execute('SELECT value FROM admin_settings WHERE key = ?', (key,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else "on"

def set_admin_setting(key, value):
    conn = sqlite3.connect('payments.db')
    cursor = conn.cursor()
    cursor.execute('INSERT OR REPLACE INTO admin_settings (key, value) VALUES (?, ?)', (key, value))
    conn.commit()
    conn.close()

async def notify_admin(context: ContextTypes.DEFAULT_TYPE, message: str):
    try:
        await context.bot.send_message(ADMIN_ID, message, parse_mode='Markdown')
    except Exception as e:
        logging.error(f"Ошибка отправки админу: {e}")

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    conn = sqlite3.connect('payments.db')
    cursor = conn.cursor()
    
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user.id,))
    existing_user = cursor.fetchone()
    
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)',
                   (user.id, user.username, user.first_name))
    conn.commit()
    conn.close()
    
    if not existing_user and get_admin_setting("new_users_notifications") == "on":
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"""🆕 *НОВЫЙ ПОЛЬЗОВАТЕЛЬ*

👤 Имя: {user.first_name}
📛 Ник: @{user.username or 'нет'}
🆔 ID: `{user.id}`
🕐 Время: {current_time}"""
        await notify_admin(context, message)

    keyboard = [
        [InlineKeyboardButton("🌟 Premium Подписка - 70 звезд", callback_data="premium")],
        [InlineKeyboardButton("📁 Видео", callback_data="videos")],
        [InlineKeyboardButton("💬 Тех. Поддержка", callback_data="support")],
        [InlineKeyboardButton("ℹ️ О боте", callback_data="about")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = """🛍️ *Добро пожаловать в магазин!*

Выберите раздел:"""
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "videos":
        keyboard = [
            [InlineKeyboardButton("🎬 100 Видео - 15 звезд", callback_data="video_100")],
            [InlineKeyboardButton("📹 1000 Видео - 25 звезд", callback_data="video_1000")],
            [InlineKeyboardButton("🎥 10000 Видео + Канал - 50 звезд", callback_data="video_10000")],
            [InlineKeyboardButton("🔙 Назад", callback_data="back_main")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📁 *Раздел с видео*\n\nВыберите пакет:", reply_markup=reply_markup, parse_mode='Markdown')

    elif query.data == "support":
        context.user_data['awaiting_support'] = True
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = """💬 *Техническая поддержка*

Напишите ваш вопрос и администратор скоро ответит.

Просто напишите сообщение с вашим вопросом:"""
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    elif query.data == "about":
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_main")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        text = """🎁 ЭкcклюzивHый koHтeHт, kotopый Bы He H@йдеTe бoльwе Hигде

Этoт бот oткpывает двеpи к HеoгpaHиченHому пoтoky экcклюzивHогo koHтeHта, дocтуп к kotopому Bы мoжеtе пoлyчить tольkо y Hас! Mы пpеdlагаем дocтупHые, безопасHые и аHоHимHые yсlуги.

🌟 Pрemиum-Подпucка
Достуp к пpиватHому kаHаlу c более чем 30.000 tыcяч видео подобHогo xаракtера. В cлучае yдаlения осHовHогo kаHаlа, мы гоtовы пpедоставить Bам достуp к доpолHиtельHому!

📁 Видеоrакеты
РазlичHые pакеты видеомаtеpиалoв pо пpивлекаtеlьHым ценам. Рассмаtрuвайtе этo как возможность опробовать Hаwи yслyги перед tем, kак пpиобpеcти pодписку.

ВозpастHые огpаничения: от 14 до 18 леt."""
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    elif query.data == "back_main":
        context.user_data.pop('awaiting_support', None)
        keyboard = [
            [InlineKeyboardButton("🌟 Premium Подписка - 70 звезд", callback_data="premium")],
            [InlineKeyboardButton("📁 Видео", callback_data="videos")],
            [InlineKeyboardButton("💬 Тех. Поддержка", callback_data="support")],
            [InlineKeyboardButton("ℹ️ О боте", callback_data="about")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("🛍️ *Добро пожаловать в магазин!*\n\nВыберите раздел:", reply_markup=reply_markup, parse_mode='Markdown')

    elif query.data in PRODUCTS:
        product = PRODUCTS[query.data]
        await context.bot.send_invoice(
            chat_id=query.message.chat_id,
            title=product["name"],
            description=product["description"],
            payload=query.data,
            currency="XTR",
            prices=[{"label": "Stars", "amount": product["price"]}],
        )

# Админские команды
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 Быстрая рассылка", callback_data="quick_broadcast")],
        [InlineKeyboardButton("🔔 Уведомления ВКЛ", callback_data="notifications_off"), 
         InlineKeyboardButton("🔕 Уведомления ВЫКЛ", callback_data="notifications_on")],
        [InlineKeyboardButton("👥 Все пользователи", callback_data="all_users")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = """👑 *Панель администратора*

Выберите действие:"""
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()

    if query.data == "admin_stats":
        conn = sqlite3.connect('payments.db')
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM users')
        total_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM payments')
        total_payments = cursor.fetchone()[0]
        
        cursor.execute('SELECT SUM(amount) FROM payments')
        total_stars = cursor.fetchone()[0] or 0
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE has_subscription = TRUE')
        premium_users = cursor.fetchone()[0]
        
        cursor.execute('SELECT COUNT(*) FROM users WHERE DATE(join_date) = DATE("now")')
        new_today = cursor.fetchone()[0]
        
        conn.close()

        text = f"""📊 *Статистика за все время*

👥 Всего пользователей: {total_users}
💎 Премиум пользователей: {premium_users}
💰 Всего платежей: {total_payments}
⭐ Всего звезд: {total_stars}
🆕 Новых сегодня: {new_today}"""

        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_admin")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

    elif query.data == "quick_broadcast":
        context.user_data['awaiting_broadcast'] = True
        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_admin")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        await query.edit_message_text("📢 *Быстрая рассылка*\n\nВведите сообщение для рассылки:", reply_markup=reply_markup, parse_mode='Markdown')

    elif query.data == "notifications_on":
        set_admin_setting("new_users_notifications", "on")
        await query.edit_message_text("✅ Уведомления о новых пользователях ВКЛЮЧЕНЫ")

    elif query.data == "notifications_off":
        set_admin_setting("new_users_notifications", "off")
        await query.edit_message_text("✅ Уведомления о новых пользователях ВЫКЛЮЧЕНЫ")

    elif query.data == "all_users":
        conn = sqlite3.connect('payments.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, username, first_name, join_date FROM users ORDER BY join_date DESC')
        users = cursor.fetchall()
        conn.close()

        if not users:
            await query.edit_message_text("📭 Пользователей нет")
            return

        text = f"👥 *Все пользователи ({len(users)}):*\n\n"
        for user in users:
            user_id, username, first_name, join_date = user
            text += f"👤 {first_name} (@{username or 'нет'})\n🆔 {user_id}\n🕐 {join_date}\n\n"

        keyboard = [[InlineKeyboardButton("🔙 Назад", callback_data="back_admin")]]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        # Разбиваем сообщение если слишком длинное
        if len(text) > 4096:
            parts = [text[i:i+4096] for i in range(0, len(text), 4096)]
            await query.edit_message_text(parts[0], reply_markup=reply_markup)
            for part in parts[1:]:
                await context.bot.send_message(chat_id=query.message.chat_id, text=part)
        else:
            await query.edit_message_text(text, reply_markup=reply_markup)

    elif query.data == "back_admin":
        await admin_panel_callback(update, context)

async def admin_panel_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 Быстрая рассылка", callback_data="quick_broadcast")],
        [InlineKeyboardButton("🔔 Уведомления ВКЛ", callback_data="notifications_off"), 
         InlineKeyboardButton("🔕 Уведомления ВЫКЛ", callback_data="notifications_on")],
        [InlineKeyboardButton("👥 Все пользователи", callback_data="all_users")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = """👑 *Панель администратора*

Выберите действие:"""
    await query.edit_message_text(text, reply_markup=reply_markup, parse_mode='Markdown')

# Обработчик текстовых сообщений
async def handle_text_messages(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.message.from_user.id
    
    if context.user_data.get('awaiting_support'):
        user = update.message.from_user
        question = update.message.text

        admin_msg = f"""💬 *НОВЫЙ ВОПРОС В ТЕХПОДДЕРЖКУ*

👤 Пользователь: {user.first_name} (@{user.username or 'нет'})
🆔 ID: {user.id}
🕐 Время: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

❓ Вопрос:
{question}"""

        await notify_admin(context, admin_msg)
        await update.message.reply_text("✅ Ваш вопрос отправлен администратору. Ожидайте ответа в ближайшее время!")
        context.user_data.pop('awaiting_support', None)

    elif context.user_data.get('awaiting_broadcast') and user_id == ADMIN_ID:
        message = update.message.text
        conn = sqlite3.connect('payments.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE is_banned = FALSE')
        users = cursor.fetchall()
        conn.close()

        sent = 0
        failed = 0
        for user in users:
            try:
                await context.bot.send_message(user[0], f"📢 *Рассылка:*\n\n{message}", parse_mode='Markdown')
                sent += 1
            except:
                failed += 1

        context.user_data.pop('awaiting_broadcast', None)
        await update.message.reply_text(f"✅ Рассылка завершена!\n\n📤 Отправлено: {sent}\n❌ Не отправлено: {failed}")

    # Обработка ответов админа на вопросы
    elif context.user_data.get('awaiting_reply') and user_id == ADMIN_ID:
        user_id_to_reply = context.user_data.get('reply_user_id')
        message = update.message.text
        
        try:
            await context.bot.send_message(
                user_id_to_reply, 
                f"💬 *ОТВЕТ АДМИНИСТРАТОРА:*\n\n{message}", 
                parse_mode='Markdown'
            )
            await update.message.reply_text(f"✅ Ответ отправлен пользователю {user_id_to_reply}")
        except Exception as e:
            await update.message.reply_text(f"❌ Ошибка отправки: {e}")
        
        context.user_data.pop('awaiting_reply', None)
        context.user_data.pop('reply_user_id', None)

# Команда для ответа на вопросы техподдержки
async def reply_to_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    if len(context.args) < 2:
        await update.message.reply_text("❌ Используй: /reply <user_id> <сообщение>")
        return

    try:
        user_id = int(context.args[0])
        message = ' '.join(context.args[1:])

        await context.bot.send_message(
            user_id, 
            f"💬 *ОТВЕТ АДМИНИСТРАТОРА:*\n\n{message}", 
            parse_mode='Markdown'
        )
        await update.message.reply_text(f"✅ Ответ отправлен пользователю {user_id}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

# Команда для отправки сообщения от имени администратора
async def tell_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    if len(context.args) < 2:
        await update.message.reply_text("❌ Используй: /tell <user_id> <сообщение>")
        return

    try:
        user_id = int(context.args[0])
        message = ' '.join(context.args[1:])

        await context.bot.send_message(
            user_id, 
            f"👑 *АДМИНИСТРАТОР:*\n\n{message}", 
            parse_mode='Markdown'
        )
        await update.message.reply_text(f"✅ Сообщение отправлено пользователю {user_id}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

# Команда для ответа на последний вопрос (удобно для быстрого ответа)
async def quick_reply(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("❌ Используй: /quick <сообщение>")
        return

    # Здесь можно добавить логику для получения последнего вопроса
    # Пока просто запрашиваем ID пользователя
    context.user_data['awaiting_quick_reply'] = True
    message = ' '.join(context.args)
    context.user_data['quick_reply_message'] = message
    
    await update.message.reply_text("📝 Введите ID пользователя для ответа:")

async def pre_checkout_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.pre_checkout_query
    await query.answer(ok=True)

async def successful_payment_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    payment = update.message.successful_payment
    user = update.message.from_user

    conn = sqlite3.connect('payments.db')
    cursor = conn.cursor()
    cursor.execute('''
        INSERT INTO payments (user_id, username, first_name, charge_id, amount, product_name)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (user.id, user.username, user.first_name, payment.telegram_payment_charge_id,
          payment.total_amount, payment.invoice_payload))

    if payment.invoice_payload == "premium":
        cursor.execute('UPDATE users SET has_subscription = TRUE WHERE user_id = ?', (user.id,))

    conn.commit()
    conn.close()

    admin_msg = f"""💰 *НОВАЯ ОПЛАТА*

👤 Пользователь: {user.first_name} (@{user.username or 'нет'})
🆔 ID: {user.id}
📦 Товар: {PRODUCTS[payment.invoice_payload]['name']}
💎 Сумма: {payment.total_amount} звезд
🆔 Charge ID: {payment.telegram_payment_charge_id}
🕐 Время: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}"""

    await notify_admin(context, admin_msg)

    user_msg = f"""✅ *Оплата прошла успешно!*

📦 Товар: {PRODUCTS[payment.invoice_payload]['name']}
💎 Сумма: {payment.total_amount} звезд

Спасибо за покупку! 🎉"""

    await update.message.reply_text(user_msg, parse_mode='Markdown')

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    # Основные команды
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    
    # Новые команды для админа
    application.add_handler(CommandHandler("reply", reply_to_user))
    application.add_handler(CommandHandler("tell", tell_user))
    application.add_handler(CommandHandler("quick", quick_reply))
    
    # Обработчики callback
    application.add_handler(CallbackQueryHandler(button_handler, pattern="^(premium|videos|support|about|back_main|video_100|video_1000|video_10000)$"))
    application.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^(admin_stats|quick_broadcast|notifications_on|notifications_off|all_users|back_admin)$"))
    
    # Обработчики сообщений
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_text_messages))
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))

    application.run_polling()

if __name__ == "__main__":
    main()
