from aiogram import types
from aiogram.utils import keyboard

tasker_kb = keyboard.InlineKeyboardBuilder(
    markup=[
        [keyboard.InlineKeyboardButton(text="Открыть Таскер", url="https://crodconnect.ddns.net/tasker")]
    ]
)

kb_hello = {
    'children': keyboard.InlineKeyboardBuilder(
        markup=[
            [keyboard.InlineKeyboardButton(
                text="Вперёд! 🔥",
                callback_data="234234"
            )]

        ]
    ),
    'mentors': keyboard.InlineKeyboardBuilder(
        markup=[
            [keyboard.InlineKeyboardButton(
                text="Начать 🏃‍♂️",
                callback_data="4324324"
            )]

        ]
    ),
    'teachers': keyboard.InlineKeyboardBuilder(
        markup=[
            [keyboard.InlineKeyboardButton(
                text="Начать 🧑‍🏫",
                callback_data="324234"
            )],

        ]
    ),
    'admins': keyboard.InlineKeyboardBuilder(
        markup=[
            [keyboard.InlineKeyboardButton(
                text="Начать 🧑‍💻",
                callback_data="23423432432"
            )]
        ]
    ),
}

kb_main = {
    'children': keyboard.InlineKeyboardBuilder(
        markup=[
            [keyboard.InlineKeyboardButton(text="Образовательные модули 💡", callback_data="children_modules")],
            [keyboard.InlineKeyboardButton(text="Обратная связь 💬", callback_data="children_feedback")],
            [keyboard.InlineKeyboardButton(text="Радио 📻", callback_data="children_radio")],
        ]
    ),
    'mentors': keyboard.InlineKeyboardBuilder(
        markup=[
            [keyboard.InlineKeyboardButton(text="Список группы 📋", callback_data="mentors_grouplist")],
            [keyboard.InlineKeyboardButton(text="Обратная связь 💬", callback_data="mentors_feedback")],
            [keyboard.InlineKeyboardButton(text="QR-коды #️⃣", callback_data="mentors_qrs")],
            [keyboard.InlineKeyboardButton(text="Дни рождения 🎂", callback_data="mentors_births")],
        ]
    ),
    'teachers': keyboard.InlineKeyboardBuilder(
        markup=[
            [keyboard.InlineKeyboardButton(text="Список группы 📋", callback_data="teachers_grouplist")],
            [keyboard.InlineKeyboardButton(text="Обратная связь 💬", callback_data="teachers_feedback")],
        ]
    ),
    'admins': keyboard.InlineKeyboardBuilder(
        markup=[
            [keyboard.InlineKeyboardButton(text="Обратная связь 💬", callback_data="admins_feedback")],
            [keyboard.InlineKeyboardButton(text="Статистика 🎂", callback_data="admins_statistics")],
        ]
    ),
    None: None
}
