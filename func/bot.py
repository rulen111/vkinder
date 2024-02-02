import vk_api
import yaml
import logging

import json
import datetime
import inspect
import time

from vk_api.bot_longpoll import VkBotEventType
from random import randrange
from datetime import date

import db.models as db
from db import session

with open("config.yaml") as c:
    config = yaml.full_load(c)

VK_VERSION = config["VK"]["VERSION"]
VK_APP_ID = input("Enter your standalone app ID") if not config["VK"]["APP_ID"] else config["VK"]["APP_ID"]
VK_GROUP_TOKEN = input("Enter VK Group Access Token") if not config["VK"]["GROUP_TOKEN"] \
    else config["VK"]["GROUP_TOKEN"]
VK_GROUP_ID = input("Enter VK Group ID") if not config["VK"]["GROUP_ID"] else config["VK"]["GROUP_ID"]
VK_USER_TOKEN = config["VK"]["USER_TOKEN"]

KB_MAIN = "func/keyboards/keyboard_main.json"
KB_CHOOSE = "func/keyboards/keyboard_choose.json"
KB_SEARCH = "func/keyboards/keyboard_search.json"
KB_EMPTY = "func/keyboards/keyboard_empty.json"
KB_SETTINGS = "func/keyboards/keyboard_settings.json"
KB_AUTHORIZE = "func/keyboards/keyboard_authorize.json"
KB_LIST_FAV = "func/keyboards/keyboard_list_fav.json"
KB_LIST_FAV_GALLERY = "func/keyboards/keyboard_list_fav_gallery.json"

logging.basicConfig(level=logging.INFO, filename=f'logs/{datetime.datetime.now().date()}.log',
                    filemode="a", format="%(asctime)s %(levelname)s %(message)s", encoding='UTF-8')
logging.info("-" * 80)
logging.warning(f"Starting VKinder Bot")
logging.info("-" * 80)


def logger(old_func):
    """
    Decorator for logging a function call
    :param old_func: func to wrap
    :return: wrapped func
    """
    def new_func(*args, **kwargs):
        logging.info(f"Handling event '{old_func.__name__}'")
        result = old_func(*args, **kwargs)
        return result

    return new_func


def api_handler(old_func):
    """
    Decorator for catching vkapi errors
    :param old_func: func to wrap
    :return: wrapped func
    """
    def new_func(*args, **kwargs):
        try:
            result = old_func(*args, **kwargs)
            return result
        except vk_api.exceptions.ApiError as e:
            logging.error(e)
            return e

    return new_func


@logger
def update_config(data):
    """
    Write updated config data to config.yaml
    :param data: data to write
    :return: None
    """
    with open("config.yaml", "w") as f:
        yaml.dump(data, f)


def calculate_age(born):
    """
    Calculate age from birthday date.
    :param born: birthday date obj
    :return: int age
    """
    today = date.today()
    return today.year - born.year - ((today.month, today.day) < (born.month, born.day))


@logger
def write_auth_link_kb(app_id, scope, version):
    """
    Generate VK OAuth link and write it to
    keyboard json files
    :param app_id: VK standalone app id
    :param scope: access scope
    :param version: api version
    :return: None
    """
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
    """
    Based on vk_api.VkApi class.
    Encapsulates several api functions
    """

    @api_handler
    def write_msg(self, user_id, message, fields=None):
        """
        Write message to user with given values. Supports attachments
        :param user_id: id of user to write to
        :param message: message to write
        :param fields: custom parameters
        :return: None
        """
        values = {'user_id': user_id, 'message': message, 'random_id': randrange(10 ** 7)}
        logging.info(f"Messaging to id{user_id}")
        if fields:
            self.method('messages.send', {**values, **fields})
        else:
            self.method('messages.send', values)

    @api_handler
    def event_answer(self, event_id, user_id, peer_id):
        """
        Send answer to a MessageEvent.
        Used to show a successful method execution
        :param event_id: id of the caller event
        :param user_id: id of the caller user
        :param peer_id: id of the chat object
        :return: None
        """
        self.method("messages.sendMessageEventAnswer", {"event_id": event_id, "user_id": user_id,
                                                        "peer_id": peer_id})

    @api_handler
    def get_user_info(self, user_id, fields):
        """
        Invoke "users.get" api method.
        :param user_id: id of the user in question
        :param fields: custom fields to return
        :return: User object
        """
        logging.info(f"Getting user information for id{user_id}")
        user_info = self.method("users.get", {"user_ids": user_id, "fields": fields})
        return user_info

    @api_handler
    def search_users(self, fields, count=100, offset=0):
        """
        Invoke "users.search" with specified search parameters.
        :param fields: fields to search with
        :param count: number of entries to get
        :param offset: first entry offset
        :return: list of User objects
        """
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
        """
        Invoke "database.getCities" api method.
        :param city_title: search query
        :return: city object
        """
        city = self.method("database.getCities", {"q": city_title, "need_all": 0})
        return city.get("items", [])[0]

    @api_handler
    def get_top_photos(self, owner_id, count=3):
        """
        Invoke "photos.get" api method.
        Get top liked profile photos of a user.
        :param owner_id: id of the user in question
        :param count: number of photos to get
        :return: list of photo dcit objects
        """
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
    """
    Class for longpoll handling. Processes incoming bot events.
    """
    def __init__(self, group_client: VKClient, user_client: VKClient = None,
                 search_fields: dict = None, search_results: dict = None, fav_list: list = None,
                 position: int = 0, current_entry: dict = None):
        """
        Must pass a working VKClient object.
        Can be initialized with specified search parameters.
        :param group_client: required. VKClient object for use with group token
        :param user_client: VKClient object for use with user token
        :param search_fields: Parameters for search function
        :param search_results: Search results
        :param fav_list: Favourite list
        :param position: Search result index
        """
        self.client = group_client
        self.user_client = VKClient(token=VK_USER_TOKEN, app_id=VK_APP_ID) if VK_USER_TOKEN else user_client
        self.search_fields = search_fields
        self.search_results = search_results
        self.fav_list = fav_list
        self.position = position
        self.current_entry = current_entry
        self.handler_schema = dict(inspect.getmembers(self, predicate=inspect.ismethod))

        logging.info(f"VKhandler initialized")
        write_auth_link_kb(VK_APP_ID, "photos", VK_VERSION)

    @api_handler
    def init_user_client(self, token):
        """
        Handle initialization of VKClient object for use with user token.
        :param token: access_token
        :return: None
        """
        self.user_client = VKClient(token=token, app_id=VK_APP_ID)

    @logger
    def start(self, event):
        """
        Handle "start" event.
        :param event: event object
        :return: None
        """
        self.client.write_msg(event.obj.message['from_id'], f"Для начала работы с ботом необходимо отправить ему "
                                                            f"токен авторизации. Получить токен можно по кнопке "
                                                            f"ниже, выдав необходимые права боту. Значение токена "
                                                            f"будет записано в адресе страницы успешной авторизации "
                                                            f"в поле 'access_token'",
                              {"keyboard": open(KB_AUTHORIZE, 'r', encoding='UTF-8').read()})

    @logger
    def token(self, event):
        """
        Handle "token" event.
        :param event: event object
        :return: None
        """
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
        """
        Handle "random_msg" event.
        :param event: event object
        :return: None
        """
        self.client.write_msg(event.obj.message['from_id'],
                              f"Если у вас пропала клавиатура, то напишите боту слово 'Начать'",
                              {"keyboard": open(KB_EMPTY, 'r', encoding='UTF-8').read()})

    @logger
    def main_menu(self, event):
        """
        Handle "main_menu" event.
        :param event: event object
        :return: None
        """
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        self.client.write_msg(event.obj.peer_id, f"Главное меню",
                              {"keyboard": open(KB_MAIN, 'r', encoding='UTF-8').read()})

    @logger
    def search(self, event):
        """
        Handle "search" event.
        :param event: event object
        :return: None
        """
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        try:
            self.search_fields = db.get_client_info(session, event.object.user_id)
            self.client.write_msg(event.object.user_id,
                                  f"Выполнить поиск по следующим данным?:\n- г. "
                                  f"{self.search_fields.get('city', {}).get('title', '')}\n- от "
                                  f"{self.search_fields.get('age_from', 0)} до "
                                  f"{self.search_fields.get('age_to', 0)} лет\n- "
                                  f"пол {'мужской' if self.search_fields.get('sex', 0) == 0 else 'женский'}",
                                  {"keyboard": open(KB_SEARCH, 'r', encoding='UTF-8').read()})
            return
        except Exception as err:
            logging.error(err)
            self.search_fields = self.client.get_user_info(event.object.user_id, "bdate,sex,city")[0]

        if type(self.search_fields) != vk_api.exceptions.ApiError:
            city = self.search_fields.get("city", {})
            sex = self.search_fields.get("sex", 0)

            try:
                born = datetime.datetime.strptime(self.search_fields.get("bdate", ""), "%d.%m.%Y")
                age_from = calculate_age(born)
                age_to = age_from
            except Exception as err:
                logging.error(err)
                age_from = 21
                age_to = age_from

            try:
                db.add_city_entry(session, city.get("id", 2), city.get("title", ""))
            except Exception as err:
                logging.error(err)

            self.search_fields = {
                "city": city,
                "sex": 0 if sex == 1 else 1,
                "age_from": age_from,
                "age_to": age_to
            }
            db.add_client_info(session, event.object.user_id, **self.search_fields)

            self.client.write_msg(event.object.user_id,
                                  f"Выполнить поиск по следующим данным?:\n- г. "
                                  f"{self.search_fields.get('city', {}).get('title', '')}\n- от "
                                  f"{self.search_fields.get('age_from', 0)} до "
                                  f"{self.search_fields.get('age_to', 0)} лет\n- "
                                  f"пол {'мужской' if self.search_fields.get('sex', 0) == 0 else 'женский'}",
                                  {"keyboard": open(KB_SEARCH, 'r', encoding='UTF-8').read()})
        else:
            self.client.write_msg(event.obj.peer_id,
                                  f"Возникла ошибка {self.search_fields.error}.\nПопробуйте еще раз",
                                  {"keyboard": open(KB_MAIN, 'r', encoding='UTF-8').read()})

    @logger
    def search_start(self, event):
        """
        Handle "search_start" event.
        :param event: event object
        :return: None
        """
        search_fields = self.search_fields
        search_fields["city"] = search_fields["city"].get("id", 2)
        search_results = self.user_client.search_users(search_fields)

        if type(search_results) != vk_api.exceptions.ApiError:
            self.search_results = search_results
            self.rotation(event)
        else:
            self.client.write_msg(event.obj.peer_id,
                                  f"Возникла ошибка {search_results.error}.\nПопробуйте еще раз",
                                  {"keyboard": open(KB_MAIN, 'r', encoding='UTF-8').read()})

    @logger
    def rotation(self, event):
        """
        Handle "rotation" event.
        :param event: event object
        :return: None
        """
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        if self.position < len(self.search_results):
            search_entry = self.search_results[self.position]

            photos = self.user_client.get_top_photos(search_entry.get("id", 1))
            if type(photos) != vk_api.exceptions.ApiError:
                logging.info(f'[USER_ID {event.object.user_id}] Got photos from [USER-ID {search_entry.get("id", 1)}]')

                attachment = ",".join(
                    [f"photo{photo.get('owner_id', 0)}_{photo.get('media_id', 0)}" for photo in photos])

                self.current_entry = {
                    "first_name": search_entry.get('first_name', ''),
                    "last_name": search_entry.get('last_name', ''),
                    "link": f"\nhttps://vk.com/id{search_entry.get('id', 0)}",
                    "attachment": attachment
                }

                self.client.write_msg(event.object.user_id, f"\n{self.current_entry.get('first_name', '')} "
                                                            f"{self.current_entry.get('last_name', '')}" +
                                      f"{self.current_entry.get('link', '')}",
                                      {"attachment": self.current_entry.get("attachment", ""),
                                       "keyboard": open(KB_CHOOSE, 'r', encoding='UTF-8').read()})
            else:
                self.next_person(event)
        else:
            self.client.write_msg(event.obj.peer_id,
                                  f"Вы достигли конца списка. Выполните поиск еще раз, чтобы обновить выдачу",
                                  {"keyboard": open(KB_MAIN, 'r', encoding='UTF-8').read()})

    @logger
    def next_person(self, event):
        """
        Handle "next_person" event.
        :param event: event object
        :return: None
        """
        self.position += 1
        self.rotation(event)

    @logger
    def show_help(self, event):
        """
        Handle "show_help" event.
        :param event: event object
        :return: None
        """
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)
        pass

    @logger
    def settings(self, event):
        """
        Handle "settings" event.
        :param event: event object
        :return: None
        """
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        self.client.write_msg(event.object.user_id, f"Какой параметр вы хотите изменить?",
                              {"keyboard": open(KB_SETTINGS, 'r', encoding='UTF-8').read()})

    @logger
    def change_city(self, event):
        """
        Handle "change_city" event.
        :param event: event object
        :return: None
        """
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        self.client.write_msg(event.object.user_id, "Введите название города в следующем формате:\n"
                                                    "город {Название городда без фиг. скобок}",
                              {"keyboard": open(KB_EMPTY, 'r', encoding='UTF-8').read()})

    @logger
    def change_city_value(self, event):
        """
        Handle "change_city_value" event.
        :param event: event object
        :return: None
        """
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        city = self.user_client.get_city_id(event.obj.message['text'].split("город ")[1])
        self.search_fields["city"] = city

        try:
            db.add_city_entry(session, city.get("id", 2), city.get("title", ""))
        except Exception as err:
            logging.error(err)

        db.add_client_info(session, event.obj.message['from_id'], **self.search_fields)

        self.client.write_msg(event.obj.message['from_id'], f"Город успешно изменен!\n"
                                                            f"Какой параметр вы хотите изменить?",
                              {"keyboard": open(KB_SETTINGS, 'r', encoding='UTF-8').read()})

    @logger
    def change_age(self, event):
        """
        Handle "change_age" event.
        :param event: event object
        :return: None
        """
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        self.client.write_msg(event.object.user_id, "Введите возраст в следующем формате:\n"
                                                    "возраст {Возраст от}-{Возраст до}",
                              {"keyboard": open(KB_EMPTY, 'r', encoding='UTF-8').read()})

    @logger
    def change_age_value(self, event):
        """
        Handle "change_age_value" event.
        :param event: event object
        :return: None
        """
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        age_from, age_to = event.obj.message['text'].split("возраст ")[1].split("-")
        self.search_fields["age_from"] = age_from
        self.search_fields["age_to"] = age_to
        db.add_client_info(session, event.obj.message['from_id'], **self.search_fields)

        self.client.write_msg(event.obj.message['from_id'], f"Возраст успешно изменен!\n"
                                                            f"Какой параметр вы хотите изменить?",
                              {"keyboard": open(KB_SETTINGS, 'r', encoding='UTF-8').read()})

    @logger
    def change_sex(self, event):
        """
        Handle "change_sex" event.
        :param event: event object
        :return: None
        """
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        self.client.write_msg(event.object.user_id, "Введите пол в следующем формате:\n"
                                                    "пол {мужской/женский}",
                              {"keyboard": open(KB_EMPTY, 'r', encoding='UTF-8').read()})

    @logger
    def change_sex_value(self, event):
        """
        Handle "change_sex_value" event.
        :param event: event object
        :return: None
        """
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        sex = event.obj.message['text'].split("пол ")[1]
        self.search_fields["sex"] = 1 if sex == "мужской" else 0
        db.add_client_info(session, event.obj.message['from_id'], **self.search_fields)

        self.client.write_msg(event.obj.message['from_id'],
                              f"Пол успешно изменен!\nКакой параметр вы хотите изменить?",
                              {"keyboard": open(KB_SETTINGS, 'r', encoding='UTF-8').read()})

    @logger
    def add_to_fav(self, event):
        """
        Handle "add_to_fav" event.
        :param event: event object
        :return: None
        """
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        entry = {k: v for k, v in self.current_entry.items() if k != "link"}
        try:
            db.add_fav_entry(session, event.object.user_id,
                             int(self.current_entry["link"].strip("\nhttps://vk.com/id")), **entry)

            self.client.write_msg(event.object.user_id,
                                  f"Пользователь {self.current_entry.get('first_name', '')} "
                                  f"{self.current_entry.get('last_name', '')} добавлен в избранное",
                                  {"keyboard": open(KB_CHOOSE, 'r', encoding='UTF-8').read()})
        except Exception as err:
            logging.error(err)
            self.client.write_msg(event.object.user_id,
                                  f"Пользователь {self.current_entry.get('first_name', '')} "
                                  f"{self.current_entry.get('last_name', '')} уже в избранном",
                                  {"keyboard": open(KB_CHOOSE, 'r', encoding='UTF-8').read()})

    @logger
    def list_fav(self, event):
        """
        Handle "list_fav" event.
        :param event: event object
        :return: None
        """
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        try:
            self.fav_list = db.get_fav_list(session, event.object.user_id)
            self.client.write_msg(event.object.user_id, f"В каком виде вывести избранное?",
                                  {"keyboard": open(KB_LIST_FAV, 'r', encoding='UTF-8').read()})
        except Exception as err:
            logging.error(err)
            self.client.write_msg(event.object.user_id, f"Вы никого не добавляли в избранное.",
                                  {"keyboard": open(KB_MAIN, 'r', encoding='UTF-8').read()})

    @logger
    def list_fav_list(self, event):
        """
        Handle "list_fav_list" event.
        :param event: event object
        :return: None
        """
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        for idx, entry in enumerate(self.fav_list):
            if (idx + 1) % 5 == 0:
                time.sleep(1)

            self.client.write_msg(event.object.user_id, f"- {entry.get('first_name', '')} "
                                                        f"{entry.get('last_name', '')} "
                                                        f"{entry.get('link', '')}")

        self.client.write_msg(event.object.user_id, f"Конец списка",
                              {"keyboard": open(KB_MAIN, 'r', encoding='UTF-8').read()})

    @logger
    def list_fav_gallery(self, event):
        """
        Handle "list_fav_gallery" event.
        :param event: event object
        :return: None
        """
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        pass

    @logger
    def fav_gallery_next(self, event):
        """
        Handle "fav_gallery_next" event.
        :param event: event object
        :return: None
        """
        if event.type == VkBotEventType.MESSAGE_EVENT:
            self.client.event_answer(event.object.event_id, event.object.user_id, event.object.peer_id)

        pass

    @logger
    def start_polling(self, longpoll):
        """
        Start receiving and handling events from VK servers.
        Iterates over every incoming event and calls an appropriate handler.
        :param longpoll: longpoll object
        :return: None
        """
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
                        case s if s.startswith("город "):
                            self.handler_schema["change_city_value"](event)
                        case s if s.startswith("возраст "):
                            self.handler_schema["change_age_value"](event)
                        case s if s.startswith("пол "):
                            self.handler_schema["change_sex_value"](event)
                        case _:
                            self.handler_schema["random_msg"](event)
