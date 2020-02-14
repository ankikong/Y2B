from utility import getVideo, GetPlayList, BiliUpload, tool, Upload3
import requests
import sqlite3
import json
from utility.conf import parser
from utility import conf
import logging
logger = logging.getLogger("fileLogger")
def run():
    cookie = parser.get("BiliHeader", "Cookie")
    work = GetPlayList.get_work_list()
    for i in work:
        res = Upload3.upload(i, cookie)
        if type(res) == bool:
            continue
        res = json.loads(res)
        if res["code"] != 0:
            logger.error(res["message"])
            continue
        db = sqlite3.connect("data/data.db")
        cur = db.cursor()
        cur.execute("insert into data(vid,aid,title) values('{0}',{1},'{2}');".format(i["id"], res["data"]["aid"], i["title"]))
        cur.close()
        db.commit()
        db.close()
        # break
