import yaml
import vk_api
from vk_api.longpoll import VkLongPoll, VkEventType
from random import randrange
import datetime
from datetime import date

with open("config.yaml") as c:
    config = yaml.full_load(c)

VK_USER_TOKEN = config["VK"]["USER_TOKEN"]
VK_VERSION = config["VK"]["VERSION"]
VK_APP_ID = config["VK"]["APP_ID"]
VK_GROUP_TOKEN = config["VK"]["GROUP_TOKEN"]


def calculate_age(born):
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


class VKClient(vk_api.VkApi):
    def write_msg(self, user_id, message, attachment=None):
        if attachment:
            self.method('messages.send', {'user_id': user_id, 'message': message,
                                          'attachment': attachment, 'random_id': randrange(10 ** 7), })
        else:
            self.method('messages.send', {'user_id': user_id, 'message': message, 'random_id': randrange(10 ** 7), })

    def get_user_info(self, user_ids, fields):
        user_info = self.method("users.get", {"user_ids": user_ids, "fields": fields})
        return user_info

    def search_users(self, fields):
        params = {
            "sort": 0,
            "offset": 0,
            "count": 10,
            "city": fields.get("city_id", 1),
            "sex": fields.get("sex", 1),
            "age_from": fields.get("age_from", 18),
            "age_to": fields.get("age_to", 99),
            "has_photo": 1
        }
        search_res = self.method("users.search", params)
        return search_res.get("items", [])

    def get_city_id(self, city_title):
        city = self.method("database.getCities", {"q": city_title, "need_all": 0})
        return city.get("items", [])[0]

    def get_top_photos(self, owner_id, count=3):
        album = self.method("photos.get", {"owner_id": owner_id, "album_id": "profile", "extended": 1})
        photos = []
        for item in album.get("items", []):
            url = item.get("sizes", [])[-1].get("url", "")
            likes = item.get("likes", {}).get("count", 0)
            entry = {"url": url, "likes": likes}
            photos.append(entry)

        result = sorted(photos, key=lambda x: x.get("likes", 0), reverse=True)
        return result[:count]


if __name__ == "__main__":
    # user_id = "73489272"
    # vk_user_client = VKClient(token=VK_USER_TOKEN, app_id=VK_APP_ID)
    # city_title = "Санкт-Петербург"
    # city_id = vk_user_client.get_city_id(city_title).get("id", 0)
    # print(city_id, city_title)
    # fields = {
    #     "city_id": city_id,
    #     "sex": 1,
    #     "age_from": 18,
    #     "age_to": 22
    # }
    # search_res = vk_user_client.search_users(fields)
    # print(search_res)
    # photos = vk_user_client.get_top_photos(search_res[1].get("id", 1))
    # print(photos)
    vk_group_client = VKClient(token=VK_GROUP_TOKEN)
    longpoll = VkLongPoll(vk_group_client)

    for event in longpoll.listen():
        if event.type == VkEventType.MESSAGE_NEW:

            if event.to_me:
                request = event.text

                if request == "Начать":
                    vk_group_client.write_msg(event.user_id, f"Хай, {event.user_id}")
                    user_info = vk_group_client.get_user_info(event.user_id, "bdate,sex,city")[0]
                    city = user_info.get("city", {})
                    sex = user_info.get("sex", 0)
                    born = datetime.datetime.strptime(user_info.get("bdate", ""), "%d.%m.%Y")
                    age = calculate_age(born)
                    vk_group_client.write_msg(event.user_id, f"Выполнить поиск по следующим данным?:\n- г. "
                                                             f"{city.get('title', '')}\n- {age} лет\n- пол "
                                                             f"{'мужской' if sex == 1 else 'женский'}")
                    for event in longpoll.listen():
                        if event.type == VkEventType.MESSAGE_NEW:
                            if event.to_me:
                                request = event.text

                                if request == "Да":
                                    vk_user_client = VKClient(token=VK_USER_TOKEN, app_id=VK_APP_ID)
                                    fields = {
                                        "city_id": city.get("id", 2),
                                        "sex": sex,
                                        "age_from": age,
                                        "age_to": age
                                    }
                                    search_res = vk_user_client.search_users(fields)
                                    photos = vk_user_client.get_top_photos(search_res[1].get("id", 1))

                                    vk_group_client.write_msg(event.user_id, f"{search_res[1].get('first_name', '')}"
                                                                             f" {search_res[1].get('last_name', '')}",
                                                              attachment=f"{photos[0].get('url', '')},"
                                                                         f"{photos[1].get('url', '')},"
                                                                         f"{photos[2].get('url', '')}")
                else:
                    vk_group_client.write_msg(event.user_id, "Для начала работы отправьте боту 'Начать'")
