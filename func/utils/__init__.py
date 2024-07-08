import logging
import datetime
import os

if not os.path.exists("./logs"):
    os.makedirs("./logs")

logging.basicConfig(level=logging.INFO, filename=f'logs/{datetime.datetime.now().date()}.log',
                    filemode="a", format="%(asctime)s %(levelname)s %(message)s", encoding='UTF-8')
logging.info("-" * 80)
logging.warning(f"Starting VKinder Bot")
logging.info("-" * 80)
