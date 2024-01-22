import sqlalchemy as sq
from sqlalchemy.orm import declarative_base, relationship, sessionmaker
import psycopg2

Base = declarative_base()


class Like_users(Base):
    __tablename__ = 'like_users'
    id = sq.Column(sq.Integer, primary_key=True)
    name = sq.Column(sq.String(length=60), unique=True)
    surname = sq.Column(sq.String(length=60), unique=True)
    # age = sq.Column(sq.Integer)
    user_id_vk = sq.Column(sq.Integer)

    def __str__(self):
        return self.name


class Image(Base):
    __tablename__ = 'image'
    id = sq.Column(sq.Integer, primary_key=True)
    url = sq.Column(sq.String(length=60), unique=True)

    def __str__(self):
        return self.url


class Info_user(Base):
    __tablename__ = 'info_user'
    id = sq.Column(sq.Integer, primary_key=True)
    user_id = sq.Column(sq.Integer, sq.ForeignKey('like_users.id'), nullable=False)
    image_id = sq.Column(sq.Integer, sq.ForeignKey('image.id'), nullable=False)
    client_id = sq.Column(sq.Integer)
    user = relationship(Like_users, backref='users')
    image = relationship(Image, backref='image')

def create_tables(engine):
    Base.metadata.drop_all(engine)
    Base.metadata.create_all(engine)

