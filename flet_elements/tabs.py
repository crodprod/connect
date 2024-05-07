from flet import icons, ScrollMode

menu_tabs_config = {
    0: {
        "index": "children",
        "title": "Информация о детях",
        'icon': icons.CHILD_CARE,
        'scroll': ScrollMode.HIDDEN
    },
    1: {
        "index": "modules",
        "title": "Учебные модули",
        'icon': icons.SCHOOL,
        'scroll': ScrollMode.ADAPTIVE
    },
    2: {
        "index": "mentors",
        "title": "Состав",
        'icon': icons.PEOPLE_ALT,
        'scroll': ScrollMode.ADAPTIVE
    },
    3: {
        "index": "docs",
        "title": "Документы",
        'icon': icons.TEXT_SNIPPET,
        'scroll': ScrollMode.ADAPTIVE
    },
    4: {
        "index": "settings",
        "title": "Настройки",
        'icon': icons.SETTINGS,
        'scroll': ScrollMode.ADAPTIVE
    },
}
