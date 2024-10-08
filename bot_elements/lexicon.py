from aiogram.utils import markdown

base_crod_url = "https://crodconnect.ru"

lexicon = {
    'hello_messages': {
        'children': "<b>Приветствуем тебя в Центре развития одарённых детей!</b>"
                    "\n\n<b>Твои данные</b>"
                    "\n{0}"
                    "\nГруппа №{1}"
                    "\n\n<b>Твои воспитатели</b>"
                    "\n{2}",
        'mentors': "<b>Приветствуем вас в Центре развития одарённых детей. "
                   "Вы успешно зарегистрированы в качестве воспитателя!</b>"
                   "\n\n<b>Ваши данные</b>"
                   "\n{0}"
                   "\nГруппа №{1}"
                   "\nКоличество детей: {2}"
                   "\n\n<b>Напарники</b>"
                   "\n{3}",
        'teachers': "<b>Приветствуем вас в Центре развития одарённых детей. "
                    "Вы успешно зарегистрированы в качестве преподавателя!</b>"
                    "\n\n<b>Ваши данные</b>"
                    "\n{0}"
                    "\nМодуль: {1}"
                    "\nЛокация: {2}"
                    "\n\n<b>По всем вопросам обращайтесь к администрации</b>",
        'admins': "<b>Вы успешно зарегистрированы в качестве администратора!</b>"
                  "\n\n<b>Ваши данные</b>"
                  "\n{0}"
                  "\nПароль для Connect: {1}"
    },
    'callback_alerts': {
        'mentor_access_denied': "⛔ Действие недоступно, так как на данный момент вы не являетесь воспитателем",
        'teacher_access_denied': "⛔ Действие недоступно, так как на данный момент вы не являетесь преподавателем",
        'child_access_denied': "⛔ Ты не можешь пользоваться ботом, потому что не находишься в ЦРОДе",
        'access_denied': "⛔ Действие недоступно",
        'mentor_fback_stat': "Статистика за {0}\nОтправлено {1} из {2}",
        'no_births_group': "В вашей группе никто не будет праздновать день рождения.",
        'no_parts_in_module': "На ваш модуль пока никто не записался, попробуйте позже.",
        'no_fback_teacher': "Обратной связи за сегодняшний день ещё нет, попробуйте позже.",
        'no_module_record': "Запись на образователи модули пока закрыта, как только она начнётся, мы пришлём тебе сообщение.",
        'no_fback_child': "Сейчас мы не собираем обратную связь, но как только начнём, обязатаельно пришлём тебе сообщение.",
        'radio_request_already': "У тебя уже есть активная заявка на радио. Подожди, пока мы её обработаем, чтобы отправить новую.",
        'no_radio': "Сейчас наше радио не работает, как только мы будем в эфире, тебе придёт уведомление."
    }
}
