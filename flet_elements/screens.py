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
    "settings": {
        "title": "Настройки",
        "lead_icon": icons.ARROW_BACK,
        "target": "main",
        'scroll': ScrollMode.HIDDEN

    },
    "login": {
        "title": "Авторизация",
        "lead_icon": None,
        "target": "",
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
