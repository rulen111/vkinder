import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import psycopg2

Base = declarative_base()


class Like_users(Base):
    __tablename__ = 'like_users'
    id = sq.Column(sq.Integer, primary_key=True)
    name = sq.Column(sq.String(length=60), unique=True)
    age = sq.Column(sq.Integer)

    def __str__(self):
        return self.name


class City(Base):
    __tablename__ = 'city'
    id = sq.Column(sq.Integer, primary_key=True)
    name = sq.Column(sq.String(length=40))
    surname = sq.Column(sq.String(length=40))
    # like_users = sq.Column(sq.Integer, sq.ForeignKey('like_users.id'), nullable=False)

    def __str__(self):
        return self.name


class Image(Base):
    __tablename__ = 'image'
    id = sq.Column(sq.Integer, primary_key=True)
    path = sq.Column(sq.String(length=60), unique=True)

    def __str__(self):
        return self.path


class Info_user(Base):
    __tablename__ = 'info_user'
    id = sq.Column(sq.Integer, primary_key=True)
    user_id = sq.Column(sq.Integer, sq.ForeignKey('like_users.id'), nullable=False)
    city_id = sq.Column(sq.Integer, sq.ForeignKey('city.id'), nullable=False)
    image_id = sq.Column(sq.Integer, sq.ForeignKey('image.id'), nullable=False)
    user = relationship(Like_users, backref='users')
    image = relationship(Image, backref='image')
    city = relationship(City, backref='city')


def create_tables(engine):
    # Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

