from utility import Subtitle
import sqlite3
import requests
import time
from utility import tool

# 遗留代码，不想改了
def send(i, cookie):
    db = tool.getDB()
    if i[3] == 0 and Subtitle.send_subtitle(bvid=i[0], cid=i[1], vid=i[2], cookie=cookie, lan="zh-CN"):
        db.execute("update data set zht = 1 where cid=(?);", (i[1], ))
        db.commit()
        time.sleep(10)
    if i[4] == 0 and Subtitle.send_subtitle(bvid=i[0], cid=i[1], vid=i[2], cookie=cookie, lan="zh-TW"):
        db.execute("update data set zhs = 1 where cid=(?);", (i[1], ))
        db.commit()
        time.sleep(10)
    if i[5] == 0 and Subtitle.send_subtitle(bvid=i[0], cid=i[1], vid=i[2], cookie=cookie, lan="en-US"):
        db.execute("update data set en = 1 where cid=(?);", (i[1], ))
        db.commit()
        time.sleep(10)
    db.close()

def run():
    user = tool.AccountManager("Anki")
    cookie = user.getCookies()
    db = tool.getDB()
    rs = db.execute("select distinct bvid from data where zht=false or zhs=false or en=false limit 50;").fetchall()
    api = "https://api.bilibili.com/x/player/pagelist?bvid="
    s = tool.Session()
    s.cookies.update(cookie)
    for bvid in rs:
        bvid = bvid[0]
        pages = s.get(api + bvid).json()
        if pages["code"] != 0:
            # db.execute("delete from data where bvid=?", (bvid, ))
            continue
        pages = pages["data"]
        vid = db.execute("select vid,zht,zhs,en from data where bvid=?", (bvid, )).fetchone()
        if len(pages) == 1: # 不分P视频
            send((bvid, pages[0]["cid"]) + vid, cookie)
            continue
        for i in pages:     # 分P视频
            title = i["part"]
            vid = db.execute("select vid,zht,zhs,en from data where title=?", (title, )).fetchone()
            if vid is None or len(vid) == 0:
                continue
            send((bvid, i["cid"]) + vid, cookie)
    Subtitle.fix_sub(cookie=cookie)
        
    # for i in pages:

    #     if i[1] is None:
    #         continue
    #     if i[3] == 0 and Subtitle.send_subtitle(bvid=i[0], cid=i[1], vid=i[2], cookie=cookie, lan="zh-CN"):
    #         db.execute("update data set zht = 1 where cid=(?);", (i[1], ))
    #         db.commit()
    #         time.sleep(10)
    #     if i[4] == 0 and Subtitle.send_subtitle(bvid=i[0], cid=i[1], vid=i[2], cookie=cookie, lan="zh-TW"):
    #         db.execute("update data set zhs = 1 where cid=(?);", (i[1], ))
    #         db.commit()
    #         time.sleep(10)
    #     if i[5] == 0 and Subtitle.send_subtitle(bvid=i[0], cid=i[1], vid=i[2], cookie=cookie, lan="en-US"):
    #         db.execute("update data set en = 1 where cid=(?);", (i[1], ))
    #         db.commit()
    #         time.sleep(10)

if __name__ == "__main__":
    run()

