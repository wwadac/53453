import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from aiogram.filters import Command
from aiogram.enums import ParseMode
import logging

# 🔐 Конфигурация
BOT_TOKEN = "8399893836:AAEdFVXohBkdM-jOkGf2ngaZ67_s65vQQNA"
ADMIN_ID = 8000395560  # Замените на ваш ID в Telegram


# 📝 Логирование
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 💬 Статичный текст "Что это такое"
ABOUT_TEXT = (
    "Это бот для получения доступа к эксклюзивным видео.\n"
    "Оплатите подписку звёздами 💎 и получите доступ к контенту!\n"
    "Все платежи защищены через Telegram Stars."
)

# 📦 Пользовательские данные (в реальном проекте — база данных)
banned_users = set()
user_questions = {}  # user_id -> last_question

# 🏠 Главное меню
def get_main_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="💳 Подписка", callback_data="subscribe")],
        [InlineKeyboardButton(text="🛠 Техподдержка", callback_data="support")],
        [InlineKeyboardButton(text="ℹ️ Что это такое", callback_data="about")]
    ])
    return kb

# 💳 Меню подписок
def get_subscribe_menu() -> InlineKeyboardMarkup:
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="10 видео — 5 ⭐", callback_data="pay_10")],
        [InlineKeyboardButton(text="100 видео — 15 ⭐", callback_data="pay_100")],
        [InlineKeyboardButton(text="1000 видео — 50 ⭐", callback_data="pay_1000")],
        [InlineKeyboardButton(text="Назад", callback_data="back_to_main")]
    ])
    return kb

# 🔄 Обратно в главное меню
@dp.callback_query(F.data == "back_to_main")
async def back_to_main(callback: CallbackQuery):
    await callback.message.edit_text("Главное меню:", reply_markup=get_main_menu())

# 📱 Команда /start
@dp.message(Command("start"))
async def cmd_start(message: Message):
    if message.from_user.id in banned_users:
        await message.answer("Вы забанены.")
        return
    await message.answer("Добро пожаловать!", reply_markup=get_main_menu())

# 📌 Главное меню: обработка кнопок
@dp.callback_query(F.data == "subscribe")
async def show_subscribe(callback: CallbackQuery):
    await callback.message.edit_text(
        "Выберите тариф:\n\n"
        "С промокодом «VIP» — скидка 11%! (50 → 45 ⭐)\n"
        "Но пока доступна только полная цена.",
        reply_markup=get_subscribe_menu()
    )

@dp.callback_query(F.data == "support")
async def support(callback: CallbackQuery):
    await callback.message.edit_text(
        "Напишите свой вопрос — я передам его администратору бота!"
    )
    # Сохраняем состояние (упрощённо — без FSM)
    user_questions[callback.from_user.id] = True

@dp.callback_query(F.data == "about")
async def about(callback: CallbackQuery):
    await callback.message.edit_text(ABOUT_TEXT, reply_markup=get_main_menu())

# 💬 Обработка вопросов в техподдержку
@dp.message()
async def handle_support_message(message: Message):
    if message.from_user.id in banned_users:
        await message.answer("Вы забанены.")
        return

    if message.from_user.id in user_questions:
        del user_questions[message.from_user.id]  # сбрасываем состояние
        question = message.text
        user_id = message.from_user.id
        username = message.from_user.username or f"id{user_id}"

        try:
            await bot.send_message(
                ADMIN_ID,
                f"📩 Новое сообщение от @{username} (ID: {user_id}):\n\n{question}",
                reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                    [InlineKeyboardButton(text="Забанить", callback_data=f"ban_{user_id}")],
                    [InlineKeyboardButton(text="Ответить", callback_data=f"reply_{user_id}")]
                ])
            )
            await message.answer("Ваш вопрос отправлен администратору!")
        except Exception as e:
            logging.error(f"Не удалось отправить вопрос админу: {e}")
            await message.answer("Ошибка при отправке. Попробуйте позже.")
    else:
        # Игнорируем прочие сообщения
        pass

# 💎 Обработка оплаты (имитация)
@dp.callback_query(F.data.startswith("pay_"))
async def process_payment(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id in banned_users:
        await callback.answer("Вы забанены.", show_alert=True)
        return

    # Уведомление админу
    plan = callback.data.split("_")[1]
    await bot.send_message(
        ADMIN_ID,
        f"🔔 Попытка оплаты от @{callback.from_user.username or f'id{user_id}'}\n"
        f"Тариф: {plan} видео\n"
        f"ID пользователя: {user_id}"
    )

    # ❌ Имитируем ошибку
    await callback.message.edit_text(
        "❌ Произошла ошибка!\n"
        "Мы не смогли найти ваш аккаунт в системе.\n"
        "Пожалуйста, оплатите ещё раз.",
        reply_markup=get_subscribe_menu()
    )

# 🔒 Админка: бан/разбан
@dp.callback_query(F.data.startswith("ban_"))
async def ban_user(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    target_id = int(callback.data.split("_")[1])
    if target_id in banned_users:
        banned_users.remove(target_id)
        await callback.answer("Пользователь разбанен!", show_alert=True)
        await bot.send_message(target_id, "Вы разблокированы!")
    else:
        banned_users.add(target_id)
        await callback.answer("Пользователь забанен!", show_alert=True)
        await bot.send_message(target_id, "Вы заблокированы администратором.")

# 📬 (Опционально) отладка: список забаненных
@dp.message(Command("banned"))
async def list_banned(message: Message):
    if message.from_user.id == ADMIN_ID:
        if banned_users:
            await message.answer(f"Забаненные: {banned_users}")
        else:
            await message.answer("Нет забаненных.")

# 🚀 Запуск
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
