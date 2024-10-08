import datetime
import re
import time

from flet import *
from flet_elements.modules_locations import locations

months = {
    1: "января",
    2: "февраля",
    3: "марта",
    4: "апреля",
    5: "мая",
    6: "июня",
    7: "июля",
    8: "августа",
    9: "сентября",
    10: "октября",
    11: "ноября",
    12: "декабря",
}


class NewModule:
    def __init__(self, page: Page, save_btn):
        self.page = page
        self.btn = save_btn
        self.module_name = TextField(
            label="Название",
            prefix_icon=icons.SCHOOL,
            hint_text="Программирование на Python",
            on_change=lambda _: self.validate()
        )
        self.locations_dropdown = Dropdown(
            label="Локация",
            prefix_icon=icons.LOCATION_ON,
            options=[dropdown.Option(key=loc, text=loc) for loc in locations],
            on_change=lambda _: self.validate()
        )
        self.seats_count = TextField(
            label="Количество мест",
            hint_text="15",
            prefix_icon=icons.EVENT_SEAT,
            on_change=lambda _: self.validate()
        )
        self.teacher_name = TextField(
            label="ФИО преподавателя",
            prefix_icon=icons.ACCOUNT_CIRCLE,
            hint_text="Иванов Иван Иванович",
            on_change=lambda _: self.validate()
        )

    def validate(self):
        if len(self.teacher_name.value.strip().split()) in [2, 3] and self.locations_dropdown.value != "" and \
                self.seats_count.value.isnumeric() and self.module_name.value:
            self.btn.disabled = False
        else:
            self.btn.disabled = True

        self.page.update()

    def reset(self):
        self.module_name.value = ""
        self.locations_dropdown.value = ""
        self.seats_count.value = ""
        self.teacher_name.value = ""
        self.btn.disabled = True

        self.page.update()


class NewAdmin:
    def __init__(self, page: Page, save_btn):
        self.page = page
        self.btn = save_btn
        self.name = TextField(
            label="ФИО",
            prefix_icon=icons.ACCOUNT_CIRCLE,
            hint_text="Иванов Иван Иванович",
            on_change=lambda _: self.validate()
        )
        self.post = TextField(
            label="Должность",
            prefix_icon=icons.WORK,
            hint_text="Координатор смены",
            on_change=lambda _: self.validate()
        )
        self.panel_access = Checkbox(value=True)

    def validate(self):
        if len(self.name.value.strip().split(" ")) in [2, 3] and self.post.value:
            self.btn.disabled = False
        else:
            self.btn.disabled = True

        self.page.update()

    def reset(self):
        self.name.value = ""
        self.post.value = ""
        self.panel_access.value = True
        self.btn.disabled = True

        self.page.update()


class NewMentor:
    def __init__(self, page: Page, save_btn):
        self.page = page
        self.btn = save_btn
        self.name = TextField(
            label="ФИО",
            prefix_icon=icons.ACCOUNT_CIRCLE,
            hint_text="Иванов Иван Иванович",
            on_change=lambda _: self.validate()
        )
        self.group = Dropdown(
            label="Номер группы",
            prefix_icon=icons.GROUP,
            options=[dropdown.Option(key=str(a), text=str(a)) for a in range(1, 6)],
            on_change=lambda _: self.validate()
        )

    def validate(self):
        if len(self.name.value.strip().split(" ")) in [2, 3] and self.group.value != "":
            self.btn.disabled = False
        else:
            self.btn.disabled = True

        self.page.update()

    def reset(self):
        self.name.value = ""
        self.group.value = ""
        self.btn.disabled = True

        self.page.update()


class NewChild:
    def __init__(self, page: Page, save_btn):
        self.page = page
        self.btn = save_btn
        self.name = TextField(
            label="ФИО ребёнка",
            prefix_icon=icons.CHILD_CARE,
            hint_text="Иванов Иван Иванович",
            on_change=lambda _: self.validate()
        )
        self.birth_day = Dropdown(
            label="День",
            # prefix_icon=icons.CALENDAR_MONTH,
            # hint_text="10.10.2010",
            options=[dropdown.Option(text=str(i), key='0' * (2 - len(str(i))) + str(i)) for i in range(1, 32)],
            on_change=lambda _: self.validate(),
            width=100
        )
        self.birth_month = Dropdown(
            label="Месяц",
            # prefix_icon=icons.CALENDAR_MONTH,
            # hint_text="10.10.2010",
            options=[dropdown.Option(text=months[i], key=i) for i in months.keys()],
            on_change=lambda _: self.validate(),
            width=110
        )
        self.birth_year = Dropdown(
            label="Год",
            # prefix_icon=icons.CALENDAR_MONTH,
            # hint_text="10.10.2010",
            options=[dropdown.Option(text=str(i), key=str(i)) for i in range(datetime.datetime.now().year - 18, datetime.datetime.now().year)],
            on_change=lambda _: self.validate(),
            width=110
        )
        self.caption = TextField(
            label="Особенности",
            prefix_icon=icons.NOTES,
            multiline=True,
            hint_text="Аллергися на цитрусовые",
            on_change=lambda _: self.validate()
        )
        self.parent_name = TextField(
            label="ФИО родителя",
            prefix_icon=icons.ACCOUNT_CIRCLE,
            hint_text="Иванов Иван Иванович",
            on_change=lambda _: self.validate()
        )
        self.phone = TextField(
            label="Телефон родителя",
            prefix_icon=icons.PHONE,
            prefix_text="+7",
            on_change=lambda _: self.validate()
        )
        self.group = Dropdown(
            label="Номер группы",
            prefix_icon=icons.GROUP,
            options=[dropdown.Option(key=str(a), text=str(a)) for a in range(1, 6)],
            on_change=lambda _: self.validate()
        )

    def validate(self):
        print(self.birth_day.value)
        if all([
            len(self.name.value.strip().split(" ")) in [2, 3],
            len(self.parent_name.value.strip().split(" ")) in [2, 3]
        ]) and self.group.value != "" and self.phone.value.isnumeric() and len(self.phone.value) == 10 and all([self.birth_day.value, self.birth_month.value, self.birth_year.value]):
            self.btn.disabled = False
        else:
            self.btn.disabled = True

        self.page.update()

    def reset(self):
        self.name.value = ""
        self.group.value = ""
        self.parent_name.value = ""
        self.phone.value = ""
        self.caption.value = ""
        self.btn.disabled = True

        self.page.update()


class ConfirmationCodeField:
    def __init__(self, page: Page, true_password, func):
        self.page = page
        self.user_input = None
        self.true_password = str(true_password)
        self.is_correct = None
        self.func = func
        self.password_row = Row(
            controls=[
                TextField(
                    border="underline",
                    cursor_height=0,
                    text_style=TextStyle(weight=FontWeight.W_600),
                    text_size=20,
                    keyboard_type=KeyboardType.NUMBER,
                    text_align=TextAlign.CENTER,
                    width=45,
                    on_change=self.go_to_next_field,
                    data={'num': i}
                ) for i in range(6)
            ],
            alignment=MainAxisAlignment.CENTER
        )

    def go_to_next_field(self, e: ControlEvent):
        if e.control.value == "":
            new_index = e.control.data['num'] - 1
        else:
            new_index = e.control.data['num'] + 1
        if new_index == 6 and self.password_row.controls[-1] != "":
            self.user_input = ''.join([self.password_row.controls[i].value for i in range(6)])
            self.check_input()

        elif 0 <= new_index <= 5:
            self.password_row.controls[new_index].focus()
            self.page.update()

    def check_input(self):
        self.is_correct = self.true_password == self.user_input
        if self.true_password == self.user_input:
            self.func()
        else:
            self.set_color(colors.RED, all=True)
            time.sleep(1)
            self.set_color(colors.TRANSPARENT, all=True)
            self.clear()

    def set_color(self, color: colors, all: bool = False):
        for i in range(6):
            self.password_row.controls[i].bgcolor = color
            if not all:
                self.page.update()
                time.sleep(0.05)
        self.page.update()

    def clear(self):
        for i in range(6):
            self.password_row.controls[i].value = None
        self.password_row.controls[0].focus()
        self.page.update()

    def create(self, target):
        target.controls.append(Container(self.password_row))
        # self.password_row.controls[0].focus()
        self.page.update()


class ExtraUsers:
    def __init__(self, page: Page):
        self.page = page
        self.users_col = Column(width=600)
        self.btn_add_user = IconButton(icons.ADD, on_click=lambda _: self.add_user())
        self.btn_continue = FilledTonalButton(text="Создать", on_click=lambda _: self.add_user())

    def add_user(self):
        self.users_col.controls.pop()
        self.users_col.controls.append(TextField(label="Имя", data={'field_type': 'name'}))
        self.users_col.controls.append(TextField(label="Должность", data={'field_type': 'name'}))
        self.users_col.controls.append(Divider(thickness=1))
        self.add_btns()
        self.page.update()

    def add_btns(self):
        self.users_col.controls.append(Row([self.btn_add_user, self.btn_continue], alignment=MainAxisAlignment.END))

    def clear(self):
        self.users_col.controls = [Divider()]
        self.page.update()
