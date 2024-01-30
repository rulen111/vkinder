import vk_api
from random import randrange
from datetime import date
import yaml
import json
import datetime
import logging
from vk_api.bot_longpoll import VkBotEventType
import inspect

with open("config.yaml") as c:
    config = yaml.full_load(c)

VK_VERSION = config["VK"]["VERSION"]
VK_APP_ID = input("Enter your standalone app ID") if not config["VK"]["APP_ID"] else config["VK"]["APP_ID"]
VK_GROUP_TOKEN = input("Enter VK Group Access Token") if not config["VK"]["GROUP_TOKEN"] else config["VK"][
    "GROUP_TOKEN"]
VK_GROUP_ID = input("Enter VK Group ID") if not config["VK"]["GROUP_ID"] else config["VK"]["GROUP_ID"]
VK_USER_TOKEN = config["VK"]["USER_TOKEN"]

KB_MAIN = "func/keyboards/keyboard_main.json"
KB_CHOOSE = "func/keyboards/keyboard_choose.json"
KB_SEARCH = "func/keyboards/keyboard_search.json"
KB_EMPTY = "func/keyboards/keyboard_empty.json"
KB_SETTINGS = "func/keyboards/keyboard_settings.json"
KB_AUTHORIZE = "func/keyboards/keyboard_authorize.json"
KB_LIST_FAV = "func/keyboards/keyboard_list_fav.json"

logging.basicConfig(level=logging.INFO, filename=f'logs/{datetime.datetime.now().date()}.log',
                    filemode="a", format="%(asctime)s %(levelname)s %(message)s", encoding='UTF-8')
logging.info("-" * 80)
logging.warning(f"Starting VKinder Bot")
logging.info("-" * 80)


def logger(old_func):
    def new_func(*args, **kwargs):
        logging.info(f"Handling event '{old_func.__name__}'")
        result = old_func(*args, **kwargs)
        return result

    return new_func


def api_handler(old_func):
    def new_func(*args, **kwargs):
        try:
            result = old_func(*args, **kwargs)
            return result
        except vk_api.exceptions.ApiError as e:
            logging.exception(e)
            return e

    return new_func


@logger
def update_config(config):
    with open("config.yaml", "w") as c:
        yaml.dump(config, c)


def calculate_age(born):
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


@logger
def write_auth_link_kb(app_id, scope, version):
    base_url = "https://oauth.vk.com/authorize"
    redirect_uri = "https://oauth.vk.com/blank.html"
    display = "page"
    response_type = "token"
    auth_url = (f"{base_url}?client_id={app_id}&display={display}&"
                f"redirect_uri={redirect_uri}&scope={scope}&"
                f"response_type={response_type}&v={version}")

    logging.warning(f"Writing links into keyboard json files")
    kb_auth = open(KB_AUTHORIZE, "r", encoding="utf-8")
    kb_auth_json = json.load(kb_auth)
    kb_auth_json["buttons"][0][0]["action"]["link"] = auth_url
    kb_auth = open(KB_AUTHORIZE, "w", encoding="utf-8")
    json.dump(kb_auth_json, kb_auth)
    kb_auth.close()

    kb_auth = open(KB_MAIN, "r", encoding="utf-8")
    kb_auth_json = json.load(kb_auth)
    kb_auth_json["buttons"][2][0]["action"]["link"] = auth_url
    kb_auth = open(KB_MAIN, "w", encoding="utf-8")
    json.dump(kb_auth_json, kb_auth)
    kb_auth.close()
    logging.info(f"Keyboard files redacted")


class VKClient(vk_api.VkApi):
    @api_handler
    def write_msg(self, user_id, message, fields=None):
        values = {'user_id': user_id, 'message': message, 'random_id': randrange(10 ** 7)}
        logging.info(f"Messaging to id{user_id}")
        if fields:
            self.method('messages.send', {**values, **fields})
        else:
            self.method('messages.send', values)

    @api_handler
    def event_answer(self, event_id, user_id, peer_id):
        self.method("messages.sendMessageEventAnswer", {"event_id": event_id, "user_id": user_id,
                                                        "peer_id": peer_id})

    @api_handler
    def get_user_info(self, user_id, fields):
        logging.info(f"Getting user information for id{user_id}")
        user_info = self.method("users.get", {"user_ids": user_id, "fields": fields})
        return user_info

    @api_handler
    def search_users(self, fields, count=100, offset=0):
        params = {
            "sort": 0,
            "offset": 0,
            "count": 100,
            **fields,
            "has_photo": 1
        }
        logging.info(f"Searching for users, count={count}, offset={offset}")
        search_res = self.method("users.search", params)
        return search_res.get("items", [])

    @api_handler
    def get_city_id(self, city_title):
        city = self.method("database.getCities", {"q": city_title, "need_all": 0})
        return city.get("items", [])[0]

    @api_handler
    def get_top_photos(self, owner_id, count=3):
        logging.info(f"Getting top {count} profile photos of id{owner_id}")
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
        self.handler_schema = dict(inspect.getmembers(self, predicate=inspect.ismethod))

        logging.warning(f"VKhandler initialized")
        write_auth_link_kb(VK_APP_ID, "photos", VK_VERSION)

    @api_handler
    def init_user_client(self, token):
        self.user_client = VKClient(token=token, app_id=VK_APP_ID)

    @logger
    def start(self, event):
        self.client.write_msg(event.obj.message['from_id'], f"Для начала работы с ботом необходимо отправить ему "
                                                            f"токен авторизации. Получить токен можно по кнопке "
                                                            f"ниже, выдав необходимые права боту. Значение токена "
                                                            f"будет записано в адресе страницы успешной авторизации "
                                                            f"в поле 'access_token'",
                              {"keyboard": open(KB_AUTHORIZE, 'r', encoding='UTF-8').read()})

    @logger
    def token(self, event):
        token = event.obj.message['text']
        request = self.init_user_client(token)
        if type(request) != vk_api.exceptions.ApiError:
            config["VK"]["USER_TOKEN"] = token
            update_config(config)

            self.client.write_msg(event.obj.message['from_id'], f"Вы успешно авторизованы",
                                  {"keyboard": open(KB_MAIN, 'r', encoding='UTF-8').read()})
        else:
            self.client.write_msg(event.obj.message['from_id'], f"Возникла ошибка {request.error}.\nПопробуйте еще раз",
                                  {"keyboard": open(KB_AUTHORIZE, 'r', encoding='UTF-8').read()})

    @logger
    def random_msg(self, event):
        self.client.write_msg(event.obj.message['from_id'],
                              f"Если у вас пропала клавиатура, то напишите боту слово 'Начать'",
                              {"keyboard": open(KB_EMPTY, 'r', encoding='UTF-8').read()})

    @logger
    def main_menu(self, event):
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        self.client.write_msg(event.obj.peer_id, f"Главное меню",
                              {"keyboard": open(KB_MAIN, 'r', encoding='UTF-8').read()})

    @logger
    def search(self, event):
        user_info = self.client.get_user_info(event.object.user_id, "bdate,sex,city")[0]
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)
        if type(user_info) != vk_api.exceptions.ApiError:
            city = user_info.get("city", {})
            sex = user_info.get("sex", 0)
            born = datetime.datetime.strptime(user_info.get("bdate", ""), "%d.%m.%Y")
            age = calculate_age(born)
            search_fields = {
                "city": city.get("id", 2),
                "sex": 0 if sex == 1 else 1,
                "age_from": age,
                "age_to": age,
            }
            self.search_fields = search_fields

            self.client.write_msg(event.object.user_id, f"Выполнить поиск по следующим данным?:\n- г. "
                                                        f"{city.get('title', '')}\n- {age} лет\n- пол "
                                                        f"{'мужской' if sex == 1 else 'женский'}",
                                  {"keyboard": open(KB_SEARCH, 'r', encoding='UTF-8').read()})
        else:
            self.client.write_msg(event.obj.peer_id, f"Возникла ошибка {user_info.error}.\nПопробуйте еще раз",
                                  {"keyboard": open(KB_MAIN, 'r', encoding='UTF-8').read()})

    @logger
    def search_start(self, event):
        search_results = self.user_client.search_users(self.search_fields)
        if type(search_results) != vk_api.exceptions.ApiError:
            self.search_results = search_results
            self.rotation(event)
        else:
            self.client.write_msg(event.obj.peer_id, f"Возникла ошибка {search_results.error}.\nПопробуйте еще раз",
                                  {"keyboard": open(KB_MAIN, 'r', encoding='UTF-8').read()})

    @logger
    def rotation(self, event):
        if self.position < len(self.search_results):
            search_entry = self.search_results[self.position]

            photos = self.user_client.get_top_photos(search_entry.get("id", 1))
            if type(photos) != vk_api.exceptions.ApiError:
                logging.info(f'[USER_ID {event.object.user_id}] Got photos from [USER-ID {search_entry.get("id", 1)}]')

                if event.type == VkBotEventType.MESSAGE_EVENT:
                    self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

                attachment = ",".join(
                    [f"photo{photo.get('owner_id', 0)}_{photo.get('media_id', 0)}" for photo in photos])

                self.client.write_msg(event.object.user_id, f"{search_entry.get('first_name', '')} "
                                                            f"{search_entry.get('last_name', '')}" +
                                                            f"\nhttps://vk.com/id{search_entry.get('id', 0)}",
                                      {"attachment": attachment,
                                       "keyboard": open(KB_CHOOSE, 'r', encoding='UTF-8').read()})
            else:
                self.next_person(event)
        else:
            self.client.write_msg(event.obj.peer_id, f"Вы достигли конца списка. Выполните поиск еще раз, чтобы "
                                                     f"обновить выдачу",
                                  {"keyboard": open(KB_MAIN, 'r', encoding='UTF-8').read()})

    @logger
    def next_person(self, event):
        self.position += 1
        self.rotation(event)

    @logger
    def show_help(self, event):
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)
        pass

    @logger
    def settings(self, event):
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        self.client.write_msg(event.object.user_id, f"Какой параметр вы хотите изменить?",
                              {"keyboard": open(KB_SETTINGS, 'r', encoding='UTF-8').read()})

    @logger
    def change_city(self, event):
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        self.client.write_msg(event.object.user_id, "Введите название города в следующем формате:\n"
                                                    "город {Название городда без фиг. скобок}",
                              {"keyboard": open(KB_EMPTY, 'r', encoding='UTF-8').read()})

    @logger
    def change_age(self, event):
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        self.client.write_msg(event.object.user_id, "Введите возраст в следующем формате:\n"
                                                    "возраст {Возраст от}-{Возраст до}",
                              {"keyboard": open(KB_EMPTY, 'r', encoding='UTF-8').read()})

    @logger
    def change_sex(self, event):
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        self.client.write_msg(event.object.user_id, "Введите пол в следующем формате:\n"
                                                    "пол {мужской/женский}",
                              {"keyboard": open(KB_EMPTY, 'r', encoding='UTF-8').read()})

    @logger
    def add_to_fav(self, event):
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        # add_to_db()

        self.client.write_msg(event.object.user_id, f"Пользователь добавлен в избранное",
                              {"keyboard": open(KB_CHOOSE, 'r', encoding='UTF-8').read()})

    @logger
    def list_fav(self, event):
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        # fav = get_from_db()

        self.client.write_msg(event.object.user_id, f"В каком виде вывести избранное?",
                              {"keyboard": open(KB_LIST_FAV, 'r', encoding='UTF-8').read()})

    @logger
    def list_fav_list(self, event):
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        pass

    @logger
    def list_fav_gallery(self, event):
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        pass

    @logger
    def fav_gallery_next(self, event):
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        pass

    @logger
    def start_polling(self, longpoll):
        for event in longpoll.listen():
            if event.type == VkBotEventType.MESSAGE_EVENT:
                payload = event.object.payload.get("type", "")
                self.handler_schema[payload](event)

            elif event.type == VkBotEventType.MESSAGE_NEW:
                if event.from_user:
                    match event.obj.message['text']:
                        case s if s.startswith("vk1.a."):
                            self.handler_schema["token"](event)
                        case "Начать":
                            self.handler_schema["start"](event)
                        case _:
                            self.handler_schema["random_msg"](event)
