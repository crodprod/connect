from typing import Optional
from aiogram.filters.callback_data import CallbackData


class TeachersCallbackFactory(CallbackData, prefix="teachers"):
    action: str


class MentorsCallbackFactory(CallbackData, prefix="mentors"):
    action: str


class ChildrenCallbackFactory(CallbackData, prefix="children"):
    action: str


class AdminsCallbackFactory(CallbackData, prefix="admins"):
    action: str


class RadioRequestCallbackFactory(CallbackData, prefix="radio"):
    child_id: int
    action: str


class FeedbackMarkCallbackFactory(CallbackData, prefix="mark"):
    child_id: int
    mark: int


class SelectModuleCallbackFactory(CallbackData, prefix="selmodule"):
    module_id: int
    name: str


class RecordModuleToChildCallbackFactory(CallbackData, prefix="recordmodule"):
    child_id: int
    module_id: int

