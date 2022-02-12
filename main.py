import datetime
import json
import logging
import os
import time
import uuid
import requests
import feedparser
import pandas as pd
import pytz
from dotmap import DotMap
from sqlalchemy import Column, String, create_engine
from sqlalchemy.dialects.postgresql import JSON
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

logging.basicConfig(
    filename="./logs/scraper.log",
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s - %(message)s",
    datefmt="%H:%M:%S",
)


start_time = time.time()
timestamp = datetime.datetime.now().timestamp()
intz = pytz.timezone("Asia/Kolkata")
nowdt = datetime.datetime.now(intz).strftime("%d%m%Y%H%M")

DB_URL = os.getenv("DB_URL")
CERT_URL = os.getenv("CERT_URL")

r = requests.get(CERT_URL)
with open("root.crt", "wb") as f:
    f.write(r.content)
# os.chmod("root.crt", 0o644)

with open("./config/news_url.json", "r") as file:
    config = json.load(file)

config = DotMap(config)


def scraper(url):
    d = feedparser.parse(url)
    df_dict = {}
    df_dict["index"] = [uuid.uuid4().hex]
    df_dict["ist"] = str(nowdt)
    df_dict["timestamp"] = str(timestamp)
    df_dict["data"] = json.dumps(d)
    df = pd.DataFrame.from_dict(df_dict)
    return df


records_df = pd.DataFrame()
for url in config.websites.thenewsminute:
    data = scraper(url)
    records_df = pd.concat([records_df, data], axis=0)
records = records_df.to_dict(orient="records")

db = create_engine(DB_URL)
base = declarative_base()


class RssFeed(base):
    __tablename__ = "daily_rss_feed"

    index = Column(String, primary_key=True)
    ist = Column(String)
    timestamp = Column(String)
    data = Column(JSON)


Session = sessionmaker(db)
base.metadata.create_all(db)

with Session.begin() as session:
    for record in records:
        session.add(RssFeed(**record))
    session.commit()


logging.info(f"scraping total time {time.time() - start_time}")

# save_filename = f"feed_{nowdt}.csv"

# if not os.path.exists("./data"):
#     os.makedirs("./data")

# records_df.to_csv(f"./data/{save_filename}")
