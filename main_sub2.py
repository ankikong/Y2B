from utility import Subtitle
import sqlite3
import requests
import time
from utility import tool


def run():
    user = tool.AccountManager("Anki")
    cookie = user.getCookies()
    db = tool.getDB()
    rs = db.execute("select aid,cid,vid,zht,zhs,en from data").fetchall()
    for i in rs:
        if i[1] is None:
            continue
        if i[3] == 0 and Subtitle.send_subtitle(aid=i[0], cid=i[1], vid=i[2], cookie=cookie, lan="zh-CN"):
                db.execute("update data set zht = 1 where cid=(?);", (i[1], ))
                db.commit()
                time.sleep(10)
        if i[4] == 0 and Subtitle.send_subtitle(aid=i[0], cid=i[1], vid=i[2], cookie=cookie, lan="zh-TW"):
                db.execute("update data set zhs = 1 where cid=(?);", (i[1], ))
                db.commit()
                time.sleep(10)
        if i[5] == 0 and Subtitle.send_subtitle(aid=i[0], cid=i[1], vid=i[2], cookie=cookie, lan="en-US"):
                db.execute("update data set en = 1 where cid=(?);", (i[1], ))
                db.commit()
                time.sleep(10)
    Subtitle.fix_sub(cookie=cookie)

if __name__ == "__main__":
    run()

