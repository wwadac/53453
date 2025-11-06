import asyncio
from aiogram import Bot, Dispatcher, types, F
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton, Message, CallbackQuery
from aiogram.filters import Command
from aiogram.enums import ParseMode
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
import logging

# 🔐 Конфигурация
BOT_TOKEN = "8399893836:AAEdFVXohBkdM-jOkGf2ngaZ67_s65vQQNA"
ADMIN_ID = 8000395560  # Замените на ваш ID в Telegram

# 📝 Логирование
logging.basicConfig(level=logging.INFO)

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# 🎯 Состояния FSM для техподдержки
class SupportStates(StatesGroup):
    waiting_for_question = State()

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
async def back_to_main(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text("Главное меню:", reply_markup=get_main_menu())

# 📱 Команда /start
@dp.message(Command("start"))
async def cmd_start(message: Message, state: FSMContext):
    await state.clear()
    if message.from_user.id in banned_users:
        await message.answer("Вы забанены.")
        return
    await message.answer("Добро пожаловать!", reply_markup=get_main_menu())

# 📌 Главное меню: обработка кнопок
@dp.callback_query(F.data == "subscribe")
async def show_subscribe(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(
        "Выберите тариф:\n\n"
        "С промокодом «VIP» — скидка 11%! (50 → 45 ⭐)\n"
        "Но пока доступна только полная цена.",
        reply_markup=get_subscribe_menu()
    )

@dp.callback_query(F.data == "support")
async def support(callback: CallbackQuery, state: FSMContext):
    await state.set_state(SupportStates.waiting_for_question)
    await callback.message.edit_text(
        "Напишите свой вопрос — я передам его администратору бота!"
    )

@dp.callback_query(F.data == "about")
async def about(callback: CallbackQuery, state: FSMContext):
    await state.clear()
    await callback.message.edit_text(ABOUT_TEXT, reply_markup=get_main_menu())

# 💬 Обработка вопросов в техподдержку
@dp.message(SupportStates.waiting_for_question)
async def handle_support_message(message: Message, state: FSMContext):
    if message.from_user.id in banned_users:
        await message.answer("Вы забанены.")
        await state.clear()
        return

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
        await message.answer("✅ Ваш вопрос отправлен администратору!", reply_markup=get_main_menu())
    except Exception as e:
        logging.error(f"Не удалось отправить вопрос админу: {e}")
        await message.answer("❌ Ошибка при отправке. Попробуйте позже.", reply_markup=get_main_menu())
    
    await state.clear()

# 💎 Создание инвойса для реальной оплаты Stars
def create_invoice(plan: str) -> types.Invoice:
    plans = {
        "10": {"title": "10 эксклюзивных видео", "description": "Доступ к 10 эксклюзивным видео", "price": 500, "payload": "pay_10"},
        "100": {"title": "100 эксклюзивных видео", "description": "Доступ к 100 эксклюзивным видео", "price": 1500, "payload": "pay_100"},
        "1000": {"title": "1000 эксклюзивных видео", "description": "Доступ к 1000 эксклюзивным видео", "price": 5000, "payload": "pay_1000"}
    }
    
    plan_data = plans.get(plan, plans["10"])
    
    return types.Invoice(
        title=plan_data["title"],
        description=plan_data["description"],
        currency="XTR",  # Telegram Stars
        prices=[types.LabeledPrice(label=plan_data["title"], amount=plan_data["price"])],
        payload=plan_data["payload"],
        provider_token="",  # Для Stars не нужен provider_token
        start_parameter=f"subscription_{plan}"
    )

# 💎 Обработка выбора тарифа - создание инвойса
@dp.callback_query(F.data.startswith("pay_"))
async def process_payment_selection(callback: CallbackQuery):
    user_id = callback.from_user.id
    if user_id in banned_users:
        await callback.answer("Вы забанены.", show_alert=True)
        return

    plan = callback.data.split("_")[1]
    invoice = create_invoice(plan)
    
    try:
        await bot.send_invoice(
            chat_id=callback.message.chat.id,
            title=invoice.title,
            description=invoice.description,
            payload=invoice.payload,
            provider_token=invoice.provider_token,
            currency=invoice.currency,
            prices=invoice.prices,
            start_parameter=invoice.start_parameter,
            need_email=False,
            need_phone_number=False,
            need_shipping_address=False,
            is_flexible=False
        )
    except Exception as e:
        logging.error(f"Ошибка при создании инвойса: {e}")
        await callback.answer("❌ Ошибка при создании платежа", show_alert=True)

# 💰 Обработка успешной оплаты
@dp.pre_checkout_query()
async def process_pre_checkout(pre_checkout_query: types.PreCheckoutQuery):
    await bot.answer_pre_checkout_query(pre_checkout_query.id, ok=True)

@dp.message(F.successful_payment)
async def process_successful_payment(message: Message):
    user_id = message.from_user.id
    plan = message.successful_payment.invoice_payload
    
    # Уведомление админу об успешной оплате
    await bot.send_message(
        ADMIN_ID,
        f"✅ Успешная оплата от @{message.from_user.username or f'id{user_id}'}\n"
        f"Тариф: {plan}\n"
        f"Сумма: {message.successful_payment.total_amount / 100} ⭐\n"
        f"ID пользователя: {user_id}"
    )
    
    # ❌ Имитируем ошибку ПОСЛЕ успешной оплаты
    await message.answer(
        "❌ Произошла ошибка!\n"
        "Мы не смогли найти ваш аккаунт в системе.\n"
        "Пожалуйста, обратитесь в техподдержку для решения проблемы.\n\n"
        f"Ваш платеж на {message.successful_payment.total_amount / 100} ⭐ получен, но доступ не активирован.",
        reply_markup=get_main_menu()
    )

# 🔒 Админка: бан/разбан
@dp.callback_query(F.data.startswith("ban_"))
async def ban_user(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    
    target_id = int(callback.data.split("_")[1])
    if target_id in banned_users:
        banned_users.remove(target_id)
        await callback.answer("Пользователь разбанен!", show_alert=True)
        try:
            await bot.send_message(target_id, "✅ Вы разблокированы администратором!")
        except:
            pass
    else:
        banned_users.add(target_id)
        await callback.answer("Пользователь забанен!", show_alert=True)
        try:
            await bot.send_message(target_id, "❌ Вы заблокированы администратором.")
        except:
            pass
    
    # Обновляем сообщение админу
    await callback.message.edit_reply_markup(reply_markup=InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="Разбанить" if target_id in banned_users else "Забанить", 
                            callback_data=f"ban_{target_id}")],
        [InlineKeyboardButton(text="Ответить", callback_data=f"reply_{target_id}")]
    ]))

# 📬 Ответ админа пользователю (заглушка)
@dp.callback_query(F.data.startswith("reply_"))
async def reply_to_user(callback: CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        await callback.answer("Доступ запрещен", show_alert=True)
        return
    
    target_id = int(callback.data.split("_")[1])
    await callback.answer(f"Для ответа пользователю {target_id} используйте команду /reply", show_alert=True)

# 📋 Команда для админа - список забаненных
@dp.message(Command("banned"))
async def list_banned(message: Message):
    if message.from_user.id == ADMIN_ID:
        if banned_users:
            banned_list = "\n".join([f"ID: {user_id}" for user_id in banned_users])
            await message.answer(f"Забаненные пользователи:\n{banned_list}")
        else:
            await message.answer("Нет забаненных пользователей.")

# 🔄 Обработка любых сообщений (кроме состояний)
@dp.message()
async def handle_other_messages(message: Message, state: FSMContext):
    current_state = await state.get_state()
    if current_state is None:  # Если не в состоянии техподдержки
        if message.from_user.id in banned_users:
            await message.answer("Вы забанены.")
            return
        # Предлагаем главное меню для любых других сообщений
        await message.answer("Используйте кнопки меню для навигации:", reply_markup=get_main_menu())

# 🚀 Запуск
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
