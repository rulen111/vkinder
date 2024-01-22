from db.functions import add_info_db
from db.config import session

add_info_db('Sava2', 'Cher2', 1232, 'https://sdfsdf/')
# add_user = Like_users(name='Sava', surname='Cher', user_id_vk=123)
# query = session.query(City.name).all()
# print(query)

session.commit()
session.close()