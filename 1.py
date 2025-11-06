import asyncio
import logging
from aiogram import Bot, Dispatcher, types
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram import F

# Настройка логирования
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Токен бота и ID админа
BOT_TOKEN = "8399893836:AAEdFVXohBkdM-jOkGf2ngaZ67_s65vQQNA"
ADMIN_ID = 8000395560  # Замените на ваш ID в Telegram


bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Хранилище для вопросов пользователей
user_questions = {}

# Главное меню
def get_main_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🌟 Подписка", callback_data="subscription")],
        [InlineKeyboardButton(text="🛠 Тех поддержка", callback_data="support")],
        [InlineKeyboardButton(text="❓ Что это такое", callback_data="what_is_this")]
    ])
    return keyboard

# Меню подписки
def get_subscription_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="10 видео - 5 звезд", callback_data="sub_10")],
        [InlineKeyboardButton(text="100 видео - 15 звезд", callback_data="sub_100")],
        [InlineKeyboardButton(text="1000 видео - 50 звезд", callback_data="sub_1000")],
        [InlineKeyboardButton(text="Telegram Premium - 100 звезд", callback_data="sub_tg")],
        [InlineKeyboardButton(text="Промокод - 89 звезд", callback_data="promo_code")],
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    return keyboard

# Меню поддержки
def get_support_menu():
    keyboard = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
    ])
    return keyboard

# Команда /start
@dp.message(Command("start"))
async def cmd_start(message: types.Message):
    await message.answer(
        "🎉 Добро пожаловать в наш бот!\n\n"
        "Здесь вы можете получить доступ к эксклюзивному контенту. "
        "Выберите нужный раздел ниже:",
        reply_markup=get_main_menu()
    )

# Обработка callback запросов
@dp.callback_query(F.data == "subscription")
async def subscription_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "💰 Выберите тип подписки:\n\n"
        "• 10 видео - 5 звезд\n"
        "• 100 видео - 15 звезд\n"
        "• 1000 видео - 50 звезд\n"
        "• Telegram Premium - 100 звезд\n"
        "• Промокод - 89 звезд",
        reply_markup=get_subscription_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "support")
async def support_handler(callback: types.CallbackQuery):
    user_id = callback.from_user.id
    user_questions[user_id] = {"waiting_for_question": True}
    
    await callback.message.edit_text(
        "🛠 Техническая поддержка\n\n"
        "Напишите ваш вопрос, и я отправлю его администратору бота. "
        "Мы постараемся ответить как можно скорее!",
        reply_markup=get_support_menu()
    )
    await callback.answer()

@dp.callback_query(F.data == "what_is_this")
async def what_is_this_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🤖 О нашем боте:\n\n"
        "Это инновационный бот для доступа к эксклюзивному видео-контенту! "
        "Мы предлагаем различные варианты подписок по доступным ценам.\n\n"
        "🌟 Особенности:\n"
        "• Качественный контент\n"
        "• Доступные цены\n"
        "• Мгновенный доступ\n"
        "• Техническая поддержка 24/7\n\n"
        "Выберите подписку и наслаждайтесь контентом!",
        reply_markup=get_main_menu()
    )
    await callback.answer()

@dp.callback_query(F.data.startswith("sub_"))
async def subscription_payment_handler(callback: types.CallbackQuery):
    subscription_type = callback.data
    prices = {
        "sub_10": "5 звезд",
        "sub_100": "15 звезд", 
        "sub_1000": "50 звезд",
        "sub_tg": "100 звезд",
        "promo_code": "89 звезд"
    }
    
    price = prices.get(subscription_type, "неизвестно")
    
    # Симуляция ошибки оплаты (как в ТЗ)
    await callback.message.edit_text(
        f"❌ Произошла ошибка!\n\n"
        f"Мы не смогли найти ваш аккаунт. Пожалуйста, попробуйте оплатить еще раз.\n\n"
        f"Выбранный тариф: {subscription_type.replace('sub_', '').replace('_', ' ').title()} - {price}",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Попробовать снова", callback_data="subscription")],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="back_to_main")]
        ])
    )
    
    # Уведомление админу о попытке оплаты
    try:
        await bot.send_message(
            ADMIN_ID,
            f"💰 Попытка оплаты!\n\n"
            f"Пользователь: @{callback.from_user.username or 'без username'}\n"
            f"ID: {callback.from_user.id}\n"
            f"Тариф: {subscription_type}\n"
            f"Сумма: {price}\n"
            f"Статус: Ошибка - аккаунт не найден"
        )
    except Exception as e:
        logger.error(f"Ошибка отправки уведомления админу: {e}")
    
    await callback.answer()

@dp.callback_query(F.data == "back_to_main")
async def back_to_main_handler(callback: types.CallbackQuery):
    await callback.message.edit_text(
        "🎉 Добро пожаловать в наш бот!\n\n"
        "Здесь вы можете получить доступ к эксклюзивному контенту. "
        "Выберите нужный раздел ниже:",
        reply_markup=get_main_menu()
    )
    await callback.answer()

# Обработка вопросов для техподдержки
@dp.message(F.text)
async def handle_support_question(message: types.Message):
    user_id = message.from_user.id
    
    if user_id in user_questions and user_questions[user_id].get("waiting_for_question"):
        question = message.text
        
        # Отправляем вопрос админу
        try:
            await bot.send_message(
                ADMIN_ID,
                f"❓ Новый вопрос от пользователя:\n\n"
                f"👤 Пользователь: @{message.from_user.username or 'без username'}\n"
                f"🆔 ID: {user_id}\n"
                f"💬 Вопрос: {question}\n\n"
                f"Действия:\n"
                f"/mute_{user_id} - Замутить\n"
                f"/ban_{user_id} - Забанить\n"
                f"/reply_{user_id} - Ответить"
            )
            
            await message.answer(
                "✅ Ваш вопрос отправлен администратору! Мы ответим вам в ближайшее время.",
                reply_markup=get_main_menu()
            )
            
        except Exception as e:
            await message.answer(
                "❌ Произошла ошибка при отправке вопроса. Попробуйте позже.",
                reply_markup=get_main_menu()
            )
            logger.error(f"Ошибка отправки вопроса админу: {e}")
        
        # Сбрасываем состояние ожидания вопроса
        user_questions[user_id]["waiting_for_question"] = False

# Команды для админа
@dp.message(Command("mute"))
async def mute_user(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        user_id = int(message.text.split()[1])
        await message.answer(f"Пользователь {user_id} замучен")
    except (IndexError, ValueError):
        await message.answer("Использование: /mute <user_id>")

@dp.message(Command("ban"))
async def ban_user(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        user_id = int(message.text.split()[1])
        await message.answer(f"Пользователь {user_id} забанен")
    except (IndexError, ValueError):
        await message.answer("Использование: /ban <user_id>")

@dp.message(Command("reply"))
async def reply_to_user(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    try:
        parts = message.text.split(maxsplit=2)
        user_id = int(parts[1])
        reply_text = parts[2]
        
        await bot.send_message(user_id, f"📨 Ответ от поддержки:\n\n{reply_text}")
        await message.answer("✅ Ответ отправлен пользователю")
        
    except (IndexError, ValueError):
        await message.answer("Использование: /reply <user_id> <текст>")
    except Exception as e:
        await message.answer(f"❌ Ошибка отправки: {e}")

# Запуск бота
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
