import datetime
import inspect
import logging
import time

import vk_api
from vk_api.bot_longpoll import VkBotEventType

import db.models as db
from db import session

from func import config, VK_VERSION, VK_APP_ID, VK_USER_TOKEN
from func import KB_MAIN, KB_CHOOSE, KB_SEARCH, KB_EMPTY, KB_SETTINGS, KB_AUTHORIZE, KB_LIST_FAV

from func.vkclient import VKClient
from func.utils.utils import logger, api_handler, update_config, calculate_age, write_auth_link_kb


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

                self.client.write_msg(event.object.user_id,
                                      f"\n{self.current_entry.get('first_name', '')} "
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

            self.client.write_msg(event.object.user_id,
                                  f"\n{entry.get('first_name', '')} "
                                  f"{entry.get('last_name', '')}" +
                                  f"{entry.get('link', '')}",
                                  {"attachment": entry.get("attachment", ""),
                                   "keyboard": open(KB_CHOOSE, 'r', encoding='UTF-8').read()})

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
