import vk_api
from random import randrange
from datetime import date
import yaml
import datetime

with open("config.yaml") as c:
    config = yaml.full_load(c)

VK_USER_TOKEN = config["VK"]["USER_TOKEN"]
VK_VERSION = config["VK"]["VERSION"]
VK_APP_ID = config["VK"]["APP_ID"]
VK_GROUP_TOKEN = config["VK"]["GROUP_TOKEN"]

KB_MAIN = "func/keyboards/keyboard_main.json"
KB_CHOOSE = "func/keyboards/keyboard_choose.json"
KB_SEARCH = "func/keyboards/keyboard_search.json"
KB_EMPTY = "func/keyboards/keyboard_empty.json"


def calculate_age(born):
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def get_auth_link(app_id, scope, version):
    base_url = "https://oauth.vk.com/authorize"
    redirect_uri = "https://oauth.vk.com/blank.html"
    display = "page"
    response_type = "token"
    auth_url = (f"{base_url}?client_id={app_id}&display={display}&"
                f"redirect_uri={redirect_uri}&scope={scope}&"
                f"response_type={response_type}&v={version}")
    return auth_url


class VKClient(vk_api.VkApi):
    def set_token(self, token):
        self.token = token

    def write_msg(self, user_id, message, fields=None):
        values = {'user_id': user_id, 'message': message, 'random_id': randrange(10 ** 7)}
        if fields:
            self.method('messages.send', {**values, **fields})
        else:
            self.method('messages.send', values)

    def event_answer(self, event_id, user_id, peer_id):
        self.method("messages.sendMessageEventAnswer", {"event_id": event_id, "user_id": user_id,
                                                        "peer_id": peer_id})

    def get_user_info(self, user_ids, fields):
        user_info = self.method("users.get", {"user_ids": user_ids, "fields": fields})
        return user_info

    def search_users(self, fields):
        params = {
            "sort": 0,
            "offset": 0,
            "count": 100,
            **fields,
            "has_photo": 1
        }
        search_res = self.method("users.search", params)
        items = search_res.get("items", [])
        result = {item.get("id", 0): {"first_name": item.get("first_name", ""),
                                      "last_name": item.get("last_name", ""),
                                      "link": f"https://vk.com/id{item.get('id', 0)}"} for item in items}

        return result

    def get_city_id(self, city_title):
        city = self.method("database.getCities", {"q": city_title, "need_all": 0})
        return city.get("items", [])[0]

    def get_top_photos(self, owner_id, count=3):
        album = self.method("photos.get", {"owner_id": owner_id, "album_id": "profile", "extended": 1})
        photos = []
        for item in album.get("items", []):
            id = item.get("id", 0)
            url = item.get("sizes", [])[-1].get("url", "")
            likes = item.get("likes", {}).get("count", 0)
            entry = {"id": id, "url": url, "likes": likes}
            photos.append(entry)

        result = sorted(photos, key=lambda x: x.get("likes", 0), reverse=True)
        return result[:count]


class VKhandler:
    def __init__(self, group_client: VKClient, user_client: VKClient = None,
                 search_fields: dict = {}, search_results: dict = {}, position=0):
        self.client = group_client
        self.user_client = user_client
        self.search_fields = search_fields
        self.search_results = search_results
        self.position = position

    def handle_start(self, event):
        self.client.write_msg(event.object.user_id, f"Для начала работы с ботом необходимо отправить ему "
                                                    f"токен авторизации. Получить токен можно по ссылке "
                                                    f"ниже, выдав необходимые права боту. Значение токена "
                                                    f"будет записано в адресе страницы успешной авторизации "
                                                    f"в поле 'access_token'",
                              {"attachment": get_auth_link(VK_APP_ID, "photos", VK_VERSION)})

    def handle_token(self, event):
        self.user_client = VKClient(token=event.obj.message['text'], app_id=VK_APP_ID)
        # self.user_client.auth(reauth=False, token_only=True)
        self.client.write_msg(event.obj.message['from_id'], f"Вы успешно авторизованы",
                              {"keyboard": open(KB_MAIN, 'r', encoding='UTF-8').read()})

    def handle_authorize(self, event):
        self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)
        self.client.write_msg(event.obj.peer_id, f"Для начала работы с ботом необходимо отправить ему "
                                                 f"токен авторизации. Получить токен можно по ссылке "
                                                 f"ниже, выдав необходимые права боту. Значение токена "
                                                 f"будет записано в адресе страницы успешной авторизации "
                                                 f"в поле 'access_token'",
                              {"attachment": get_auth_link(VK_APP_ID, "photos", VK_VERSION)})

    def handle_search(self, event):
        user_info = self.client.get_user_info(event.object.user_id, "bdate,sex,city")[0]
        city = user_info.get("city", {})
        sex = user_info.get("sex", 0)
        born = datetime.datetime.strptime(user_info.get("bdate", ""), "%d.%m.%Y")
        age = calculate_age(born)
        search_fields = {
            # "fields": "bdate,sex,city",
            "city": city.get("id", 2),
            "sex": 0 if sex == 1 else 1,
            "age_from": age,
            "age_to": age,
        }
        self.search_fields = search_fields
        self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)
        self.client.write_msg(event.object.user_id, f"Выполнить поиск по следующим данным?:\n- г. "
                                                    f"{city.get('title', '')}\n- {age} лет\n- пол "
                                                    f"{'мужской' if sex == 1 else 'женский'}",
                              {"keyboard": open(KB_SEARCH, 'r', encoding='UTF-8').read()})

    def handle_main_menu(self, event):
        self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)
        self.client.write_msg(event.object.user_id, f"Главное меню",
                              {"keyboard": open(KB_MAIN, 'r', encoding='UTF-8').read()})

    def handle_start_search(self, event):
        search_results = self.user_client.search_users(self.search_fields)
        self.search_results = search_results
        self.handle_rotation(event)

    def handle_rotation(self, event):
        search_entry = self.search_results[self.position]

        photos = self.user_client.get_top_photos(search_entry.get("id", 1))
        self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)
        self.client.write_msg(event.object.user_id, f"{search_entry.get('first_name', '')} "
                                                    f"{search_entry.get('last_name', '')}",
                              {"attachment": f"photo{photos[0].get('owner_id', 0)}_{photos[0].get('media_id', 0)},"
                                             f"photo{photos[1].get('owner_id', 0)}_{photos[1].get('media_id', 0)},"
                                             f"photo{photos[1].get('owner_id', 0)}_{photos[1].get('media_id', 0)}"})

    def handle_next(self, event):
        self.position += 1
        self.handle_rotation(event)

    def handle_change_city(self, event):
        pass

    def handle_change_age(self, event):
        pass

    def handle_like(self, event):
        pass

    def handle_list_fav(self, event):
        pass
