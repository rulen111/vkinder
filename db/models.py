import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship

Base = declarative_base()


# Client_Favourite = sq.Table(
#     "client_favourite",
#     Base.metadata,
#     sq.Column("client_user_id", sq.ForeignKey("client.user_id"), primary_key=True),
#     sq.Column("favourite_user_id", sq.ForeignKey("favourite.user_id"), primary_key=True),
# )


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
    # favourites: Mapped[List[Favourite]] = relationship(secondary=Client_Favourite)


class Client_Favourite(Base):
    __tablename__ = "client_favourite"

    def __str__(self):
        return self.name

    id = sq.Column(sq.Integer, primary_key=True)
    client_user_id = sq.Column(sq.Integer, sq.ForeignKey('client.user_id'), nullable=False)
    favourite_user_id = sq.Column(sq.Integer, sq.ForeignKey('favourite.user_id'), nullable=False)

    # clients = relationship(Client, backref="favourites")
    # favourites = relationship(Favourite, backref="clients")


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
    q = session.query(Client_Favourite).filter(Client_Favourite.client_user_id == client_user_id, Client_Favourite.favourite_user_id == user_id)
    # q = session.query(Client_Favourite).filter((Client_Favourite.c.client_user_id == client_user_id) &
    #                                            (Client_Favourite.c.favourite_user_id == user_id))

    if q.all():
        raise "Already exists"

    sss = q.all()

    fav_user = Favourite(user_id=user_id, first_name=first_name, last_name=last_name, attachment=attachment)
    session.add(fav_user)
    session.commit()

    client_fav = Client_Favourite(client_user_id=client_user_id, favourite_user_id=user_id)
    session.add(client_fav)

    session.commit()


def get_fav_list(session, client_id):
    q = session.query(Client).filter(Client.user_id == client_id)
    sp = q.all()
    if q.all():
        fav_list = [{
            "first_name": fav.first_name,
            "last_name": fav.last_name,
            "link": f"\nhttps://vk.com/id{fav.user_id}",
            "attachment": fav.attachment
        } for fav in q.all()[0].favourites]

        return fav_list
    else:
        return None


def add_client_info(session, user_id, age, sex, city_id):
    client = Client(user_id=user_id, age=age, sex=sex, city_id=city_id)
    session.add(client)

    session.commit()


def get_client_info(session, user_id):
    q = session.query(Client.age, Client.sex, Client.city_id).join(City.clients).filter(Client.user_id == user_id)

    if q.all()[0]:
        client_info = {
            "city": {"id": q.all()[0].city_id,
                     "title": q.all()[0].title},
            "sex": q.all()[0].sex,
            "age_from": q.all()[0].age,
            "age_to": q.all()[0].age,
        }

        return client_info
    else:
        return None


def add_city_entry(session, city_id, name):
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
            return None

    else:
        q = session.query(City.id, City.name).filter(City.id == city_id)

        if q.all()[0]:
            city = {"id": city_id,
                    "title": q.all()[0].name}

            return city
        else:
            return None
