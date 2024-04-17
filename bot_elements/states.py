from aiogram.fsm.state import StatesGroup, State


class Feedback(StatesGroup):
    feedback_text = State()
    feedback_mark = State()


class Radio(StatesGroup):
    request_text = State()
