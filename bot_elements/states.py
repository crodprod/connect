from aiogram.fsm.state import StatesGroup, State


class Feedback(StatesGroup):
    feedback_text = State()
    callback = State()


class Radio(StatesGroup):
    request_text = State()
