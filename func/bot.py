import vk_api
from random import randrange
from datetime import date
import yaml
import json
import datetime
import logging
from vk_api.bot_longpoll import VkBotEventType

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

logging.basicConfig(level=logging.INFO, filename=f'logs/{datetime.datetime.now().date()}.txt',
                    filemode="a", format="%(asctime)s %(levelname)s %(message)s", encoding='UTF-8')
logging.info("\n" + "-" * 80)
logging.info(f"Starting VKinder Bot")
logging.info("-" * 80)


def logger(old_func):
    def new_func(*args, **kwargs):
        logging.info(f"Calling '{old_func.__name__}'")
        result = old_func(*args, **kwargs)
        return result

    return new_func


def calculate_age(born):
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


def write_auth_link_kb(app_id, scope, version):
    base_url = "https://oauth.vk.com/authorize"
    redirect_uri = "https://oauth.vk.com/blank.html"
    display = "page"
    response_type = "token"
    auth_url = (f"{base_url}?client_id={app_id}&display={display}&"
                f"redirect_uri={redirect_uri}&scope={scope}&"
                f"response_type={response_type}&v={version}")

    logging.info(f"Writing links into keyboard files")
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


class VKClient(vk_api.VkApi):
    @logger
    def write_msg(self, user_id, message, fields=None):
        values = {'user_id': user_id, 'message': message, 'random_id': randrange(10 ** 7)}
        if fields:
            self.method('messages.send', {**values, **fields})
        else:
            self.method('messages.send', values)

    @logger
    def event_answer(self, event_id, user_id, peer_id):
        self.method("messages.sendMessageEventAnswer", {"event_id": event_id, "user_id": user_id,
                                                        "peer_id": peer_id})

    @logger
    def get_user_info(self, user_ids, fields):
        user_info = self.method("users.get", {"user_ids": user_ids, "fields": fields})
        return user_info

    @logger
    def search_users(self, fields):
        params = {
            "sort": 0,
            "offset": 0,
            "count": 100,
            **fields,
            "has_photo": 1
        }
        search_res = self.method("users.search", params)
        return search_res.get("items", [])

    @logger
    def get_city_id(self, city_title):
        city = self.method("database.getCities", {"q": city_title, "need_all": 0})
        return city.get("items", [])[0]

    @logger
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
    @logger
    def __init__(self, group_client: VKClient, user_client: VKClient = None,
                 search_fields: dict = {}, search_results: dict = {}, position=0):
        self.client = group_client
        self.user_client = VKClient(token=VK_USER_TOKEN, app_id=VK_APP_ID) if VK_USER_TOKEN else user_client
        self.search_fields = search_fields
        self.search_results = search_results
        self.position = position

        write_auth_link_kb(VK_APP_ID, "photos", VK_VERSION)

    @logger
    def handle_start(self, event):
        self.client.write_msg(event.obj.message['from_id'], f"Для начала работы с ботом необходимо отправить ему "
                                                            f"токен авторизации. Получить токен можно по кнопке "
                                                            f"ниже, выдав необходимые права боту. Значение токена "
                                                            f"будет записано в адресе страницы успешной авторизации "
                                                            f"в поле 'access_token'",
                              {"keyboard": open(KB_AUTHORIZE, 'r', encoding='UTF-8').read()})

    @logger
    def handle_token(self, event):
        self.user_client = VKClient(token=event.obj.message['text'], app_id=VK_APP_ID)
        # self.user_client.auth(reauth=False, token_only=True)
        self.client.write_msg(event.obj.message['from_id'], f"Вы успешно авторизованы",
                              {"keyboard": open(KB_MAIN, 'r', encoding='UTF-8').read()})

    @logger
    def handle_random(self, event):
        self.client.write_msg(event.obj.message['from_id'],
                              f"Если у вас пропала клавиатура, то напишите боту слово 'Начать'",
                              {"keyboard": open(KB_EMPTY, 'r', encoding='UTF-8').read()})

    @logger
    def handle_main_menu(self, event):
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)
        self.client.write_msg(event.obj.peer_id, f"Главное меню",
                              {"keyboard": open(KB_MAIN, 'r', encoding='UTF-8').read()})

    @logger
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

    @logger
    def handle_search_start(self, event):
        search_results = self.user_client.search_users(self.search_fields)
        self.search_results = search_results
        self.handle_rotation(event)

    @logger
    def handle_rotation(self, event):
        if self.position < len(self.search_results):
            search_entry = self.search_results[self.position]

            try:
                photos = self.user_client.get_top_photos(search_entry.get("id", 1))
            except vk_api.exceptions.ApiError as e:
                logging.error(
                    f'[USER_ID {event.object.user_id}] Unable to get photos from [USER-ID {search_entry.get("id", 1)}]. {e}')
                self.handle_next(event)
            else:
                logging.info(f'[USER_ID {event.object.user_id}] Got photos from [USER-ID {search_entry.get("id", 1)}]')
                if event.type == VkBotEventType.MESSAGE_EVENT:
                    self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

                attachment = ",".join(
                    [f"photo{photo.get('owner_id', 0)}_{photo.get('media_id', 0)}" for photo in photos])
                self.client.write_msg(event.object.user_id, f"{search_entry.get('first_name', '')} "
                                                            f"{search_entry.get('last_name', '')}" + f"\nhttps://vk.com/id{search_entry.get('id', 0)}",
                                      {"attachment": attachment,
                                       "keyboard": open(KB_CHOOSE, 'r', encoding='UTF-8').read()})

    @logger
    def handle_next(self, event):
        self.position += 1
        self.handle_rotation(event)

    @logger
    def handle_help(self, event):
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)
        pass

    @logger
    def handle_settings(self, event):
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)
        self.client.write_msg(event.object.user_id, f"Какой параметр вы хотите изменить?",
                              {"keyboard": open(KB_SETTINGS, 'r', encoding='UTF-8').read()})

    @logger
    def handle_change_city(self, event):
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)
        self.client.write_msg(event.object.user_id, f"Какой параметр вы хотите изменить?",
                              {"keyboard": open(KB_SETTINGS, 'r', encoding='UTF-8').read()})

    @logger
    def handle_change_age(self, event):
        pass

    @logger
    def handle_change_sex(self, event):
        pass

    @logger
    def handle_like(self, event):
        pass

    @logger
    def handle_list_fav(self, event):
        pass


@logger
def start_polling(longpoll, vk_handler):
    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_EVENT:
            match event.object.payload.get("type", ""):
                case "main_menu":
                    vk_handler.handle_main_menu(event)
                case "search":
                    vk_handler.handle_search(event)
                case "search_start":
                    vk_handler.handle_search_start(event)
                case "next":
                    vk_handler.handle_next(event)
                case "help":
                    vk_handler.handle_help(event)
                case "settings":
                    vk_handler.handle_settings(event)
                case "change_city":
                    vk_handler.handle_change_city(event)
                case "change_age":
                    vk_handler.handle_change_age(event)
                case "change_sex":
                    vk_handler.handle_change_sex(event)
                case "like":
                    vk_handler.handle_like(event)
                case "list_fav":
                    vk_handler.handle_list_fav(event)

        elif event.type == VkBotEventType.MESSAGE_NEW:
            if event.from_user:
                match event.obj.message['text']:
                    case s if s.startswith("vk1.a."):
                        vk_handler.handle_token(event)
                    case "Начать":
                        vk_handler.handle_start(event)
                    case _:
                        vk_handler.handle_random(event)
