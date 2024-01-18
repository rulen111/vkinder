import sqlalchemy
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
import psycopg2

from create_db import *

DSN = "postgresql://postgres:postgres@localhost:5432/familiarity_bot"
engine = sqlalchemy.create_engine(DSN)
create_tables(engine)
con = engine.connect()

Session = sessionmaker(bind=engine)
session = Session()

query = session.query(City.name).all()
print(query)

session.commit()
session.close()