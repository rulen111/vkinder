from vk_api.bot_longpoll import VkBotLongPoll

from func import VK_GROUP_TOKEN, VK_VERSION, VK_GROUP_ID
from func.vkclient import VKClient
from func.vkhandler import VKhandler

if __name__ == "__main__":
    vk_group_client = VKClient(token=VK_GROUP_TOKEN, api_version=VK_VERSION)
    vk_handler = VKhandler(vk_group_client)
    longpoll = VkBotLongPoll(vk_group_client, VK_GROUP_ID)
    vk_handler.start_polling(longpoll)
