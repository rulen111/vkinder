import sqlalchemy
from sqlalchemy.orm import sessionmaker
import create_db

DSN = "postgresql://postgres:postgres@localhost:5432/familiarity_bot"
engine = sqlalchemy.create_engine(DSN)
create_db.create_tables(engine)
con = engine.connect()
Session = sessionmaker(bind=engine)
session = Session()