from func.bot import *
import yaml
from vk_api.longpoll import VkLongPoll, VkEventType
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


def get_auth_link(app_id, scope, version):
    base_url = "https://oauth.vk.com/authorize"
    redirect_uri = "https://oauth.vk.com/blank.html"
    display = "page"
    response_type = "token"
    auth_url = (f"{base_url}?client_id={app_id}&display={display}&"
                f"redirect_uri={redirect_uri}&scope={scope}&"
                f"response_type={response_type}&v={version}")
    return auth_url


if __name__ == "__main__":
    # user_id = "73489272"
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