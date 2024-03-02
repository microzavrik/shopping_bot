import logging
import sqlite3

from config import *
from db import db, create_db

from aiogram import Bot, Dispatcher, executor, types
from aiogram.dispatcher.filters.state import StatesGroup, State
from aiogram.contrib.fsm_storage.memory import MemoryStorage
from aiogram.dispatcher import FSMContext
from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton

import asyncio

import re

set_role_user_id = 0

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
bot = Bot(token=token, parse_mode="HTML")
dp = Dispatcher(bot=bot, storage=MemoryStorage())

states = [State('user', StatesGroup),
          State('image', StatesGroup)]

# SQLite database connection
conn = sqlite3.connect("users.db")
cursor = conn.cursor()

Send_Image = False

photo_for_mailing = ""
previous_message = None
previous_reply_markup = None

admin_replies = {}  

# Create 'users' table if it doesn't exist
cursor.execute("CREATE TABLE IF NOT EXISTS users (id INTEGER PRIMARY KEY, role TEXT)")

class user(StatesGroup):
    name = State()
    text = State()
    image = State()
    input_image = State()
    text_template = State()

@dp.message_handler(commands=["start"], state="*")
async def start(message: types.Message, state: FSMContext):
    await state.finish()

    user_id = message.from_user.id
    user_un = message.from_user.username
    if user_un is None:
        user_un = message.from_user.first_name


    # Check if the user ID is already present in the database
    cursor.execute("SELECT id FROM users WHERE id = ?", (user_id, ))
    existing_user = cursor.fetchone()

    if not existing_user:
        # Insert the user ID into the database
        print(f"User: {user_id} added to data base")
        cursor.execute("INSERT INTO users (id, role) VALUES (?, ?)", (user_id, "Default"))
        conn.commit()

    if user_id == int(admin):
        await message.answer("<b>Вы являетесь администратором, пропишите команду /admin</b>")
    else:
        keyboard = types.InlineKeyboardMarkup(row_width=5)
        row = []
        try:
            for template in db.get_templates():
                template_btn = types.InlineKeyboardButton(text=template, callback_data=f"send_{template}_{user_id}")
                row.append(template_btn)
            keyboard.add(*row)
        except:
            pass

        delete_message_button = types.InlineKeyboardButton(text="Удалить это сообщение", callback_data="delete_message")
        keyboard.add(delete_message_button)
        print("add")

        user_id = message.from_user.id

        # Query the database to retrieve the user's role
        cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
        result = cursor.fetchone()
        if result:
            role = result[0]
        else:
            role = "Unknown"

        string_role = ""

        if role == "Default":
            string_role = "Обычный клиент 🤖"
        elif role == "Want Client":
            string_role = "Потенциальный покупатель 💸"
        elif role == "Buy Client":
            string_role = "Купивший 💳"

        message_text = f"<b>Новое сообщение</b>\n\n" \
                       f"<code>{message.text}</code>\n\n" \
                       f"<b>От: <a href='tg://user?id={user_id}'>{user_un}</a></b>\n" \
                       f"Статус пользователя: {string_role}\n" \
                       f"<b>Айди пользователя:</b> <code>{user_id}</code>"

        add = types.InlineKeyboardButton(text="Изменить статус ✨", callback_data="change_role")
        keyboard.add(add)

        await bot.send_message(text=message_text, reply_markup=keyboard, chat_id=admin)

@dp.message_handler(commands=["admin"], state="*")
async def admin_command(message: types.Message, state: FSMContext):
    user_id = message.from_user.id

    if user_id != int(admin):
        return

    if user_id == int(admin):
        keyboard = types.InlineKeyboardMarkup(row_width=1)
        add = types.InlineKeyboardButton(text="➕ Добавить", callback_data="add_template")
        delete = types.InlineKeyboardButton(text="🗑 Удалить", callback_data="delete_template")
        mailing_button = types.InlineKeyboardButton(text="📧 Рассылка", callback_data="mailing")
        view_users_button = types.InlineKeyboardButton(text="👥 Просмотреть пользователей", callback_data="view_users")
        keyboard.add(add, delete, mailing_button, view_users_button)

    await message.answer("<b>🕵️‍♂️ Админ - панель</b>", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == "view_users")
async def view_users_callback(call: types.CallbackQuery, state: FSMContext):
    cursor.execute("SELECT id, role FROM users")
    users = cursor.fetchall()

    default_user = 0
    want_user = 0
    buy_user = 0

    user_list = "<b>Users:</b> 🌟\n"
    separator = "─" * 20  # Customize the number of dashes as needed
    user_list += f"\n{separator}\n\n"
    for user_id, role in users:
        username = await get_username(user_id)

        if role == "Default":
            role = "Обычный клиент 🤖"
            default_user += 1
        elif role == "Want Client":
            role = "Потенциальный покупатель 💸"
            want_user += 1
        elif role == "Buy Client":
            role = "Купивший 💳"
            buy_user += 1

        user_list += f"<b>@{username}</b> | {role}\n"

    user_list += f"\n\nКоличество клиентов по статусам:\n\n🔸Обычные: {default_user}\n🔸Потенциальные: {want_user}\n🔸Купившие: {buy_user}"

    await call.message.edit_text(user_list, parse_mode="HTML")

    # Call the function directly
    await view_users_callback(call, state)


async def get_username(user_id):
    user = await bot.get_chat(user_id)
    return user.username or user.first_name
        
@dp.callback_query_handler(lambda c: c.data == "mailing", state="*")
async def mailing_button_click(call: types.CallbackQuery, state: FSMContext):
    keyboard = InlineKeyboardMarkup(row_width=1)
    keyboard.add(
        InlineKeyboardButton(text="Обычным клиентам 🤖", callback_data="select_role_Default"),
        InlineKeyboardButton(text="Потенциальным клиентам 💸", callback_data="select_role_Want_Client"),
        InlineKeyboardButton(text="Купившим 💸", callback_data="select_role_Buy_Client"),
        InlineKeyboardButton(text="Всем пользователям 👥", callback_data="select_role_All_Users"),
    )
    await call.message.edit_text("Выберите статус для рассылки:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith("select_role"), state="*")
async def select_role_callback(call: types.CallbackQuery, state: FSMContext):
    selected_role = call.data.split("_")[2]  # Modified line
    await state.update_data(selected_role=selected_role)

    print(selected_role)

    display_role = ""

    if selected_role == "Default":
        display_role = "Обычный клиент 🤖"
    if selected_role == "Want":
        display_role = "Потенциальный клиент 💸"
    if selected_role == "Buy":
        display_role = "Купивший 💳"

    await call.message.edit_text(f"Выбран статус: {display_role}\nВведите текст для рассылки: ")
    await call.answer()
    await user.text.set()

@dp.callback_query_handler(lambda call: call.data == "delete_message")
async def delete_message_callback(callback_query: types.CallbackQuery):
    print("нажата кнопка удаления сообщения")
    
    chat_id = callback_query.message.chat.id
    message_id = callback_query.message.message_id
    
    if message_id in admin_replies:
        # Удаляем ответы администратора из чата
        admin_reply_message_ids = admin_replies[message_id]
        for reply_message_id in admin_reply_message_ids:
            try:
                await bot.delete_message(chat_id, reply_message_id)
            except Exception as e:
                print(f"An error occurred while deleting message {reply_message_id}: {e}")
    
        # Удаляем значение из admin_replies
        del admin_replies[message_id]
    
    await callback_query.answer()  # Отправляем уведомление о нажатии кнопки
    await bot.delete_message(chat_id, message_id)  # Удаляем исходное сообщение

    

@dp.message_handler(state=user.text)
async def send_mailing_text(message: types.Message, state: FSMContext):
    global text_for_malling
    print(message.text)
    text_for_malling = message.text
    print(text_for_malling)

    await message.answer("Прикрепите изображение для рассылки, или введите '-' для пропуска этого шага.")
    await user.next()
    current_state = await state.get_state()
    print(current_state)

@dp.message_handler(content_types=types.ContentType.PHOTO, state=user.image)
async def send_mailing_image(message: types.Message, state: FSMContext):
    photo_for_mailing = message.photo[-1].file_id

    data = await state.get_data()
    selected_role = data.get("selected_role")
    print(selected_role)

    if selected_role == "All":
        cursor.execute("SELECT id FROM users")
    elif selected_role == "Buy":
        cursor.execute("SELECT id FROM users WHERE role = ?", ("Buy Client",))
    elif selected_role == "Default":
        cursor.execute("SELECT id FROM users WHERE role = ?", ("Default",))
    elif selected_role == "Want":
        cursor.execute("SELECT id FROM users WHERE role = ?", ("Want Client",))

    users = [str(user[0]) for user in cursor.fetchall()]

    print("#1")
    print(text_for_malling)

    success_send = 0
    failed_send = 0

    for user_id in users:
        print(user_id)
        if text_for_malling and photo_for_mailing:
            try:
                print(user_id)
                await bot.send_photo(photo=photo_for_mailing, caption=text_for_malling, chat_id=user_id)
                success_send += 1
            except Exception as e:
                print(user_id)
                print(f"An error occurred while sending message to user {user_id}: {e}")
                failed_send += 1
        elif text_for_malling:
            try:
                await bot.send_message(text=text_for_malling, chat_id=user_id)
                success_send += 1
            except Exception as e:
                print(user_id)
                print(f"An error occurred while sending message to user {user_id}: {e}")
                failed_send += 1
        elif photo_for_mailing:
            try:
                await bot.send_photo(photo=photo_for_mailing, caption="", chat_id=user_id)
                success_send += 1
            except Exception as e:
                print(user_id)
                print(f"An error occurred while sending message to user {user_id}: {e}")
                failed_send += 1

    await message.answer("Рассылка завершена.\n\n✅ Удачно" + str(success_send) + "\n❌ Неудачно: " + str(failed_send))
    await state.finish()

@dp.message_handler(state=user.image)
async def send_mailing_image(message: types.Message, state: FSMContext):
    data = await state.get_data()
    selected_role = data.get("selected_role")
    print(selected_role)

    if selected_role == "All":
        cursor.execute("SELECT id FROM users")
    elif selected_role == "Buy":
        cursor.execute("SELECT id FROM users WHERE role = ?", ("Buy Client",))
    elif selected_role == "Default":
        cursor.execute("SELECT id FROM users WHERE role = ?", ("Default",))
    elif selected_role == "Want":
        cursor.execute("SELECT id FROM users WHERE role = ?", ("Want Client",))

    users = [str(user[0]) for user in cursor.fetchall()]

    success_send = 0
    failed_send = 0

    for user_id in users:
        print(user_id)
        if text_for_malling and photo_for_mailing:
            try:
                print(user_id)
                await bot.send_photo(photo=photo_for_mailing, caption=text_for_malling, chat_id=user_id)
                success_send += 1
            except Exception as e:
                print(user_id)
                print(f"An error occurred while sending message to user {user_id}: {e}")
                failed_send += 1
        elif text_for_malling:
            try:
                await bot.send_message(text=text_for_malling, chat_id=user_id)
                success_send += 1
            except Exception as e:
                print(user_id)
                print(f"An error occurred while sending message to user {user_id}: {e}")
                failed_send += 1
        elif photo_for_mailing:
            try:
                await bot.send_photo(photo=photo_for_mailing, caption="", chat_id=user_id)
                success_send += 1
            except Exception as e:
                print(user_id)
                print(f"An error occurred while sending message to user {user_id}: {e}")
                failed_send += 1

    await message.answer("Рассылка завершена.\n\n✅ Удачно: " + str(success_send) + "\n\n❌ Неудачно: " + str(failed_send))
    await state.finish()
    
@dp.callback_query_handler(lambda c: c.data == "add_template", state="*")
async def add_template(call: types.CallbackQuery):
    keyboard = types.InlineKeyboardMarkup()
    back = types.InlineKeyboardButton(text="🔙 Назад", callback_data="back")
    keyboard.add(back)

    await call.message.edit_text("<b>Введите название для шаблона:</b>", reply_markup=keyboard)

    await user.name.set()

@dp.message_handler(state=user.name)
async def name(message: types.Message, state: FSMContext):
    await state.update_data(name=message.text)

    keyboard = types.InlineKeyboardMarkup()
    back = types.InlineKeyboardButton(text="🔙 Назад", callback_data="back")
    keyboard.add(back)

    await message.answer(f"<b>Введите текст для {message.text}:</b>", reply_markup=keyboard)

    await user.text_template.set()

@dp.message_handler(state=user.text_template)
async def text(message: types.Message, state: FSMContext):
    data = await state.get_data()

    db.add_template(data["name"], message.text)

    keyboard = types.InlineKeyboardMarkup()
    back = types.InlineKeyboardButton(text="🔙 Назад", callback_data="back")
    keyboard.add(back)

    await message.answer("<b>Шаблон успешно добавлен!</b>", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == "delete_template", state="*")
async def delete_template(call: types.CallbackQuery, state: FSMContext):
    
    keyboard = types.InlineKeyboardMarkup(row_width=5)
    row = []
    try:
        for template in db.get_templates():
            template_btn = types.InlineKeyboardButton(text=template, callback_data=f"delete_{template}")
            row.append(template_btn)
        keyboard.add(*row)
    except:
        pass
    back = types.InlineKeyboardButton(text="🔙 Назад", callback_data="back")
    keyboard.add(back)

    await call.message.edit_text("<b>Выберите шаблон, который хотите удалить.</b>", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data.startswith("delete_"), state="*")
async def delete_template(call: types.CallbackQuery, state: FSMContext):
    template = call.data[len("delete_"):]

    db.delete_template(template)

    keyboard = types.InlineKeyboardMarkup(row_width=5)
    row = []
    try:
        for template in db.get_templates():
            template_btn = types.InlineKeyboardButton(text=template, callback_data=f"delete_{template}")
            row.append(template_btn)
        keyboard.add(*row)
    except:
        pass
    back = types.InlineKeyboardButton(text="🔙 Назад", callback_data="back")
    keyboard.add(back)

    await call.message.edit_reply_markup(keyboard)
    await call.answer(f"Шаблон {template} успешно удален!", show_alert=True)

@dp.callback_query_handler(lambda c: c.data.startswith("send_"), state="*")
async def send_template(call: types.CallbackQuery, state: FSMContext):
    template, user_id = call.data[len("send_"):].split("_")

    text = db.get_template(template)
    
    await bot.send_message(text=text, chat_id=user_id)

@dp.callback_query_handler(lambda c: c.data == "back_button", state="*")
async def back_button_click(call: types.CallbackQuery):
    global previous_message, previous_reply_markup
    if previous_message is not None:
        await previous_message.edit_text(previous_message.text, reply_markup=previous_reply_markup)  # Restore previous message's reply markup (buttons)
        previous_message = None  # Reset the previous message variable
        previous_reply_markup = None  # Reset the previous message's reply markup variable

@dp.callback_query_handler(lambda c: c.data == "change_role", state="*")
async def change_role_button_click(call: types.CallbackQuery):
    global previous_message, previous_reply_markup, set_role_user_id
    keyboard = types.InlineKeyboardMarkup(row_width=1)
    set_role_1 = types.InlineKeyboardButton(text="🤖 Обычный клиент", callback_data="set_role_1")
    set_role_2 = types.InlineKeyboardButton(text="💸 Потенциальный покупатель", callback_data="set_role_2")
    set_role_3 = types.InlineKeyboardButton(text="💳 Купивший", callback_data="set_role_3")
    back_button = types.InlineKeyboardButton(text="⬅️ Назад", callback_data="back_button")  # Added back button
    keyboard.add(set_role_1, set_role_2, set_role_3, back_button)  # Added back button to the keyboard

    message_text = call.message.text  # Get the message text
    match = re.search(r"Айди пользователя:\s(\d+)", message_text)  # Search for the user ID pattern

    if match:
        user_id_string = match.group(1)  # Extract the user ID string from the match
        set_role_user_id = int(user_id_string)  # Convert the user ID string to an integer
        print(set_role_user_id)
    else:
        print("User ID not found in the message text")

    previous_message = call.message  # Store the previous message
    previous_reply_markup = call.message.reply_markup  # Store the previous message's reply markup
    await call.message.edit_text("🕵️‍♂️ Выберите статус:", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == "back", state="*")
async def back(call: types.CallbackQuery, state: FSMContext):
    await state.finish()

    keyboard = types.InlineKeyboardMarkup()
    add = types.InlineKeyboardButton(text="➕ Добавить", callback_data="add_template")
    delete = types.InlineKeyboardButton(text="🗑 Удалить", callback_data="delete_template")
    keyboard.add(add, delete)

    await call.message.edit_text("<b>Вы вернулись назад.</b>", reply_markup=keyboard)

@dp.callback_query_handler(lambda c: c.data == "set_role_1", state="*")
async def set_role_1_button_click(call: types.CallbackQuery):
    global set_role_user_id
    user_id = set_role_user_id
    new_role = "Default"

    print(user_id)

    # Update the user's role in the database
    cursor.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    conn.commit()

    set_role_user_id = None

    await call.answer("Статус изменен на: Обычный клиент")

@dp.callback_query_handler(lambda c: c.data == "set_role_2", state="*")
async def set_role_2_button_click(call: types.CallbackQuery):
    global set_role_user_id
    user_id = set_role_user_id
    new_role = "Want Client"

    # Update the user's role in the database
    cursor.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    conn.commit()

    set_role_user_id = None

    await call.answer("Статус изменен на: Потенциальный клиент")

@dp.callback_query_handler(lambda c: c.data == "set_role_3", state="*")
async def set_role_3_button_click(call: types.CallbackQuery):
    global set_role_user_id
    user_id = set_role_user_id
    new_role = "Buy Client"

    # Update the user's role in the database
    cursor.execute("UPDATE users SET role = ? WHERE id = ?", (new_role, user_id))
    conn.commit()

    set_role_user_id = 0

    await call.answer("Статус изменен на: Купивший")

@dp.message_handler(content_types=types.ContentTypes.TEXT)
async def echo(message: types.Message):
    user_id = message.from_user.id
    user_un = message.from_user.username
    if user_un is None:
        user_un = message.from_user.first_name

    # Query the database to retrieve the user's role
    cursor.execute("SELECT role FROM users WHERE id = ?", (user_id,))
    result = cursor.fetchone()
    if result:
        role = result[0]
    else:
        role = "Unknown"

    string_role = ""

    if role == "Default":
        string_role = "Обычный клиент 🤖"
    elif role == "Want Client":
        string_role = "Потенциальный покупатель 💸"
    elif role == "Buy Client":
        string_role = "Купивший 💳"

    if message.reply_to_message:
        if user_id == int(admin):
            user_message_id = message.reply_to_message.message_id
            if user_message_id not in admin_replies:
                admin_replies[user_message_id] = [message.message_id]
                print("добавлено сообщ в список 2 | " + str(user_message_id) + ":" + str(message.message_id))
            else:
                admin_replies[user_message_id].append(message.message_id)
                print("добавлено сообщ в список 2 | " + str(user_message_id) + ":" + str(message.message_id))

    keyboard = types.InlineKeyboardMarkup(row_width=5)
    row = []
    try:
        for template in db.get_templates():
            template_btn = types.InlineKeyboardButton(text=template, callback_data=f"send_{template}_{user_id}")
            row.append(template_btn)
        keyboard.add(*row)
        delete_message_button = types.InlineKeyboardButton(text="Удалить это сообщение ✂️", callback_data="delete_message")
        keyboard.add(delete_message_button)
        add = types.InlineKeyboardButton(text="Изменить статус ✨", callback_data="change_role")
        keyboard.add(add)
    except:
        pass

    if message.reply_to_message:
        if user_id == int(admin):
            user_id_to = message.reply_to_message.text.split("\n")[-1][len("Айди пользователя: "):]


            await bot.send_message(text=message.text, chat_id=user_id_to)
        else:
            await bot.send_message(text=f"📧 <b>Новое сообщение</b>\n\n"
                                        f"<code>{message.text}</code>\n\n"
                                        f"<b>От: <a href='tg://user?id={user_id}'>{user_un}</a></b>\n"
                                        f"<b>Статус пользователя</b> {string_role}\n"
                                        f"<b>Айди пользователя:</b> <code>{user_id}</code>", reply_markup=keyboard, chat_id=admin)
    else:
        await bot.send_message(text=f"📧 <b>Новое сообщение</b>\n\n"
                                        f"<code>{message.text}</code>\n\n"
                                        f"<b>От: <a href='tg://user?id={user_id}'>{user_un}</a></b>\n"
                                        f"<b>Статус пользователя</b> {string_role}\n"
                                        f"<b>Айди пользователя:</b> <code>{user_id}</code>", reply_markup=keyboard, chat_id=admin)

async def on_startup(dispatcher):
    create_db()
    
if __name__ == '__main__':
    executor.start_polling(dp, on_startup=on_startup, skip_updates=True)