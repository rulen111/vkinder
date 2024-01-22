from db.create_db import Like_users, Image
from db.config import session


def find_user():
    pass


def add_info_db(*args):

    print(args[3])
    added_user = Like_users(name=args[0], surname=args[1], user_id_vk=args[2])
    added_image = Image(url=args[3])
    session.add(added_user)
    session.add(added_image)

    session.commit()
    return added_user
