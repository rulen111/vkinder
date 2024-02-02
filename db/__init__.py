import yaml
import sqlalchemy as sq
from sqlalchemy.orm import sessionmaker

from db.models import create_tables

with open("config.yaml") as c:
    config = yaml.full_load(c)

DSN = (f'{config["DB"]["PROTOCOL"]}://{config["DB"]["USER"]}:'
       f'{config["DB"]["PASSWORD"]}@{config["DB"]["SERVER"]}:'
       f'{config["DB"]["PORT"]}/{config["DB"]["NAME"]}')

engine = sq.create_engine(DSN)
create_tables(engine)

Session = sessionmaker(bind=engine)
session = Session()

session.commit()
