from flet import icons, ScrollMode

screens = {
    "main": {
        "title": "Коннект",
        "lead_icon": None,
        "target": None,
        'scroll': ScrollMode.HIDDEN

    },
    "children": {
        "title": "Информация о детях",
        "lead_icon": icons.ARROW_BACK,
        "target": "main",
        'scroll': ScrollMode.HIDDEN

    },
    "modules": {
        "title": "Учебные модули",
        "lead_icon": icons.ARROW_BACK,
        "target": "main",
        'scroll': ScrollMode.HIDDEN

    },
    "mentors": {
        "title": "Состав",
        "lead_icon": icons.ARROW_BACK,
        "target": "main",
        'scroll': ScrollMode.HIDDEN

    },
    "docs": {
        "title": "Документы",
        "lead_icon": icons.ARROW_BACK,
        "target": "main",
        'scroll': ScrollMode.HIDDEN

    },
    "settings": {
        "title": "Настройки",
        "lead_icon": icons.ARROW_BACK,
        "target": "main",
        'scroll': ScrollMode.HIDDEN

    },
    "reboot": {
        "title": "Перезагрузка",
        "lead_icon": icons.ARROW_BACK,
        "target": "settings",
        'scroll': ScrollMode.HIDDEN

    },
    "login": {
        "title": "Авторизация",
        "lead_icon": None,
        "target": "",
        'scroll': None
    },
    "add_module": {
        "title": "Новый модуль",
        "lead_icon": icons.ARROW_BACK,
        "target": "modules",
        'scroll': None
    },
    "add_mentor": {
        "title": "Новый воспитатель",
        "lead_icon": icons.ARROW_BACK,
        "target": "mentors_info",
        'scroll': None
    },
    "add_admin": {
        "title": "Новый администратор",
        "lead_icon": icons.ARROW_BACK,
        "target": "mentors",
        'scroll': None
    },
    "mentors_info": {
        "title": "Воспитатели",
        "lead_icon": icons.ARROW_BACK,
        "target": "mentors",
        'scroll': ScrollMode.HIDDEN
    },
    "admins_info": {
        "title": "Администраторы",
        "lead_icon": icons.ARROW_BACK,
        "target": "mentors",
        'scroll': ScrollMode.HIDDEN
    },
    "info": {
        "title": "О приложении",
        "lead_icon": icons.ARROW_BACK,
        "target": "settings",
        'scroll': None
    },
    "showqr": {
        "title": "QR-коды",
        "lead_icon": None,
        "target": "",
        'scroll': ScrollMode.HIDDEN

    },
    "modulecheck": {
        "title": "Посещаемость",
        "lead_icon": None,
        "target": "",
        'scroll': ScrollMode.HIDDEN
    }
}
