import yaml

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
