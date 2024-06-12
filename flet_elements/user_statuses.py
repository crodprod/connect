from flet import colors

user_statuses = {
    'waiting_for_registration': {
        'color': colors.AMBER,
        'naming': "Ожидание регистрации"
    },
    'active': {
        'color': colors.GREEN,
        'naming': "Зарегистрирован"
    },
    'frozen': {
        'color': colors.RED,
        'naming': "Отключен"
    }
}
