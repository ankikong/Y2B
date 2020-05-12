import sqlite3
import os


try:
    os.mkdir("data")
except:
    pass

try:
    os.mkdir("logs")
except:
    pass

db = sqlite3.connect("data/data.db")
try:
    db.execute("""
    create table data (
            zht Boolean DEFAULT 0,
            zhs Boolean DEFAULT 0,
            en Boolean DEFAULT 0,
            needSubtitle Boolean DEFAULT 1,
            deleted Boolean DEFAULT 0,
            stime timestamp DEFAULT 0,
            subtime timestamp DEFAULT 0,
            errorcode int DEFAULT 0,
            vid text PRIMARY KEY NOT NULL,
            filename text,
            bvid text,
            cid text,
            title text,
            platform text DEFAULT 'ytb'
    )""")
except:
    pass

db.commit()

if not os.path.exists("conf/channel.yaml"):
    with open("conf/channel.yaml", "w", encoding="utf8") as out:
        with open("conf/channel_ex.yaml", "r", encoding="utf8") as ins:
            out.write(ins.read())

if not os.path.exists("conf/setting.yaml"):
    with open("conf/setting.yaml", "w", encoding="utf8") as out:
        with open("conf/setting_ex.yaml", "r", encoding="utf8") as ins:
            out.write(ins.read())
