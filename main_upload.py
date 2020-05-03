from utility import getVideo, GetPlayList, Upload
import requests
import sqlite3
import json
from utility import tool
import logging
logger = logging.getLogger("fileLogger")

def run():
    # {"title": tmp_data["title"], "id": video_id, "av": _["av"]}
    work = GetPlayList.get_work_list()
    account = tool.AccountManager("Anki")
    for i in work:
        logger.debug(json.dumps(i))
        logger.info("start: vid[{}], 1080P[{}], Multipart[{}]".format(i["id"], i["hd"], i["multipart"]))
        vmer = getVideo.VideoManager(i["id"], i["hd"])
        data = vmer.getVideo()
        if data[0]:
            if i["multipart"]:
                res = Upload.uploadWithOldBvid(account.getCookies(), i, data[1])
            else:
                res = Upload.uploadWithNewBvid(account.getCookies(), i, data[1])
            if type(res) == bool:
                continue
            res = json.loads(res)
            if res["code"] != 0:
                logger.error(res["message"])
                continue
            with tool.getDB() as db:
                db.execute("insert into data(vid,bvid,title) values(?,?,?);", (i["id"], res["data"]["bvid"], i["title"]))
                db.commit()
            logger.info("finished, bvid[{}]".format(res["data"]["bvid"]))
            vmer.deleteFile()
        else:
            logger.error("download failed")
