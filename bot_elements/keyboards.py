import os

from dotenv import load_dotenv
from aiogram.utils import keyboard
from bot_elements.lexicon import base_crod_url
from bot_elements.keyboard_builders import builder_teachers, builder_mentors, builder_children, builder_admins

load_dotenv()

tasker_kb = keyboard.InlineKeyboardBuilder(
    markup=[
        [keyboard.InlineKeyboardButton(text="Открыть Таскер 🗒️", url=f"{base_crod_url}/tasker")]
    ]
)

reboot_bot_kb = keyboard.InlineKeyboardBuilder(
    markup=[
        [keyboard.InlineKeyboardButton(text="Перезагрузить ⚡", callback_data="rebootbot")]
    ]
)

radio_kb = keyboard.InlineKeyboardBuilder(
    markup=[
        [keyboard.InlineKeyboardButton(text="🟢 Запустить", callback_data="radio_on")],
        [keyboard.InlineKeyboardButton(text="🔴 Остановить", callback_data="radio_off")]
    ]
)

check_apply_to_channel_kb = keyboard.InlineKeyboardBuilder(
    markup=[
        [keyboard.InlineKeyboardButton(text="Подписаться", url=f"https://t.me/{os.getenv('ID_CHANNEL')}")],
        [keyboard.InlineKeyboardButton(text="✅ Я подписался (-ась)!", callback_data="check_apply")]
    ]
)

kb_hello = {
    'children': keyboard.InlineKeyboardBuilder(
        markup=[
            [keyboard.InlineKeyboardButton(
                text="Главное меню 🔥",
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
            [
                keyboard.InlineKeyboardButton(
                    text="Главное меню 🧑‍💻",
                    callback_data="firststart"
                ),
                keyboard.InlineKeyboardButton(
                    text="Открыть Коннект",
                    url=f"{base_crod_url}/connect"
                )
            ]
        ]
    ),
}

kb_main = {
    'children': builder_children,
    'mentors': builder_mentors,
    'teachers': builder_teachers,
    'admins': builder_admins
}
