import vk_api
from random import randrange
from datetime import date
import yaml
import datetime
import logging
from vk_api.bot_longpoll import VkBotEventType

with open("config.yaml") as c:
    config = yaml.full_load(c)

VK_VERSION = config["VK"]["VERSION"]
VK_GROUP_TOKEN = config["VK"]["GROUP_TOKEN"]
VK_GROUP_ID = config["VK"]["GROUP_ID"]
VK_USER_TOKEN = config["VK"]["USER_TOKEN"]
VK_APP_ID = config["VK"]["APP_ID"]

KB_MAIN = "func/keyboards/keyboard_main.json"
KB_CHOOSE = "func/keyboards/keyboard_choose.json"
KB_SEARCH = "func/keyboards/keyboard_search.json"
KB_EMPTY = "func/keyboards/keyboard_empty.json"
KB_SETTINGS = "func/keyboards/keyboard_settings.json"


logging.basicConfig(level=logging.INFO, filename=f'logs/{datetime.datetime.now().date()}.txt',
                    filemode="a", format="%(asctime)s %(levelname)s %(message)s", encoding='UTF-8')
logging.info('-' * 80)
logging.info(f'Starting at {datetime.datetime.now()}')
logging.info('-' * 80)


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
        return search_res.get("items", [])

    def get_city_id(self, city_title):
        city = self.method("database.getCities", {"q": city_title, "need_all": 0})
        return city.get("items", [])[0]

    def get_top_photos(self, owner_id, count=3):
        album = self.method("photos.get", {"owner_id": owner_id, "album_id": "profile", "extended": 1})
        photos = []
        for item in album.get("items", []):
            media_id = item.get("id", 0)
            url = item.get("sizes", [])[-1].get("url", "")
            likes = item.get("likes", {}).get("count", 0)
            entry = {"media_id": media_id, "url": url, "likes": likes, "owner_id": owner_id}
            photos.append(entry)

        result = sorted(photos, key=lambda x: x.get("likes", 0), reverse=True)
        return result[:count]


class VKhandler:
    def __init__(self, group_client: VKClient, user_client: VKClient = None,
                 search_fields: dict = {}, search_results: dict = {}, position=0):
        self.client = group_client
        self.user_client = VKClient(token=VK_USER_TOKEN, app_id=VK_APP_ID) if VK_USER_TOKEN else user_client
        self.search_fields = search_fields
        self.search_results = search_results
        self.position = position

    def handle_start(self, event):
        self.client.write_msg(event.obj.message['from_id'], f"Для начала работы с ботом необходимо отправить ему "
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

    def handle_random(self, event):
        self.client.write_msg(event.obj.peer_id, f"Если у вас пропала клавиатура, то напишите боту слово 'Начать'",
                              {"attachment": get_auth_link(VK_APP_ID, "photos", VK_VERSION)})

    def handle_main_menu(self, event):
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)
        self.client.write_msg(event.obj.peer_id, f"Главное меню",
                              {"keyboard": open(KB_MAIN, 'r', encoding='UTF-8').read()})

    def handle_authorize(self, event):
        if event.type == VkBotEventType.MESSAGE_EVENT:
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
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)
        self.client.write_msg(event.object.user_id, f"Выполнить поиск по следующим данным?:\n- г. "
                                                    f"{city.get('title', '')}\n- {age} лет\n- пол "
                                                    f"{'мужской' if sex == 1 else 'женский'}",
                              {"keyboard": open(KB_SEARCH, 'r', encoding='UTF-8').read()})

    def handle_search_start(self, event):
        search_results = self.user_client.search_users(self.search_fields)
        self.search_results = search_results
        self.handle_rotation(event)

    def handle_rotation(self, event):
        if self.position < len(self.search_results):
            search_entry = self.search_results[self.position]

            photos = self.user_client.get_top_photos(search_entry.get("id", 1))
            if event.type == VkBotEventType.MESSAGE_EVENT:
                self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)
            self.client.write_msg(event.object.user_id, f"{search_entry.get('first_name', '')} "
                                                        f"{search_entry.get('last_name', '')}" + f"\nhttps://vk.com/id{search_entry.get('id', 0)}",
                                  {"attachment": f"photo{photos[0].get('owner_id', 0)}_{photos[0].get('media_id', 0)},"
                                                 f"photo{photos[1].get('owner_id', 0)}_{photos[1].get('media_id', 0)},"
                                                 f"photo{photos[2].get('owner_id', 0)}_{photos[2].get('media_id', 0)}",
                                   "keyboard": open(KB_CHOOSE, 'r', encoding='UTF-8').read()})

    def handle_next(self, event):
        self.position += 1
        self.handle_rotation(event)

    def handle_help(self, event):
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)
        pass

    def handle_settings(self, event):
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)
        self.client.write_msg(event.object.user_id, f"Какой параметр вы хотите изменить?",
                              {"keyboard": open(KB_SETTINGS, 'r', encoding='UTF-8').read()})

    def handle_change_city(self, event):
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)
        self.client.write_msg(event.object.user_id, f"Какой параметр вы хотите изменить?",
                              {"keyboard": open(KB_SETTINGS, 'r', encoding='UTF-8').read()})

    def handle_change_age(self, event):
        pass

    def handle_change_sex(self, event):
        pass

    def handle_like(self, event):
        pass

    def handle_list_fav(self, event):
        pass
