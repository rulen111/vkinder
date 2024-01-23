import vk_api
from random import randrange
from datetime import date


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

