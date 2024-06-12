import re

from flet import *
from flet_elements.modules_locations import locations


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

    def validate(self):
        if len(self.name.value.strip().split(" ")) in [2, 3]:
            self.btn.disabled = False
        else:
            self.btn.disabled = True

        self.page.update()

    def reset(self):
        self.name.value = ""
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
        self.birth = TextField(
            label="Дата рождения",
            prefix_icon=icons.CALENDAR_MONTH,
            hint_text="10.10.2010",
            on_change=lambda _: self.validate()
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
        if all([
            len(self.name.value.strip().split(" ")) in [2, 3],
            len(self.parent_name.value.strip().split(" ")) in [2, 3]
        ]) and self.group.value != "" and self.phone.value.isnumeric() and len(self.phone.value) == 10 and re.match(r'^(0[1-9]|[12][0-9]|3[01])\.(0[1-9]|1[0-2])\.(19|20)\d{2}$', self.birth.value):
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
        self.birth.value = ""
        self.btn.disabled = True

        self.page.update()

