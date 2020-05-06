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
    db.execute("""CREATE TABLE data(vid text PRIMARY KEY NOT NULL,
                                    bvid text,
                                    zht Boolean DEFAULT 0,
                                    zhs Boolean DEFAULT 0,
                                    en Boolean DEFAULT 0, 
                                    cid text,
                                    title text);""")
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
