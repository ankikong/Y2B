from utility import tool
import time
import sqlite3
import datetime
from urllib import parse
import os
from datetime import timezone

api1 = "https://member.bilibili.com/x/web/archive/view?history=&bvid={}"

old = "data/data.db"
nw = "data/nw.db"

con1 = sqlite3.connect(old)
con2 = sqlite3.connect(nw)
s = tool.Session()
s.cookies.update(tool.AccountManager("Anki").getCookies())

try:
    con2.execute('''
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
    )
    ''')
except:
    pass
sql = '''
insert into data(vid, zht, zhs, en, subtime, filename, bvid, title)
            values(?,?,?,?,?,?,?,?)
'''

fCnt = 0

rs1 = con1.execute("select distinct bvid from data;").fetchall()

for i in rs1:
    bvid = i[0]
    url = api1.format(bvid)
    res = s.get(url).json()["data"]["videos"]
    for j in res:
        subtime = j["ctime"]
        cid = j["cid"]
        title = j["title"]
        title = parse.unquote(title)

        filename = j["filename"]
        if con1.execute("select count(*) from data where bvid=?", (bvid, )).fetchone()[0] == 1:
            rs2 = con1.execute(
                "select vid, zht, zhs, en from data where bvid=?", (bvid, )).fetchone()
        else:
            rs2 = con1.execute(
                "select vid, zht, zhs, en from data where title=? or vid=?", (title, title)).fetchone()
        if rs2 is None:  # 未知错误
            print("未知错误", bvid, cid, title)
            fCnt += 1
            continue
        print(bvid, cid, title, rs2[0])
        values = rs2 + (subtime, filename, bvid, title)
        try:
            con2.execute(sql, values)
        except Exception as e:
            fCnt += 1
            print(e)
con2.commit()

rs1 = con1.execute("select vid from data").fetchall()

cnt: int = 0
cnts: int = len(rs1)

while cnt < cnts:
    query = []
    limit = 0
    while cnt < cnts and limit < 49:
        limit += 1
        query.append(rs1[cnt][0])
        cnt += 1
    api2 = "https://www.googleapis.com/youtube/v3/videos"
    params = {
        "id": ",".join(query),
        "part": "snippet",
        "key": tool.settingConf["GoogleToken"]
    }
    rs2 = s.get(api2, params=params, useProxy=True).json()["items"]
    for i in rs2:
        vid = i["id"]
        ts = i["snippet"]["publishedAt"]
        try:
            ts = datetime.datetime.strptime(
                ts, "%Y-%m-%dT%H:%M:%SZ")+datetime.timedelta(hours=8)
        except:
            ts = datetime.datetime.strptime(
                ts, "%Y-%m-%dT%H:%M:%S.%fZ")+datetime.timedelta(hours=8)
        ts = ts.replace(tzinfo=timezone.utc).timestamp()
        con2.execute("update data set stime=? where vid=?", (ts, vid))

con1.commit()
con2.commit()

con1.close()
con2.close()

print("失败个数：", fCnt)

del con1
del con2

os.rename(old, f"data/{time.time()}")
os.rename(nw, old)

