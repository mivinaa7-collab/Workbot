import asyncio
import uuid
import os

from aiogram import Bot, Dispatcher, F, Router, types
from aiogram.types import (
    InlineKeyboardMarkup,
    InlineKeyboardButton,
    InputMediaPhoto
)
from aiogram.client.default import DefaultBotProperties
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.context import FSMContext
from aiogram.fsm.storage.memory import MemoryStorage

# ================== CONFIG ==================

TOKEN = os.getenv("BOT_TOKEN")

if not TOKEN:
    raise Exception("❌ BOT_TOKEN не найден! Добавь его в Railway Variables.")

PHOTO_ID = "AgACAgIAAxkBAAEhGfxplRTG7SYAAYHIZHbtYSo8AwnLCocAAggRaxuvxKhIkQABFTv0MmKoAQADAgADeAADOgQ"

ADMIN_IDS = {8437167194}

ROLES = {
    "admin": "ADMIN",
    "worker": "WORKER"
}

def get_user_role(user_id: int) -> str:
    return ROLES["admin"] if user_id in ADMIN_IDS else ROLES["worker"]

def main_menu_caption(user: types.User) -> str:
    role = get_user_role(user.id)
    name = user.first_name or "Пользователь"
    username = f"@{user.username}" if user.username else ""

    return (
        f"👋 <b>Привет, {name} {username}</b>\n"
        f"🔑 Роль: <b>{role}</b>\n"
        f"⚡ Выберите действие ниже:"
    )

# ================== INIT ==================

bot = Bot(token=TOKEN, default=DefaultBotProperties(parse_mode="HTML"))
dp = Dispatcher(storage=MemoryStorage())
router = Router()

# ================== STORAGE ==================

applications = {}
approved_users = set()
user_links = {}

# ================== FSM ==================

class ApplyFSM(StatesGroup):
    source = State()
    experience = State()
    time = State()

class LinkFSM(StatesGroup):
    service = State()
    price = State()

# ================== KEYBOARDS ==================

def approve_kb(user_id: int):
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="✅ Принять", callback_data=f"approve:{user_id}"),
            InlineKeyboardButton(text="❌ Отклонить", callback_data=f"reject:{user_id}")
        ]
    ])

def main_menu():
    return InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="🔥 Создать ссылку", callback_data="create_link")],
        [InlineKeyboardButton(text="❤️ Мои объявления", callback_data="my_links")]
    ])

def services_kb():
    return InlineKeyboardMarkup(inline_keyboard=[
        [
            InlineKeyboardButton(text="📞 Viber", callback_data="srv:VIBER"),
            InlineKeyboardButton(text="🏦 Privat", callback_data="srv:PRIVAT")
        ],
        [
            InlineKeyboardButton(text="🏦 PUMB", callback_data="srv:PUMB"),
            InlineKeyboardButton(text="🏦 Oshad", callback_data="srv:OSHAD")
        ],
        [InlineKeyboardButton(text="🌐 Multi", callback_data="srv:MULTI")],
        [InlineKeyboardButton(text="⬅️ В меню", callback_data="back_menu")]
    ])

# ================== START ==================

@router.message(F.text == "/start")
async def start(msg: types.Message, state: FSMContext):
    if msg.from_user.id in approved_users:
        await msg.answer_photo(PHOTO_ID, caption=main_menu_caption(msg.from_user), reply_markup=main_menu())
    else:
        await state.set_state(ApplyFSM.source)
        await msg.answer("1️⃣ <b>Откуда узнали о нас?</b>")

# ================== APPLY ==================

@router.message(ApplyFSM.source)
async def apply_source(msg: types.Message, state: FSMContext):
    await state.update_data(source=msg.text)
    await state.set_state(ApplyFSM.experience)
    await msg.answer("2️⃣ <b>Ваш опыт работы?</b>")

@router.message(ApplyFSM.experience)
async def apply_exp(msg: types.Message, state: FSMContext):
    await state.update_data(experience=msg.text)
    await state.set_state(ApplyFSM.time)
    await msg.answer("3️⃣ <b>Сколько времени готовы уделять?</b>")

@router.message(ApplyFSM.time)
async def apply_time(msg: types.Message, state: FSMContext):
    data = await state.get_data()
    data["time"] = msg.text
    applications[msg.from_user.id] = data

    text = (
        "📝 <b>Новая заявка</b>\n\n"
        f"👤 ID: <code>{msg.from_user.id}</code>\n"
        f"📍 Источник: {data['source']}\n"
        f"🧠 Опыт: {data['experience']}\n"
        f"⏳ Время: {data['time']}"
    )

    for admin in ADMIN_IDS:
        await bot.send_message(admin, text, reply_markup=approve_kb(msg.from_user.id))

    await msg.answer("✅ Заявка отправлена. Ожидайте решения.")
    await state.clear()

# ================== ADMIN ==================

@router.callback_query(F.data.startswith("approve:"))
async def approve(call: types.CallbackQuery):
    user_id = int(call.data.split(":")[1])
    approved_users.add(user_id)

    await bot.send_message(user_id, "✅ Ваша заявка одобрена!")
    await bot.send_photo(user_id, PHOTO_ID, caption="🏠 Главное меню", reply_markup=main_menu())
    await call.answer("Готово")

@router.callback_query(F.data.startswith("reject:"))
async def reject(call: types.CallbackQuery):
    user_id = int(call.data.split(":")[1])
    await bot.send_message(user_id, "❌ Ваша заявка отклонена")
    await call.answer("Отклонено")

# ================== CREATE LINK ==================

@router.callback_query(F.data == "create_link")
async def create_link(call: types.CallbackQuery, state: FSMContext):
    await state.set_state(LinkFSM.service)

    await call.message.edit_media(
        InputMediaPhoto(PHOTO_ID, caption="🔗 <b>Выберите сервис</b>"),
        reply_markup=services_kb()
    )

    await call.answer()

@router.callback_query(F.data.startswith("srv:"))
async def choose_service(call: types.CallbackQuery, state: FSMContext):
    service = call.data.split(":")[1]
    await state.update_data(service=service)
    await state.set_state(LinkFSM.price)

    await call.message.answer(f"💰 Введите стоимость для <b>{service}</b>")
    await call.answer()

# ================== PRICE ==================

@router.message(LinkFSM.price)
async def set_price(msg: types.Message, state: FSMContext):
    if not msg.text.isdigit():
        await msg.answer("❌ Введите число")
        return

    data = await state.get_data()
    link = f"https://example.com/{uuid.uuid4().hex[:8]}"

    user_links.setdefault(msg.from_user.id, []).append({
        "service": data["service"],
        "price": msg.text,
        "link": link
    })

    await msg.answer(f"✅ Ссылка создана!\n<b>{data['service']} | {msg.text}₴</b>\n{link}")
    await state.clear()

# ================== MY LINKS ==================

@router.callback_query(F.data == "my_links")
async def my_links(call: types.CallbackQuery):
    links = user_links.get(call.from_user.id, [])

    if not links:
        await call.answer("❌ Нет объявлений", show_alert=True)
        return

    text = "📋 <b>Ваши объявления:</b>\n\n"

    kb = []

    for i, l in enumerate(links):
        text += f"{i+1}. {l['service']} | {l['price']}₴\n{l['link']}\n\n"
        kb.append([InlineKeyboardButton(text=f"Удалить {i+1}", callback_data=f"del:{i}")])

    kb.append([InlineKeyboardButton(text="Удалить все", callback_data="del_all")])
    kb.append([InlineKeyboardButton(text="⬅️ В меню", callback_data="back_menu")])

    await call.message.answer(text, reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await call.answer()

@router.callback_query(F.data.startswith("del:"))
async def delete_one(call: types.CallbackQuery):
    idx = int(call.data.split(":")[1])
    user_links[call.from_user.id].pop(idx)
    await call.answer("Удалено")
    await my_links(call)

@router.callback_query(F.data == "del_all")
async def delete_all(call: types.CallbackQuery):
    user_links[call.from_user.id] = []
    await call.message.answer("📭 Объявлений нет", reply_markup=main_menu())
    await call.answer("Все удалено")

# ================== BACK ==================

@router.callback_query(F.data == "back_menu")
async def back_menu(call: types.CallbackQuery):
    await call.message.edit_media(
        InputMediaPhoto(PHOTO_ID, caption=main_menu_caption(call.from_user)),
        reply_markup=main_menu()
    )
    await call.answer()

# ================== RUN ==================

async def main():
    dp.include_router(router)
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
