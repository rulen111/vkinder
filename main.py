from func.bot import VKClient, VKhandler
import yaml
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType


with open("config.yaml") as c:
    config = yaml.full_load(c)

VK_VERSION = config["VK"]["VERSION"]
VK_GROUP_TOKEN = config["VK"]["GROUP_TOKEN"]
VK_GROUP_ID = config["VK"]["GROUP_ID"]


if __name__ == "__main__":
    vk_group_client = VKClient(token=VK_GROUP_TOKEN, api_version=VK_VERSION)
    vk_handler = VKhandler(vk_group_client)
    longpoll = VkBotLongPoll(vk_group_client, VK_GROUP_ID)

    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_EVENT:
            if event.object.payload.get("type", "") == "authorize":
                vk_handler.handle_authorize(event)
            elif event.object.payload.get("type", "") == "search":
                vk_handler.handle_search(event)
            elif event.object.payload.get("type", "") == "search_start":
                vk_handler.handle_start_search(event)
            elif event.object.payload.get("type", "") == "main_menu":
                vk_handler.handle_main_menu(event)

        elif event.type == VkBotEventType.MESSAGE_NEW:
            if event.from_user:
                if event.obj.message['text'].startswith("vk1.a."):
                    vk_handler.handle_token(event)
                elif event.obj.message['text'] == "Начать":
                    vk_handler.handle_start(event)

