from flet import icons, ScrollMode

menu_icon = icons.MENU
back_icon = icons.ARROW_BACK_ROUNDED
base_scroll_mode = ScrollMode.AUTO

screens = {
    'login': {
        'appbar': {
            'visible': False,
            'leading': {
                'icon': menu_icon,
                'action': "change_screen",  # или "drawer"
                'target': 'main'  # если change_screen, то указание экрана перехода
            },
            'title': "Авторизация"
        },
        'scroll_mode': None
    },
    'main': {
        'appbar': {
            'visible': True,
            'leading': {
                'icon': menu_icon,
                'action': "drawer",
                'target': None
            },
            'title': "Главная"
        },
        'scroll_mode': base_scroll_mode
    },
    'edit_child_group_num': {
        'appbar': {
            'visible': True,
            'leading': {
                'icon': menu_icon,
                'action': "drawer",
                'target': None
            },
            'title': "Изменение группы"
        },
        'scroll_mode': base_scroll_mode
    },
    'add_child': {
        'appbar': {
            'visible': True,
            'leading': {
                'icon': menu_icon,
                'action': "drawer",
                'target': None
            },
            'title': "Добавление ребёнка"
        },
        'scroll_mode': None
    },
    'modules_info': {
        'appbar': {
            'visible': True,
            'leading': {
                'icon': menu_icon,
                'action': "drawer",
                'target': None
            },
            'title': "Учебные модули"
        },
        'scroll_mode': base_scroll_mode
    },
    'create_module': {
        'appbar': {
            'visible': True,
            'leading': {
                'icon': back_icon,
                'action': "change_screen",
                'target': 'modules_info'
            },
            'title': "Создание модуля"
        },
        'scroll_mode': base_scroll_mode
    },
    'mentors_info': {
        'appbar': {
            'visible': True,
            'leading': {
                'icon': menu_icon,
                'action': "drawer",
                'target': None
            },
            'title': "Воспитатели"
        },
        'scroll_mode': base_scroll_mode
    },
    'admins_info': {
        'appbar': {
            'visible': True,
            'leading': {
                'icon': menu_icon,
                'action': "drawer",
                'target': None
            },
            'title': "Администраторы"
        },
        'scroll_mode': base_scroll_mode
    },
    'create_admin': {
        'appbar': {
            'visible': True,
            'leading': {
                'icon': back_icon,
                'action': "change_screen",
                'target': 'admins_info'
            },
            'title': "Новый администратор"
        },
        'scroll_mode': base_scroll_mode
    },
    'create_mentor': {
        'appbar': {
            'visible': True,
            'leading': {
                'icon': back_icon,
                'action': "change_screen",
                'target': 'mentors_info'
            },
            'title': "Новый воспитатель"
        },
        'scroll_mode': base_scroll_mode
    },
    'documents': {
        'appbar': {
            'visible': True,
            'leading': {
                'icon': menu_icon,
                'action': "drawer",
                'target': None
            },
            'title': "Документы"
        },
        'scroll_mode': base_scroll_mode
    },
    'reboot_menu': {
        'appbar': {
            'visible': True,
            'leading': {
                'icon': menu_icon,
                'action': "drawer",
                'target': None
            },
            'title': "Состояние системы"
        },
        'scroll_mode': base_scroll_mode
    },
    'app_info': {
        'appbar': {
            'visible': True,
            'leading': {
                'icon': menu_icon,
                'action': "drawer",
                'target': None
            },
            'title': "О приложении"
        },
        'scroll_mode': None
    },
    'edit_env': {
        'appbar': {
            'visible': True,
            'leading': {
                'icon': menu_icon,
                'action': "drawer",
                'target': None
            },
            'title': "Конфигурация"
        },
        'scroll_mode': base_scroll_mode
    },
    'select_qr_group': {
        'appbar': {
            'visible': True,
            'leading': {
                'icon': menu_icon,
                'action': "drawer",
                'target': None
            },
            'title': "QR-коды"
        },
        'scroll_mode': base_scroll_mode
    },
    'errors': {
        'appbar': {
            'visible': False,
            'leading': {
                'icon': menu_icon,
                'action': "drawer",
                'target': None
            },
            'title': "QR-коды"
        },
        'scroll_mode': None
    },
}
