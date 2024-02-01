import yaml
import sqlalchemy as sq
from sqlalchemy.orm import sessionmaker

import db.models as models

with open("config.yaml") as c:
    config = yaml.full_load(c)

# Make DSN string
DSN = (f'{config["DB"]["PROTOCOL"]}://{config["DB"]["USER"]}:'
       f'{config["DB"]["PASSWORD"]}@{config["DB"]["SERVER"]}:'
       f'{config["DB"]["PORT"]}/{config["DB"]["NAME"]}')

# Initialize Engine object
engine = sq.create_engine(DSN)

# Drop existing tables and create them again
models.drop_tables(engine)
models.create_tables(engine)

Session = sessionmaker(bind=engine)
session = Session()

session.commit()
# session.close()
