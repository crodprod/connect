from aiogram.utils import keyboard

from bot_elements.callback_factory import TeachersCallbackFactory, MentorsCallbackFactory

builder_teachers = keyboard.InlineKeyboardBuilder()
builder_teachers.button(text="Список группы 📋", callback_data=TeachersCallbackFactory(action="grouplist"))
builder_teachers.button(text="Обратная связь 💬", callback_data=TeachersCallbackFactory(action="feedback"))
builder_teachers.adjust(1)

builder_mentors = keyboard.InlineKeyboardBuilder()
builder_mentors.button(text="Список группы 📋", callback_data=MentorsCallbackFactory(action="grouplist"))
builder_mentors.button(text="Обратная связь 💬", callback_data=MentorsCallbackFactory(action="feedback"))
builder_mentors.button(text="QR-коды #️⃣", callback_data=MentorsCallbackFactory(action="qrs"))
builder_mentors.button(text="Дни рождения 🎂", callback_data=MentorsCallbackFactory(action="births"))
builder_mentors.adjust(1)