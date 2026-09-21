import asyncio
import logging
import os
import sqlite3
from datetime import datetime, timedelta
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    ReplyKeyboardMarkup, 
    KeyboardButton, 
    InlineKeyboardMarkup, 
    InlineKeyboardButton
)
from dotenv import load_dotenv

# .env faylidan tokenlarni yuklaymiz
load_dotenv()

# ==================== AYARLAR ====================
BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = int(os.getenv("ADMIN_ID", "7214612272"))

# Bot Nesnesi
bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()


# ==================== VERİTABANI ====================
def init_db():
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY,
            full_name TEXT,
            username TEXT,
            joined_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS homework (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            subject TEXT,
            group_type TEXT,
            task TEXT,
            photo_id TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)
    
    try:
        cursor.execute("ALTER TABLE homework ADD COLUMN created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP")
    except sqlite3.OperationalError:
        pass

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS books (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            title TEXT,
            file_id TEXT
        )
    """)
    
    conn.commit()
    conn.close()

def add_user(user_id: int, full_name: str, username: str):
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT OR IGNORE INTO users (user_id, full_name, username) VALUES (?, ?, ?)",
        (user_id, full_name, username)
    )
    conn.commit()
    conn.close()

def count_users():
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    cursor.execute("SELECT COUNT(*) FROM users")
    count = cursor.fetchone()[0]
    conn.close()
    return count

def get_all_users():
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id FROM users")
    users = cursor.fetchall()
    conn.close()
    return [u[0] for u in users]

def get_detailed_users():
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    cursor.execute("SELECT user_id, full_name, username, joined_at FROM users")
    users = cursor.fetchall()
    conn.close()
    return users

def clean_old_homework():
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    two_days_ago = datetime.now() - timedelta(days=2)
    cursor.execute("DELETE FROM homework WHERE created_at < ?", (two_days_ago.strftime("%Y-%m-%d %H:%M:%S"),))
    conn.commit()
    conn.close()

def add_homework(subject: str, group_type: str, task: str, photo_id: str = None):
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    cursor.execute(
        "INSERT INTO homework (subject, group_type, task, photo_id, created_at) VALUES (?, ?, ?, ?, ?)",
        (subject, group_type, task, photo_id, datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    )
    conn.commit()
    conn.close()

def get_latest_homework():
    try:
        clean_old_homework()
    except Exception:
        pass
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, subject, group_type, task, photo_id FROM homework ORDER BY id DESC")
    data = cursor.fetchall()
    conn.close()
    return data

def delete_homework_by_id(hw_id: int):
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    cursor.execute("DELETE FROM homework WHERE id = ?", (hw_id,))
    conn.commit()
    conn.close()

def add_book(title: str, file_id: str):
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    cursor.execute("INSERT INTO books (title, file_id) VALUES (?, ?)", (title, file_id))
    conn.commit()
    conn.close()

def get_all_books():
    conn = sqlite3.connect("school.db")
    cursor = conn.cursor()
    cursor.execute("SELECT id, title, file_id FROM books")
    data = cursor.fetchall()
    conn.close()
    return data


# ==================== MENÜ BUTONLARI ====================

main_menu = ReplyKeyboardMarkup(
    keyboard=[
        [
            KeyboardButton(text="📅 Dars jadvali"),
            KeyboardButton(text="📝 Uyga vazifalar")
        ],
        [
            KeyboardButton(text="🎨 To'garaklar jadvali"),
            KeyboardButton(text="📚 Kitoblar (PDF)")
        ]
    ],
    resize_keyboard=True
)

admin_inline_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="📊 Statistika (Foydalanuvchilar)", callback_data="admin_stats"),
            InlineKeyboardButton(text="📢 Xabar Yuborish", callback_data="admin_broadcast")
        ],
        [
            InlineKeyboardButton(text="➕ Uyga vazifa qo'shish", callback_data="admin_add_hw"),
            InlineKeyboardButton(text="🗑 Vazifani o'chirish", callback_data="admin_delete_hw")
        ],
        [
            InlineKeyboardButton(text="➕ Kitob qo'shish", callback_data="admin_add_book")
        ]
    ]
)

group_select_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="1️⃣ 1-Guruh", callback_data="group_1"),
            InlineKeyboardButton(text="2️⃣ 2-Guruh", callback_data="group_2")
        ],
        [
            InlineKeyboardButton(text="🌐 Barcha uchun (Umumiy)", callback_data="group_all")
        ]
    ]
)

days_inline_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="📌 Dushanba", callback_data="day_dushanba"),
            InlineKeyboardButton(text="📌 Seshanba", callback_data="day_seshanba")
        ],
        [
            InlineKeyboardButton(text="📌 Chorshanba", callback_data="day_chorshanba"),
            InlineKeyboardButton(text="📌 Payshanba", callback_data="day_payshanba")
        ],
        [
            InlineKeyboardButton(text="📌 Juma", callback_data="day_juma")
        ]
    ]
)

clubs_inline_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [
            InlineKeyboardButton(text="📌 Dushanba", callback_data="club_dushanba"),
            InlineKeyboardButton(text="📌 Seshanba", callback_data="club_seshanba")
        ],
        [
            InlineKeyboardButton(text="📌 Chorshanba", callback_data="club_chorshanba"),
            InlineKeyboardButton(text="📌 Payshanba", callback_data="club_payshanba")
        ],
        [
            InlineKeyboardButton(text="📌 Juma", callback_data="club_juma")
        ]
    ]
)

back_to_days_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_days")]
    ]
)

back_to_clubs_menu = InlineKeyboardMarkup(
    inline_keyboard=[
        [InlineKeyboardButton(text="🔙 Orqaga", callback_data="back_to_clubs")]
    ]
)


# ==================== FSM DURUMLARI ====================
class HomeworkState(StatesGroup):
    subject = State()
    group = State()
    task = State()
    photo = State()

class BookState(StatesGroup):
    title = State()
    file = State()

class BroadcastState(StatesGroup):
    message = State()


# ==================== PROGRAM VERİLERİ ====================
SCHEDULES = {
    "day_dushanba": (
        "<b>📌 DUSHANBA DARS JADVALI:</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "1-soat: 🚀 Kelajak soati\n"
        "2-soat: ⚡ Fizika\n"
        "3-soat: ⚽ Jismoniy tarbiya\n"
        "4-soat: 🌍 Jahon tarixi\n"
        "5-soat: 🇺🇿 Oʻzbekiston tarixi\n"
        "6-soat: 📐 Geometriya\n"
        "7-soat: 🪆 Rus tili"
    ),
    "day_seshanba": (
        "<b>📌 SESHANBA DARS JADVALI:</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "1-soat: 📖 Ona tili\n"
        "2-soat: 🗺 Geografiya\n"
        "3-soat: 🎨 Tasviriy sanʼat\n"
        "4-soat: ⚡ Fizika\n"
        "5-soat: 🔢 Algebra\n"
        "6-soat: 🇬🇧 Chet tili\n"
        "7-soat: 🧪 Kimyo"
    ),
    "day_chorshanba": (
        "<b>📌 CHORSHANBA DARS JADVALI:</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "1-soat: 🇺🇿 Oʻzbekiston tarixi\n"
        "2-soat: 💡 Tarbiya\n"
        "3-soat: 🔢 Algebra\n"
        "4-soat: 🇬🇧 Chet tili\n"
        "5-soat: 💻 Informatika\n"
        "6-soat: ⚽ Jismoniy tarbiya\n"
        "7-soat: 🗺 Geografiya"
    ),
    "day_payshanba": (
        "<b>📌 PAYSHANBA DARS JADVALI:</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "1-soat: 🪆 Rus tili\n"
        "2-soat: 🔢 Algebra\n"
        "3-soat: 🇬🇧 Chet tili\n"
        "4-soat: 📖 Ona tili\n"
        "5-soat: 📐 Geometriya\n"
        "6-soat: 🌿 Biologiya\n"
        "7-soat: 📚 Adabiyot"
    ),
    "day_juma": (
        "<b>📌 JUMA DARS JADVALI:</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "1-soat: 📚 Adabiyot\n"
        "2-soat: 🔢 Algebra\n"
        "3-soat: ⚡ Fizika\n"
        "4-soat: 📐 Geometriya\n"
        "5-soat: 🇬🇧 Chet tili\n"
        "6-soat: ⚙️ Texnik aloqa\n"
        "7-soat: 🌿 Biologiya"
    )
}

CLUBS_SCHEDULE = {
    "club_dushanba": (
        "<b>🎨 DUSHANBA TO'GARAKLAR JADVALI:</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "⚡ Fizika to'garagi"
    ),
    "club_seshanba": (
        "<b>🎨 SESHANBA TO'GARAKLAR JADVALI:</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "🇬🇧 Ingliz tili to'garagi"
    ),
    "club_chorshanba": (
        "<b>🎨 CHORSHANBA TO'GARAKLAR JADVALI:</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "🔢 Matematika to'garagi"
    ),
    "club_payshanba": (
        "<b>🎨 PAYSHANBA TO'GARAKLAR JADVALI:</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "🇬🇧 Ingliz tili to'garagi"
    ),
    "club_juma": (
        "<b>🎨 JUMA TO'GARAKLAR JADVALI:</b>\n"
        "━━━━━━━━━━━━━━━━━━━\n"
        "⚽ Jismoniy tarbiya to'garagi"
    )
}


# ==================== HANDLERLAR ====================

@dp.message(CommandStart())
async def start_handler(message: types.Message):
    user_name = message.from_user.first_name or "Foydalanuvchi"
    add_user(
        user_id=message.from_user.id,
        full_name=message.from_user.full_name,
        username=message.from_user.username or "mavjud_emas"
    )
    
    await message.answer(
        f"🚀 <b>Salom, {user_name}!</b>\n\n"
        "Sinfimizning aqlli botiga xush kelibsiz! Kerakli bo'limni tanlang:",
        reply_markup=main_menu,
        parse_mode="HTML"
    )

# Admin Panel
@dp.message(Command("admin"))
async def admin_command_handler(message: types.Message):
    if message.from_user.id != ADMIN_ID:
        return
    
    total_users = count_users()
    await message.answer(
        f"👑 <b>Admin Paneliga xush kelibsiz!</b>\n\n"
        f"👥 Hozirda botdan <b>{total_users} ta</b> foydalanuvchi foydalanmoqda.\n\n"
        "Kerakli amalni tanlang:",
        reply_markup=admin_inline_menu,
        parse_mode="HTML"
    )

@dp.callback_query(F.data == "admin_stats")
async def process_admin_stats(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    users = get_detailed_users()
    total_users = len(users)
    
    text = f"📊 <b>BOT FOYDALANUVCHILARI RO'YXATI ({total_users} ta):</b>\n━━━━━━━━━━━━━━━━━━━\n\n"
    
    for u_id, name, username, joined in users:
        u_link = f"@{username}" if username != "mavjud_emas" else "Usernamenisiz"
        text += f"👤 <b>{name}</b> ({u_link})\n🆔 ID: <code>{u_id}</code>\n📅 Sanasi: {joined}\n\n"
    
    if len(text) > 4000:
        for x in range(0, len(text), 4000):
            await callback.message.answer(text[x:x+4000], parse_mode="HTML")
    else:
        await callback.message.answer(text, parse_mode="HTML")
        
    await callback.answer()

@dp.callback_query(F.data == "admin_broadcast")
async def process_admin_broadcast(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    await callback.message.answer("📢 Barcha foydalanuvchilarga yubormoqchi bo'lgan xabaringizni yozing:")
    await state.set_state(BroadcastState.message)
    await callback.answer()

@dp.message(BroadcastState.message)
async def process_broadcast_message(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    users = get_all_users()
    count = 0
    await message.answer("⏳ Xabar yuborilmoqda...")
    
    for user_id in users:
        try:
            await message.copy_to(chat_id=user_id)
            count += 1
            await asyncio.sleep(0.05)
        except Exception:
            pass
            
    await message.answer(f"✅ Xabar <b>{count} ta</b> foydalanuvchiga muvaffaqiyatli yuborildi!", parse_mode="HTML")
    await state.clear()


# Admin: Ödev Ekleme
@dp.callback_query(F.data == "admin_add_hw")
async def process_admin_add_hw(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    await callback.message.answer("Qaysi fandan vazifa? (Masalan: Matematika, Ingliz tili):")
    await state.set_state(HomeworkState.subject)
    await callback.answer()

@dp.message(HomeworkState.subject)
async def process_hw_subject(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.update_data(subject=message.text)
    await message.answer("Ushbu vazifa qaysi guruh uchun?", reply_markup=group_select_menu)
    await state.set_state(HomeworkState.group)

@dp.callback_query(HomeworkState.group, F.data.startswith("group_"))
async def process_hw_group(callback: types.CallbackQuery, state: FSMContext):
    group_map = {
        "group_1": "1-Guruh",
        "group_2": "2-Guruh",
        "group_all": "Barcha uchun"
    }
    selected_group = group_map.get(callback.data, "Barcha uchun")
    await state.update_data(group=selected_group)
    
    await callback.message.answer("Vazifa matnini kiriting (yoki tushuntirish yozing):")
    await state.set_state(HomeworkState.task)
    await callback.answer()

@dp.message(HomeworkState.task)
async def process_hw_task(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.update_data(task=message.text)
    await message.answer(
        "📷 Ushbu vazifaga Rasm yuklaysizmi?\n\n"
        "Rasmni yuboring yoki rasm bo'lmasa <b>'Yo'q'</b> deb yozing:",
        parse_mode="HTML"
    )
    await state.set_state(HomeworkState.photo)

@dp.message(HomeworkState.photo)
async def process_hw_photo(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    
    data = await state.get_data()
    photo_id = None
    
    if message.photo:
        photo_id = message.photo[-1].file_id
    elif message.text and message.text.lower() in ["yo'q", "yoq", "no"]:
        photo_id = None
    else:
        await message.answer("Iltimos, rasm yuboring yoki 'Yo'q' deb yozing.")
        return
        
    add_homework(
        subject=data['subject'],
        group_type=data['group'],
        task=data['task'],
        photo_id=photo_id
    )
    
    await message.answer("✅ Uyga vazifa muvaffaqiyatli saqlandi va e'lon qilindi!")
    await state.clear()


# Admin: Ödev Silme
@dp.callback_query(F.data == "admin_delete_hw")
async def process_admin_delete_hw(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    tasks = get_latest_homework()
    if not tasks:
        await callback.message.answer("📌 O'chirish uchun hech qanday vazifa topilmadi.")
        await callback.answer()
        return

    for hw_id, subject, group_type, task, photo_id in tasks:
        delete_btn = InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text=f"🗑 O'chirish (ID: {hw_id})", callback_data=f"del_hw_{hw_id}")
            ]]
        )
        caption_text = f"📌 <b>{subject}</b> ({group_type}):\n{task}"
        
        if photo_id:
            await callback.message.answer_photo(photo=photo_id, caption=caption_text, reply_markup=delete_btn, parse_mode="HTML")
        else:
            await callback.message.answer(text=caption_text, reply_markup=delete_btn, parse_mode="HTML")
            
    await callback.answer()

@dp.callback_query(F.data.startswith("del_hw_"))
async def process_confirm_delete_hw(callback: types.CallbackQuery):
    if callback.from_user.id != ADMIN_ID:
        return
    
    hw_id = int(callback.data.split("_")[2])
    delete_homework_by_id(hw_id)
    
    await callback.message.edit_reply_markup(reply_markup=None)
    await callback.message.answer("✅ Vazifa bazadan muvaffaqiyatli o'chirildi!")
    await callback.answer()


# ==================== 📝 ÖDEVLERİ GÖRÜNTÜLEME ====================
@dp.message(F.text.contains("Uyga vazifalar"))
async def homework_view_handler(message: types.Message):
    tasks = get_latest_homework()
    if not tasks:
        await message.answer("📝 Hozircha uyga vazifa yuklanmagan.")
        return
    
    await message.answer("<b>📝 MAVJUD UYGA VAZIFALAR:</b>", parse_mode="HTML")
    
    for hw_id, subject, group_type, task, photo_id in tasks:
        badge = "👥" if group_type == "Barcha uchun" else ("1️⃣" if group_type == "1-Guruh" else "2️⃣")
        caption_text = f"📌 <b>{subject}</b> | {badge} <b>{group_type}</b>\n━━━━━━━━━━━━━━━━━━━\n{task}"
        
        if photo_id:
            await message.answer_photo(photo=photo_id, caption=caption_text, parse_mode="HTML")
        else:
            await message.answer(text=caption_text, parse_mode="HTML")


# ==================== 📅 DERS PROGRAMI ====================
@dp.message(F.text.contains("Dars jadvali"))
async def schedule_menu_handler(message: types.Message):
    await message.answer(
        "📅 <b>Qaysi kunning dars jadvali kerak?</b>\n"
        "Quyidagi kunlardan birini tanlang:",
        reply_markup=days_inline_menu,
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("day_"))
async def process_day_callback(callback: types.CallbackQuery):
    day_key = callback.data
    text = SCHEDULES.get(day_key, "Dars jadvali topilmadi.")
    
    await callback.message.edit_text(
        text=text,
        reply_markup=back_to_days_menu,
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_days")
async def process_back_callback(callback: types.CallbackQuery):
    await callback.message.edit_text(
        text="📅 <b>Qaysi kunning dars jadvali kerak?</b>\n"
             "Quyidagi kunlardan birini tanlang:",
        reply_markup=days_inline_menu,
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== 🎨 KULÜP PROGRAMI ====================
@dp.message(F.text.contains("To'garak"))
async def clubs_menu_handler(message: types.Message):
    await message.answer(
        "🎨 <b>Qaysi kunning to'garaklar jadvali kerak?</b>\n"
        "Quyidagi kunlardan birini tanlang:",
        reply_markup=clubs_inline_menu,
        parse_mode="HTML"
    )

@dp.callback_query(F.data.startswith("club_"))
async def process_club_callback(callback: types.CallbackQuery):
    club_key = callback.data
    text = CLUBS_SCHEDULE.get(club_key, "To'garak jadvali topilmadi.")
    
    await callback.message.edit_text(
        text=text,
        reply_markup=back_to_clubs_menu,
        parse_mode="HTML"
    )
    await callback.answer()

@dp.callback_query(F.data == "back_to_clubs")
async def process_back_clubs_callback(callback: types.CallbackQuery):
    await callback.message.edit_text(
        text="🎨 <b>Qaysi kunning to'garaklar jadvali kerak?</b>\n"
             "Quyidagi kunlardan birini tanlang:",
        reply_markup=clubs_inline_menu,
        parse_mode="HTML"
    )
    await callback.answer()


# ==================== 📚 KİTAPLAR ====================
@dp.message(F.text.contains("Kitoblar"))
async def books_handler(message: types.Message):
    books = get_all_books()
    if not books:
        await message.answer("📂 Hozircha kutubxonaga kitoblar yuklanmagan.")
        return
    
    await message.answer("📚 Mavjud darslik va kitoblar:")
    for b_id, title, file_id in books:
        await message.answer_document(document=file_id, caption=f"📘 {title}")

@dp.callback_query(F.data == "admin_add_book")
async def process_admin_add_book(callback: types.CallbackQuery, state: FSMContext):
    if callback.from_user.id != ADMIN_ID:
        return
    await callback.message.answer("Kitob / Darslik nomini kiriting:")
    await state.set_state(BookState.title)
    await callback.answer()

@dp.message(BookState.title)
async def process_book_title(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    await state.update_data(title=message.text)
    await message.answer("Endi PDF faylni yuboring:")
    await state.set_state(BookState.file)

@dp.message(BookState.file, F.document)
async def process_book_file(message: types.Message, state: FSMContext):
    if message.from_user.id != ADMIN_ID:
        return
    data = await state.get_data()
    file_id = message.document.file_id
    add_book(data['title'], file_id)
    await message.answer("✅ PDF darslik bazaga saqlandi!")
    await state.clear()


# ==================== BOTU BAŞLATMA ====================
async def main():
    logging.basicConfig(level=logging.INFO)
    init_db()
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())