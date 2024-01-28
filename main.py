from func.bot import *
from vk_api.bot_longpoll import VkBotLongPoll, VkBotEventType

if __name__ == "__main__":
    vk_group_client = VKClient(token=VK_GROUP_TOKEN, api_version=VK_VERSION)
    vk_handler = VKhandler(vk_group_client)
    longpoll = VkBotLongPoll(vk_group_client, VK_GROUP_ID)

    for event in longpoll.listen():
        if event.type == VkBotEventType.MESSAGE_EVENT:
            match event.object.payload.get("type", ""):
                case "main_menu":
                    logging.info(f"[USER_ID {event.object.user_id}] Handling 'main_menu'")
                    vk_handler.handle_main_menu(event)
                case "search":
                    logging.info(f"[USER_ID {event.object.user_id}] Handling 'search'")
                    vk_handler.handle_search(event)
                case "search_start":
                    logging.info(f"[USER_ID {event.object.user_id}] Handling 'search_start'")
                    vk_handler.handle_search_start(event)
                case "next":
                    logging.info(f"[USER_ID {event.object.user_id}] Handling 'next'")
                    vk_handler.handle_next(event)
                case "help":
                    logging.info(f"[USER_ID {event.object.user_id}] Handling 'help'")
                    vk_handler.handle_help(event)
                case "settings":
                    logging.info(f"[USER_ID {event.object.user_id}] Handling 'settings'")
                    vk_handler.handle_settings(event)
                case "change_city":
                    logging.info(f"[USER_ID {event.object.user_id}] Handling 'change_city'")
                    vk_handler.handle_change_city(event)
                case "change_age":
                    logging.info(f"[USER_ID {event.object.user_id}] Handling 'change_age'")
                    vk_handler.handle_change_age(event)
                case "change_sex":
                    logging.info(f"[USER_ID {event.object.user_id}] Handling 'change_sex'")
                    vk_handler.handle_change_sex(event)
                case "like":
                    logging.info(f"[USER_ID {event.object.user_id}] Handling 'like'")
                    vk_handler.handle_like(event)
                case "list_fav":
                    logging.info(f"[USER_ID {event.object.user_id}] Handling 'list_fav'")
                    vk_handler.handle_list_fav(event)

        elif event.type == VkBotEventType.MESSAGE_NEW:
            if event.from_user:
                match event.obj.message['text']:
                    case s if s.startswith("vk1.a."):
                        logging.info(f"[USER_ID {event.obj.message['from_id']}] Handling 'token'")
                        vk_handler.handle_token(event)
                    case "Начать":
                        logging.info(f"[USER_ID {event.obj.message['from_id']}] Handling 'Начать'")
                        vk_handler.handle_start(event)
                    case _:
                        logging.info(f"[USER_ID {event.obj.message['from_id']}] Handling 'random message'")
                        vk_handler.handle_random(event)
