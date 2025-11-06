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
    # Настройки по умолчанию
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
        await context.bot.send_message(ADMIN_ID, message)
    except:
        pass

async def notify_new_user(user):
    """Уведомление о новом пользователе"""
    if get_admin_setting("new_users_notifications") == "on":
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        message = f"""🆕 *НОВЫЙ ПОЛЬЗОВАТЕЛЬ*

👤 Имя: {user.first_name}
📛 Ник: @{user.username}
🆔 ID: `{user.id}`
🕐 Время: {current_time}"""
        
        try:
            from telegram.ext import ApplicationBuilder
            app = ApplicationBuilder().token(BOT_TOKEN).build()
            await app.bot.send_message(ADMIN_ID, message, parse_mode='Markdown')
        except:
            pass

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.message.from_user
    conn = sqlite3.connect('payments.db')
    cursor = conn.cursor()
    
    # Проверяем новый ли пользователь
    cursor.execute('SELECT * FROM users WHERE user_id = ?', (user.id,))
    existing_user = cursor.fetchone()
    
    cursor.execute('INSERT OR IGNORE INTO users (user_id, username, first_name) VALUES (?, ?, ?)',
                   (user.id, user.username, user.first_name))
    conn.commit()
    conn.close()
    
    # Уведомляем админа о новом пользователе
    if not existing_user:
        await notify_new_user(user)

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

# Админские инлайн кнопки
async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data="admin_stats")],
        [InlineKeyboardButton("📢 Быстрая рассылка", callback_data="quick_broadcast")],
        [InlineKeyboardButton("🔔 Уведомления ВКЛ", callback_data="notifications_off"), 
         InlineKeyboardButton("🔕 Уведомления ВЫКЛ", callback_data="notifications_on")],
        [InlineKeyboardButton("👥 Последние пользователи", callback_data="recent_users")],
        [InlineKeyboardButton("💰 Последние платежи", callback_data="recent_payments")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)

    text = """👑 *Панель администратора*

Выберите действие:"""
    await update.message.reply_text(text, reply_markup=reply_markup, parse_mode='Markdown')

async def admin_button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
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

        await query.edit_message_text(text, parse_mode='Markdown')

    elif query.data == "quick_broadcast":
        context.user_data['awaiting_broadcast'] = True
        await query.edit_message_text("📢 *Быстрая рассылка*\n\nВведите сообщение для рассылки:")

    elif query.data == "notifications_on":
        set_admin_setting("new_users_notifications", "on")
        await query.edit_message_text("✅ Уведомления о новых пользователях ВКЛЮЧЕНЫ")

    elif query.data == "notifications_off":
        set_admin_setting("new_users_notifications", "off")
        await query.edit_message_text("✅ Уведомления о новых пользователях ВЫКЛЮЧЕНЫ")

    elif query.data == "recent_users":
        conn = sqlite3.connect('payments.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, username, first_name, join_date FROM users ORDER BY join_date DESC LIMIT 10')
        users = cursor.fetchall()
        conn.close()

        if not users:
            await query.edit_message_text("📭 Пользователей нет")
            return

        text = "👥 *Последние 10 пользователей:*\n\n"
        for user in users:
            user_id, username, first_name, join_date = user
            text += f"👤 {first_name} (@{username})\n🆔 {user_id}\n🕐 {join_date}\n\n"

        await query.edit_message_text(text)

    elif query.data == "recent_payments":
        conn = sqlite3.connect('payments.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, amount, product_name, timestamp FROM payments ORDER BY timestamp DESC LIMIT 10')
        payments = cursor.fetchall()
        conn.close()

        if not payments:
            await query.edit_message_text("📭 Платежей нет")
            return

        text = "💰 *Последние 10 платежей:*\n\n"
        for payment in payments:
            user_id, amount, product_name, timestamp = payment
            text += f"👤 {user_id}\n💎 {amount} звезд\n📦 {product_name}\n🕐 {timestamp}\n\n"

        await query.edit_message_text(text)

# Обработчик текстовых сообщений для техподдержки
async def handle_support_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if context.user_data.get('awaiting_support'):
        user = update.message.from_user
        question = update.message.text

        admin_msg = f"""💬 *НОВЫЙ ВОПРОС В ТЕХПОДДЕРЖКУ*

👤 Пользователь: {user.first_name} (@{user.username})
🆔 ID: {user.id}
🕐 Время: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}

❓ Вопрос:
{question}"""

        await notify_admin(context, admin_msg)
        await update.message.reply_text("✅ Ваш вопрос отправлен администратору. Ожидайте ответа в ближайшее время!")
        context.user_data.pop('awaiting_support', None)

    elif context.user_data.get('awaiting_broadcast') and update.message.from_user.id == ADMIN_ID:
        message = update.message.text
        conn = sqlite3.connect('payments.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id FROM users WHERE is_banned = FALSE')
        users = cursor.fetchall()
        conn.close()

        sent = 0
        for user in users:
            try:
                await context.bot.send_message(user[0], f"📢 *Рассылка:*\n\n{message}", parse_mode='Markdown')
                sent += 1
            except:
                continue

        context.user_data.pop('awaiting_broadcast', None)
        await update.message.reply_text(f"✅ Сообщение отправлено {sent} пользователям")

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

👤 Пользователь: {user.first_name} (@{user.username})
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

# Существующие админ команды (оставлены для обратной совместимости)
async def admin_stats(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

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

    conn.close()

    text = f"""👑 *Статистика админа*

👥 Всего пользователей: {total_users}
💎 Премиум пользователей: {premium_users}
💰 Всего платежей: {total_payments}
⭐ Всего звезд: {total_stars}"""

    await update.message.reply_text(text, parse_mode='Markdown')

async def ban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("❌ Используй: /ban <user_id>")
        return

    try:
        user_id = int(context.args[0])
        conn = sqlite3.connect('payments.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_banned = TRUE WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()

        await update.message.reply_text(f"✅ Пользователь {user_id} забанен")
    except:
        await update.message.reply_text("❌ Ошибка")

async def unban_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("❌ Используй: /unban <user_id>")
        return

    try:
        user_id = int(context.args[0])
        conn = sqlite3.connect('payments.db')
        cursor = conn.cursor()
        cursor.execute('UPDATE users SET is_banned = FALSE WHERE user_id = ?', (user_id,))
        conn.commit()
        conn.close()

        await update.message.reply_text(f"✅ Пользователь {user_id} разбанен")
    except:
        await update.message.reply_text("❌ Ошибка")

async def broadcast(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    if not context.args:
        await update.message.reply_text("❌ Используй: /broadcast <сообщение>")
        return

    message = ' '.join(context.args)
    conn = sqlite3.connect('payments.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id FROM users WHERE is_banned = FALSE')
    users = cursor.fetchall()
    conn.close()

    sent = 0
    for user in users:
        try:
            await context.bot.send_message(user[0], f"📢 Рассылка:\n\n{message}")
            sent += 1
        except:
            continue

    await update.message.reply_text(f"✅ Сообщение отправлено {sent} пользователям")

async def reply_user(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    if len(context.args) < 2:
        await update.message.reply_text("❌ Используй: /reply <user_id> <сообщение>")
        return

    try:
        user_id = int(context.args[0])
        message = ' '.join(context.args[1:])

        await context.bot.send_message(user_id, f"💬 Ответ от администратора:\n\n{message}")
        await update.message.reply_text(f"✅ Ответ отправлен пользователю {user_id}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def refund(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    if len(context.args) < 2:
        await update.message.reply_text("❌ Используй: /refund <charge_id> <amount>")
        return

    try:
        charge_id = context.args[0]
        amount = int(context.args[1])

        conn = sqlite3.connect('payments.db')
        cursor = conn.cursor()
        cursor.execute('SELECT user_id, amount FROM payments WHERE charge_id = ?', (charge_id,))
        payment = cursor.fetchone()
        conn.close()

        if not payment:
            await update.message.reply_text("❌ Платеж не найден")
            return

        user_id, paid_amount = payment
        if amount > paid_amount:
            await update.message.reply_text(f"❌ Нельзя вернуть больше {paid_amount} звезд")
            return

        result = await context.bot.refund_star_payment(
            user_id=user_id,
            telegram_payment_charge_id=charge_id,
            star_count=amount
        )

        await update.message.reply_text(f"✅ Возвращено {amount} звезд пользователю {user_id}")
    except Exception as e:
        await update.message.reply_text(f"❌ Ошибка: {e}")

async def show_payments(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message.from_user.id != ADMIN_ID:
        return

    conn = sqlite3.connect('payments.db')
    cursor = conn.cursor()
    cursor.execute('SELECT user_id, charge_id, amount, product_name, timestamp FROM payments ORDER BY id DESC LIMIT 10')
    payments = cursor.fetchall()
    conn.close()

    if not payments:
        await update.message.reply_text("📭 Платежей нет")
        return

    text = "📊 Последние платежи:\n\n"
    for payment in payments:
        user_id, charge_id, amount, product_name, timestamp = payment
        text += f"👤 {user_id}\n💰 {amount} звезд ({product_name})\n🆔 {charge_id}\n🕐 {timestamp}\n\n"

    await update.message.reply_text(text)

def main():
    application = Application.builder().token(BOT_TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    application.add_handler(CommandHandler("stats", admin_stats))
    application.add_handler(CommandHandler("ban", ban_user))
    application.add_handler(CommandHandler("unban", unban_user))
    application.add_handler(CommandHandler("broadcast", broadcast))
    application.add_handler(CommandHandler("reply", reply_user))
    application.add_handler(CommandHandler("refund", refund))
    application.add_handler(CommandHandler("payments", show_payments))
    application.add_handler(CallbackQueryHandler(button_handler))
    application.add_handler(CallbackQueryHandler(admin_button_handler, pattern="^admin_"))
    application.add_handler(PreCheckoutQueryHandler(pre_checkout_handler))
    application.add_handler(MessageHandler(filters.SUCCESSFUL_PAYMENT, successful_payment_handler))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_support_message))

    application.run_polling()

if __name__ == "__main__":
    main()
