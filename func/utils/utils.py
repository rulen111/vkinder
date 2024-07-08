import vk_api
import yaml
import logging

import json
from datetime import date

from func import KB_AUTHORIZE, KB_MAIN


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
