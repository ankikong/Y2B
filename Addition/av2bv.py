import requests
import sqlite3
import os
import time

api = "https://api.bilibili.com/x/web-interface/archive/stat?aid={}"

db = sqlite3.connect("data/data2.db")
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

db2 = sqlite3.connect("data/data.db")
s = requests.session()
s.headers.update({
    "Display-ID": "XZDA0A8D4BE3EA66CA7BA1C05CB00E8A56143-1584023167",
    "Buvid": "XZDA0A8D4BE3EA66CA7BA1C05CB00E8A56143",
    "User-Agent": "Mozilla/5.0 BiliDroid/5.39.0 (bbcallen@gmail.com)",
    "Device-ID": "KREhESMUJxAnQ3FBPUE6Rz8OaV1vDHwWcg",
    # "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
    "Accept-Encoding": "gzip",
})
cache = {}

rs = db2.execute("select aid, vid, zht, zhs, en, cid, title from data;").fetchall()
for i in rs:
    bid = cache.get(i[0], None)
    if bid is None:
        try:
            bid = s.get(api.format(i[0])).json()
            bid = bid["data"]["bvid"]
            if bid is None: # 视频被删了，那就直接pass
                continue
        except:
            continue
    cache[i[0]] = bid
    db.execute("insert into data(bvid, vid, zht, zhs, en, cid, title) values (?,?,?,?,?,?,?)", (bid, ) + i[1:])
    print(i[0], bid)
    time.sleep(1)

db.commit()
db.close()
db2.close()

os.rename("data/data.db", f"data/{time.time()}.db")
os.rename("data/data2.db", "data/data.db")
