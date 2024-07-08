import vk_api
import logging
from random import randrange

from func.utils.utils import api_handler


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
