from flet import icons, ScrollMode, Icon, FilledTonalButton

tabs_config = {
    0: {
        "index": "settings",
        "title": "Главная",
        'icon': icons.HOME,
        'scroll': ScrollMode.HIDDEN,
        'fab': {
            'status': True,
            'icon': icons.MENU,
            'target_screen': '...'
        },
        'actions': [
            FilledTonalButton(content=Icon(icons.LOCK))
        ]
    },
    1: {
        "index": "children",
        "title": "Дети",
        'icon': icons.CHILD_CARE,
        'scroll': ScrollMode.ADAPTIVE,
        'fab': {
            'status': True,
            'icon': icons.MENU,
            'target_screen': '...'
        },
        'actions': None
    },
    2: {
        "index": "modules",
        "title": "Модули",
        'icon': icons.SCHOOL,
        'scroll': ScrollMode.ADAPTIVE,
        'fab': {
            'status': True,
            'icon': icons.MENU,
            'target_screen': '...'
        },
        'actions': [
            FilledTonalButton(content=Icon(icons.ADD))
        ]
    },
    3: {
        "index": "admins",
        "title": "Состав",
        'icon': icons.PEOPLE_ALT,
        'scroll': ScrollMode.ADAPTIVE,
        'fab': {
            'status': True,
            'icon': icons.MENU,
            'target_screen': '...'
        },
        'actions': [
            FilledTonalButton(content=Icon(icons.ADD))
        ]
    },
}
