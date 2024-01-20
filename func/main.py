import yaml
import requests

with open("config.yaml") as c:
    config = yaml.full_load(c)

VK_USER_TOKEN = config["VK"]["USER_TOKEN"]
VK_VERSION = config["VK"]["VERSION"]
VK_APP_ID = config["VK"]["APP_ID"]


class VKUserClient:
    def __init__(self, access_token, user_id, version):
        self.token = access_token
        self.id = user_id
        self.version = version
        self.base_url = "https://api.vk.com/method/"
        self.params = {"access_token": self.token, "v": self.version}

    def search_users(self, fields, offset=0):
        url = self.base_url + "users.search"
        params = {
            "sort": 0,
            "offset": offset,
            "count": 10,
            "city": fields.get("city_id", 1),
            "sex": fields.get("sex", 1),
            "age_from": fields.get("age_from", 18),
            "age_to": fields.get("age_to", 99),
            "has_photo": 1
        }
        response = requests.get(url, params={**self.params, **params})
        content = response.json().get("response", {})
        return content.get("items", [])

    def get_city_id(self, city):
        url = self.base_url + "database.getCities"
        params = {
            "q": city,
            "need_all": 0
        }
        response = requests.get(url, params={**self.params, **params})
        content = response.json().get("response", {})
        return content.get("items", [])[0]

    def get_top_photos(self, owner_id, count=3):
        url = self.base_url + "photos.get"
        params = {
            "owner_id": owner_id,
            "album_id": "profile",
            "extended": 1
        }
        response = requests.get(url, params={**self.params, **params})
        content = response.json().get("response", {})

        album = []
        for item in content.get("items", []):
            url = item.get("sizes", [])[-1].get("url", "")
            likes = item.get("likes", {}).get("count", 0)
            entry = {"url": url, "likes": likes}
            album.append(entry)

        result = sorted(album, key=lambda x: x.get("likes", 0), reverse=True)
        return result[:count]


if __name__ == "__main__":
    user_id = "73489272"
    client_vk = VKUserClient(VK_USER_TOKEN, user_id, VK_VERSION)
    city = "Санкт-Петербург"
    city_id = client_vk.get_city_id(city).get("id", 0)
    print(city_id, city)
    fields = {
        "city_id": city_id,
        "sex": 1,
        "age_from": 18,
        "age_to": 22
    }
    search_res = client_vk.search_users(fields)
    print(search_res)
    photos = client_vk.get_top_photos(search_res[1].get("id", 1))
    print(photos)