from aiogram.utils import keyboard

from bot_elements.callback_factory import TeachersCallbackFactory, MentorsCallbackFactory, ChildrenCallbackFactory, AdminsCallbackFactory
from bot_elements.lexicon import base_crod_url

builder_teachers = keyboard.InlineKeyboardBuilder()
builder_teachers.button(text="Состав модуля 📋", callback_data=TeachersCallbackFactory(action="grouplist"))
builder_teachers.button(text="Обратная связь 💬", callback_data=TeachersCallbackFactory(action="feedback"))
builder_teachers.adjust(1)

builder_mentors = keyboard.InlineKeyboardBuilder()
builder_mentors.button(text="Список группы 📋", callback_data=MentorsCallbackFactory(action="grouplist"))
builder_mentors.button(text="QR-коды #️⃣", callback_data=MentorsCallbackFactory(action="qrc"))
builder_mentors.button(text="Списки модулей", callback_data=MentorsCallbackFactory(action="modules_list"))
builder_mentors.button(text="Посещаемость 💡", callback_data=MentorsCallbackFactory(action="traffic"))
builder_mentors.button(text="Дни рождения 🎂", callback_data=MentorsCallbackFactory(action="births"))
builder_mentors.button(text="Обратная связь 💬", callback_data=MentorsCallbackFactory(action="feedback"))
builder_mentors.adjust(2)

builder_children = keyboard.InlineKeyboardBuilder()
builder_children.button(text="Образовательные модули 💡", callback_data=ChildrenCallbackFactory(action="modules"))
builder_children.button(text="Радио 📻", callback_data=ChildrenCallbackFactory(action="radio"))
builder_children.button(text="Обратная связь 💬", callback_data=ChildrenCallbackFactory(action="feedback"))
builder_children.adjust(2)

builder_admins = keyboard.InlineKeyboardBuilder()
builder_admins.button(text="Документы 💬", callback_data=AdminsCallbackFactory(action="docs"))
builder_admins.button(text="Списки модулей", callback_data=AdminsCallbackFactory(action="modules_list"))
builder_admins.button(text="Открыть Connect 💡", url=f"{base_crod_url}/connect")
builder_mentors.button(text="QR-коды #️⃣", callback_data=AdminsCallbackFactory(action="qrc"))
# to-do
# выбор: генерация файла или открыть через connect
builder_admins.adjust(2)
