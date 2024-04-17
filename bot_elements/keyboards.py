from aiogram.utils import keyboard
from bot_elements.lexicon import base_crod_url
from bot_elements.keyboard_builders import builder_teachers, builder_mentors

tasker_kb = keyboard.InlineKeyboardBuilder(
    markup=[
        [keyboard.InlineKeyboardButton(text="Открыть Таскер 🗒️", url=f"{base_crod_url}/tasker")]
    ]
)

reboot_bot_kb = keyboard.InlineKeyboardBuilder(
    markup=[
        [keyboard.InlineKeyboardButton(text="Перезагрузить ⚡", callback_data="admins_rebootbot")]
    ]
)

radio_kb = keyboard.InlineKeyboardBuilder(
    markup=[
        [keyboard.InlineKeyboardButton(text="🟢 Запустить", callback_data="radio_on")],
        [keyboard.InlineKeyboardButton(text="🔴 Остановить", callback_data="radio_off")]
    ]
)

kb_hello = {
    'children': keyboard.InlineKeyboardBuilder(
        markup=[
            [keyboard.InlineKeyboardButton(
                text="Погнали! 🔥",
                callback_data="firststart"
            )]

        ]
    ),
    'mentors': keyboard.InlineKeyboardBuilder(
        markup=[
            [keyboard.InlineKeyboardButton(
                text="Главное меню 🏃‍♂️",
                callback_data="firststart"
            )]

        ]
    ),
    'teachers': keyboard.InlineKeyboardBuilder(
        markup=[
            [keyboard.InlineKeyboardButton(
                text="Главное меню 🧑‍🏫",
                callback_data="firststart"
            )],

        ]
    ),
    'admins': keyboard.InlineKeyboardBuilder(
        markup=[
            [keyboard.InlineKeyboardButton(
                text="Главное меню 🧑‍💻",
                callback_data="firststart"
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
    'mentors': builder_mentors,
    'teachers': builder_teachers,
    'admins': keyboard.InlineKeyboardBuilder(
        markup=[
            [keyboard.InlineKeyboardButton(text="Обратная связь 💬", callback_data="admins_feedback")],
            [keyboard.InlineKeyboardButton(text="Статистика 🎂", callback_data="admins_statistics")],
            [keyboard.InlineKeyboardButton(text="Открыть Connect", url=f"{base_crod_url}/connect")],
        ]
    ),
    None: None
}


