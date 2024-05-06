from flet import icons, ScrollMode, Icon, FilledTonalButton

menu_tabs_config = {
    0: {
        "index": "children",
        "title": "Информация о детях",
        'icon': icons.CHILD_CARE,
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
        "index": "modules",
        "title": "Учебные модули",
        'icon': icons.SCHOOL,
        'scroll': ScrollMode.ADAPTIVE,
        'fab': {
            'status': True,
            'icon': icons.MENU,
            'target_screen': '...'
        },
        'actions': None
    },
    2: {
        "index": "mentors",
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
    3: {
        "index": "settings",
        "title": "Настройки",
        'icon': icons.SETTINGS,
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
