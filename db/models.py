import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


class Favourite(Base):
    __tablename__ = "favourite"

    def __str__(self):
        return self.name

    user_id = sq.Column(sq.Integer, primary_key=True)
    first_name = sq.Column(sq.String(length=30))
    last_name = sq.Column(sq.String(length=30))
    attachment = sq.Column(sq.String(length=90), unique=True, nullable=False)

    clients = relationship('Client', secondary='client_favourite', back_populates='favourites')


class Client(Base):
    __tablename__ = "client"

    def __str__(self):
        return self.name

    user_id = sq.Column(sq.Integer, primary_key=True)
    age = sq.Column(sq.String(length=6), nullable=False)
    sex = sq.Column(sq.SmallInteger(), nullable=False)
    city_id = sq.Column(sq.Integer, sq.ForeignKey('city.id'), nullable=False)

    favourites = relationship('Favourite', secondary='client_favourite', back_populates='clients')


class Client_Favourite(Base):
    __tablename__ = "client_favourite"

    def __str__(self):
        return self.name

    id = sq.Column(sq.Integer, primary_key=True)
    client_user_id = sq.Column(sq.Integer, sq.ForeignKey('client.user_id'), nullable=False)
    favourite_user_id = sq.Column(sq.Integer, sq.ForeignKey('favourite.user_id'), nullable=False)


class City(Base):
    __tablename__ = 'city'

    def __str__(self):
        return self.name

    id = sq.Column(sq.Integer, primary_key=True)
    name = sq.Column(sq.String(length=40))

    clients = relationship(Client, backref='city')


def create_tables(engine):
    """
    Creates all tables using defined structure
    :param engine: sqlalchemy Engine object
    :return: None
    """
    Base.metadata.create_all(engine)


def drop_tables(engine):
    """
    Deletes all tables from DB
    :param engine: sqlalchemy Engine object
    :return: None
    """
    Base.metadata.drop_all(engine)


def add_fav_entry(session, client_user_id, user_id, first_name, last_name, attachment):
    q = session.query(Client_Favourite).filter(Client_Favourite.client_user_id == client_user_id,
                                               Client_Favourite.favourite_user_id == user_id)
    if q.all():
        raise f"(Client_Favourite) Entry client[{client_user_id}] - fav[{user_id}] already exists in target DB."

    q = session.query(Favourite).filter(Favourite.user_id == user_id)
    if q.all():
        pass
    else:
        fav_user = Favourite(user_id=user_id, first_name=first_name, last_name=last_name, attachment=attachment)
        session.add(fav_user)
        session.commit()

    client_fav = Client_Favourite(client_user_id=client_user_id, favourite_user_id=user_id)
    session.add(client_fav)
    session.commit()


def get_fav_list(session, client_id):
    q = session.query(Client).filter(Client.user_id == client_id)
    if q.all():
        if q.all()[0].favourites:
            fav_list = [{
                "first_name": fav.first_name,
                "last_name": fav.last_name,
                "link": f"\nhttps://vk.com/id{fav.user_id}",
                "attachment": fav.attachment
            } for fav in q.all()[0].favourites]

            return fav_list
        else:
            raise f"There is no single entry in client's id[{client_id}] favourites."
    else:
        raise f"(Client) There is no entry with client's id[{client_id}]."


def add_client_info(session, user_id, age, sex, city_id):
    # q = session.query(Client).filter(Client.user_id == user_id)
    # if q.all():
    #     raise f"(Client) Entry client[{user_id}] already exists in target DB."
    # else:
    client = Client(user_id=user_id, age=age, sex=sex, city_id=city_id)
    session.merge(client)
    session.commit()


def get_client_info(session, user_id):
    q = session.query(Client).join(City.clients).filter(Client.user_id == user_id)
    if q.one():
        client_info = {
            "city": {"id": q.all()[0].city_id,
                     "title": q.all()[0].title},
            "sex": q.all()[0].sex,
            "age_from": q.all()[0].age,
            "age_to": q.all()[0].age,
        }

        return client_info
    else:
        raise f"(Client) There is no entry with client's id[{user_id}]."


def add_city_entry(session, city_id, name):
    q = session.query(City).filter(City.id == city_id)
    if q.all():
        raise f"(City) Entry city[{name}] already exists in target DB."
    else:
        city = City(id=city_id, name=name)
        session.add(city)
        session.commit()


def get_city_entry(session, city_id, name=None):
    if name:
        q = session.query(City.id, City.name).filter(City.name == name)
        if q.all()[0]:
            city = {"id": q.all()[0].id,
                    "title": name}

            return city
        else:
            raise f"(City) There is no entry with name[{name}]."
    else:
        q = session.query(City.id, City.name).filter(City.id == city_id)
        if q.all()[0]:
            city = {"id": city_id,
                    "title": q.all()[0].name}

            return city
        else:
            raise f"(City) There is no entry with id[{city_id}]."
