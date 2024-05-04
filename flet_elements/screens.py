from flet import icons

screens = {
    "main": {
        "title": "Главная",
        "lead_icon": icons.LOGOUT_ROUNDED,
        "target": "login"

    },
    "login": {
        "title": "Авторизация",
        "lead_icon": None,
        "target": ""
    },
    "import_themes": {
        "title": "Импорт тем",
        "lead_icon": icons.ARROW_BACK_ROUNDED,
        "target": "main"

    },
    "add_jury": {
        "title": "Новое жюри",
        "lead_icon": icons.ARROW_BACK_ROUNDED,
        "target": "main"
    },
    "view_group": {
        'title': "Обзор группы",
        "lead_icon": icons.ARROW_BACK_ROUNDED,
        "target": "main"
    }
}
