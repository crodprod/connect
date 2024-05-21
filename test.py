import asyncio
import datetime
import logging
import os
import platform
import re
import time

import requests
from aiogram import Bot, Dispatcher, types, F
from aiogram.filters.command import Command, CommandStart, CommandObject
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import StatesGroup, State
from aiogram.types import Message
from aiogram.utils import markdown, keyboard
from aiogram.methods import DeleteWebhook
from aiogram.utils.markdown import link
from apscheduler.schedulers.asyncio import AsyncIOScheduler

from dotenv import load_dotenv

from bot_elements.callback_factory import TeachersCallbackFactory, MentorsCallbackFactory, ChildrenCallbackFactory, RadioRequestCallbackFactory, SelectModuleCallbackFactory, AdminsCallbackFactory, \
    RecordModuleToChildCallbackFactory, FeedbackMarkCallbackFactory
from bot_elements.database import DataBase
from bot_elements.lexicon import lexicon, base_crod_url
from bot_elements.keyboards import kb_hello, kb_main, tasker_kb, reboot_bot_kb, radio_kb, check_apply_to_channel_kb
from bot_elements.states import Radio, Feedback
from functions import load_config_file, update_config_file
from wording.wording import get_grouplist, get_feedback

load_dotenv()

bot = Bot(token=os.getenv('BOT_TOKEN'), parse_mode="html")
dp = Dispatcher()

async def check():
    fl = False
    while not fl:
        print('getting')
        try:
            code = requests.get('https://dl.spbstu.ru').status_code
        except requests.exceptions.ConnectTimeout:
            code = 'Timeout'
        print('ok')
        print(code)
        if code == 200:
            await bot.send_message(
                chat_id=2048822830,
                text="Политех поднялся!!!!!!!!!!!!!!!!!1"
            )
        else:
            await bot.send_message(
                chat_id=2048822830,
                text="Политех откисает в канаве со статусом: " + str(code)
            )

        time.sleep(10)


async def main():
    await bot(DeleteWebhook(drop_pending_updates=True))
    await dp.start_polling(bot)


if __name__ == "__main__":
    asyncio.run(main())
