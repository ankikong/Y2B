from utility import Subtitle
import sqlite3
import requests
import time
from utility.conf import parser, channel, channels
api = "https://member.bilibili.com/x/web/archive/view?aid={}&history="
db = sqlite3.connect("data/data.db")
cur = db.cursor()


def run():
    rs = cur.execute("select aid,cid,vid,zht,zhs,en from data").fetchall()
    for i in rs:
        if i[1] is None:
            continue
        if i[3] == 0 and Subtitle.send_subtitle(aid=i[0], cid=i[1], vid=i[2], lan="zh-CN"):
                cur.execute("update data set zht = 1 where cid=(?);", (i[1], ))
                db.commit()
                time.sleep(10)
        if i[4] == 0 and Subtitle.send_subtitle(aid=i[0], cid=i[1], vid=i[2], lan="zh-TW"):
                cur.execute("update data set zhs = 1 where cid=(?);", (i[1], ))
                db.commit()
                time.sleep(10)
        if i[5] == 0 and Subtitle.send_subtitle(aid=i[0], cid=i[1], vid=i[2], lan="en-US"):
                cur.execute("update data set en = 1 where cid=(?);", (i[1], ))
                db.commit()
                time.sleep(10)
    Subtitle.fix_sub()

        

