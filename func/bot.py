from random import randrange
import datetime
from datetime import date

import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType

token = input('Token: ')

vk = vk_api.VkApi(token=token)
longpoll = VkLongPoll(vk)


def write_msg(user_id, message):
    vk.method('messages.send', {'user_id': user_id, 'message': message, 'random_id': randrange(10 ** 7), })


def get_user_info(user_id):
    user_info = vk.method("users.get", {"user_ids": [user_id], "fields": "bdate,sex,city"})
    return user_info


def calculate_age(born):
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


for event in longpoll.listen():
    if event.type == VkEventType.MESSAGE_NEW:

        if event.to_me:
            request = event.text

            if request == "Начать":
                write_msg(event.user_id, f"Хай, {event.user_id}")
                user_info = get_user_info(event.user_id)[0]
                city = user_info.get("city", {})
                sex = "мужской" if user_info.get("sex", 0) == 1 else "женский"
                born = datetime.datetime.strptime(user_info.get("bdate", ""), "%d.%m.%Y")
                age = calculate_age(born)
                write_msg(event.user_id, f"Выполнить поиск по следующим данным?:\n- г. "
                                         f"{city.get('title', '')}\n- {age} лет\n- пол {sex}")
            else:
                write_msg(event.user_id, "Для начала работы отправьте боту 'Начать'")
