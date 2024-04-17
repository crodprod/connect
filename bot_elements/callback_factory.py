from typing import Optional
from aiogram.filters.callback_data import CallbackData


class TeachersCallbackFactory(CallbackData, prefix="teachers"):
    action: str


class MentorsCallbackFactory(CallbackData, prefix="mentors"):
    action: str


class ChildrenCallbackFactory(CallbackData, prefix="children"):
    action: str


class AdminsCallbackFactory(CallbackData, prefix="children"):
    action: str


class RadioRequestCallbackFactory(CallbackData, prefix="radio"):
    child_id: int
    action: str
