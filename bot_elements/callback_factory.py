from typing import Optional
from aiogram.filters.callback_data import CallbackData


class TeachersCallbackFactory(CallbackData, prefix="teachers"):
    action: str


class MentorsCallbackFactory(CallbackData, prefix="mentors"):
    action: str
