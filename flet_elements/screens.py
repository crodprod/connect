from flet import icons, ScrollMode

screens = {
    "main": {
        "title": "Главная",
        "lead_icon": icons.LOGOUT_ROUNDED,
        "target": "login",
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
