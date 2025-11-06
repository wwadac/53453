import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery
from aiogram.utils import executor
from aiogram.utils.exceptions import MessageNotModified, BadRequest

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота
API_TOKEN = "8399893836:AAEdFVXohBkdM-jOkGf2ngaZ67_s65vQQNA"
ADMIN_ID = 8000395560  # Замените на ваш ID в Telegram

# Инициализация бота и диспетчера
bot = Bot(token=API_TOKEN)
dp = Dispatcher(bot)

# Словарь для хранения вопросов от пользователей (user_id: question)
user_questions = {}
# Словарь для отслеживания состояния пользователей
user_states = {}

# Основное меню
def get_main_menu():
    keyboard = InlineKeyboardMarkup(row_width=2)
    buttons = [
        InlineKeyboardButton("💎 Подписка", callback_data="subscription"),
        InlineKeyboardButton("🛠 Тех поддержка", callback_data="support"),
        InlineKeyboardButton("❓ Что это такое", callback_data="about")
    ]
    keyboard.add(*buttons)
    return keyboard

# Меню подписки
def get_subscription_menu():
    keyboard = InlineKeyboardMarkup(row_width=1)
    buttons = [
        InlineKeyboardButton("10 видео - 5 звезд", callback_data="sub_5"),
        InlineKeyboardButton("100 видео - 15 звезд", callback_data="sub_15"),
        InlineKeyboardButton("1000 видео - 50 звезд", callback_data="sub_50"),
        InlineKeyboardButton("TGK - 100 звезд", callback_data="sub_100"),
        InlineKeyboardButton("Промокод - 89 звезд", callback_data="promo_89"),
        InlineKeyboardButton("◀️ Назад", callback_data="back_main")
    ]
    keyboard.add(*buttons)
    return keyboard

# Меню тех поддержки
def get_support_menu():
    keyboard = InlineKeyboardMarkup()
    keyboard.add(InlineKeyboardButton("◀️ Назад", callback_data="back_main"))
    return keyboard

# Безопасное редактирование сообщения
async def safe_edit_message(callback_query: CallbackQuery, text: str, reply_markup: InlineKeyboardMarkup = None):
    try:
        await callback_query.message.edit_text(text, reply_markup=reply_markup)
    except MessageNotModified:
        # Игнорируем ошибку, если сообщение не изменилось
        await callback_query.answer()
    except BadRequest as e:
        logger.error(f"Error editing message: {e}")
        await callback_query.answer("Произошла ошибка. Попробуйте снова.", show_alert=True)

# Обработчик команды /start
@dp.message_handler(commands=['start'])
async def cmd_start(message: types.Message):
    welcome_text = "Добро пожаловать! Выберите опцию:"
    user_states[message.from_user.id] = 'main'
    await message.answer(welcome_text, reply_markup=get_main_menu())

# Обработчик инлайн кнопок
@dp.callback_query_handler(lambda c: c.data in ['subscription', 'support', 'about', 'back_main'])
async def process_callback(callback_query: CallbackQuery):
    user_id = callback_query.from_user.id
    
    if callback_query.data == 'subscription':
        user_states[user_id] = 'subscription'
        await safe_edit_message(
            callback_query,
            "💎 Выберите тип подписки:",
            get_subscription_menu()
        )
    
    elif callback_query.data == 'support':
        user_states[user_id] = 'support'
        support_text = "🛠 Напишите свой вопрос, и я отправлю его администратору бота!"
        await safe_edit_message(
            callback_query,
            support_text,
            get_support_menu()
        )
    
    elif callback_query.data == 'about':
        user_states[user_id] = 'about'
        about_text = (
            "🤖 **Что это такое?**\n\n"
            "Это бот для доступа к эксклюзивному видео-контенту! "
            "Вы можете приобрести подписку на различное количество видео "
            "за звезды Telegram. Выбирайте подходящий тариф и наслаждайтесь контентом!\n\n"
            "⭐ **Звезды** - это внутренняя валюта Telegram для покупок"
        )
        await safe_edit_message(
            callback_query,
            about_text,
            get_support_menu()
        )
    
    elif callback_query.data == 'back_main':
        user_states[user_id] = 'main'
        await safe_edit_message(
            callback_query,
            "Добро пожаловать! Выберите опцию:",
            get_main_menu()
        )

# Обработчик выбора подписки
@dp.callback_query_handler(lambda c: c.data.startswith('sub_') or c.data.startswith('promo_'))
async def process_subscription(callback_query: CallbackQuery):
    await callback_query.answer()
    
    subscription_data = {
        'sub_5': {'amount': 5, 'text': '10 видео - 5 звезд'},
        'sub_15': {'amount': 15, 'text': '100 видео - 15 звезд'},
        'sub_50': {'amount': 50, 'text': '1000 видео - 50 звезд'},
        'sub_100': {'amount': 100, 'text': 'TGK - 100 звезд'},
        'promo_89': {'amount': 89, 'text': 'Промокод - 89 звезд'}
    }
    
    sub_type = callback_query.data
    if sub_type in subscription_data:
        amount = subscription_data[sub_type]['amount']
        text = subscription_data[sub_type]['text']
        
        # Создаем инвойс для оплаты
        prices = [types.LabeledPrice(label=text, amount=amount * 100)]  # amount в копейках
        
        try:
            await bot.send_invoice(
                chat_id=callback_query.from_user.id,
                title=f"Оплата: {text}",
                description=f"Оплата {amount} звезд за подписку",
                provider_token="",  # Замените на ваш токен платежного провайдера
                currency="XTR",
                prices=prices,
                payload=f"subscription_{sub_type}_{callback_query.from_user.id}"
            )
        except Exception as e:
            logger.error(f"Error creating invoice: {e}")
            await bot.send_message(
                chat_id=callback_query.from_user.id,
                text="Произошла ошибка при создании счета. Попробуйте позже."
            )

# Обработчик успешной оплаты
@dp.pre_checkout_query_handler()
async def process_pre_checkout_query(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message_handler(content_types=types.ContentType.SUCCESSFUL_PAYMENT)
async def process_successful_payment(message: types.Message):
    payment_info = message.successful_payment
    user_id = message.from_user.id
    
    # Отправляем уведомление админу
    admin_text = (
        f"💰 Новое пополнение!\n"
        f"👤 Пользователь: @{message.from_user.username or 'Нет username'}\n"
        f"🆔 ID: {user_id}\n"
        f"💎 Сумма: {payment_info.total_amount / 100} звезд\n"
        f"💳 Валюта: {payment_info.currency}"
    )
    
    try:
        await bot.send_message(ADMIN_ID, admin_text)
    except Exception as e:
        logger.error(f"Не удалось отправить уведомление админу: {e}")
    
    # Имитируем ошибку для пользователя
    error_text = "❌ Произошла ошибка: мы не смогли найти ваш аккаунт. Пожалуйста, оплатите еще раз!"
    await message.answer(error_text)

# Обработчик сообщений для тех поддержки
@dp.message_handler(content_types=types.ContentType.TEXT)
async def handle_text_messages(message: types.Message):
    user_id = message.from_user.id
    
    # Проверяем, находится ли пользователь в режиме техподдержки
    if user_states.get(user_id) == 'support' and message.text:
        question = message.text
        
        # Отправляем вопрос админу
        admin_question_text = (
            f"❓ Новый вопрос от пользователя:\n"
            f"👤 @{message.from_user.username or 'Нет username'}\n"
            f"🆔 ID: {user_id}\n"
            f"💬 Вопрос: {question}"
        )
        
        # Клавиатура для админа
        admin_keyboard = InlineKeyboardMarkup()
        admin_keyboard.add(
            InlineKeyboardButton("🔇 Замутить", callback_data=f"mute_{user_id}"),
            InlineKeyboardButton("🚫 Забанить", callback_data=f"ban_{user_id}")
        )
        
        try:
            await bot.send_message(ADMIN_ID, admin_question_text, reply_markup=admin_keyboard)
            await message.answer("✅ Ваш вопрос отправлен администратору! Ожидайте ответа.")
        except Exception as e:
            logger.error(f"Error sending question to admin: {e}")
            await message.answer("❌ Не удалось отправить вопрос. Попробуйте позже.")
        
        # Возвращаем в главное меню
        user_states[user_id] = 'main'
        await message.answer("Выберите опцию:", reply_markup=get_main_menu())
    
    elif message.text and not message.text.startswith('/'):
        # Если это обычное текстовое сообщение, показываем главное меню
        user_states[user_id] = 'main'
        await message.answer("Выберите опцию:", reply_markup=get_main_menu())

# Обработчик действий админа (мут/бан)
@dp.callback_query_handler(lambda c: c.data.startswith('mute_') or c.data.startswith('ban_'))
async def process_admin_actions(callback_query: CallbackQuery):
    await callback_query.answer()
    
    if str(callback_query.from_user.id) != str(ADMIN_ID):
        await callback_query.answer("У вас нет прав для этого действия!", show_alert=True)
        return
    
    action, user_id = callback_query.data.split('_')
    user_id = int(user_id)
    
    if action == 'mute':
        # Здесь логика мута пользователя
        await bot.send_message(
            ADMIN_ID,
            f"Пользователь {user_id} был замьючен"
        )
        await callback_query.answer("Пользователь замьючен!")
    
    elif action == 'ban':
        # Здесь логика бана пользователя
        await bot.send_message(
            ADMIN_ID,
            f"Пользователь {user_id} был забанен"
        )
        await callback_query.answer("Пользователь забанен!")

# Обработчик ошибок
@dp.errors_handler()
async def errors_handler(update, exception):
    logger.error(f"Update {update} caused error {exception}")
    return True

if __name__ == '__main__':
    # Убедитесь, что только один экземпляр бота запущен
    try:
        executor.start_polling(dp, skip_updates=True, relax=0.1)
    except Exception as e:
        logger.error(f"Bot crashed: {e}")
