from utility import getVideo, GetPlayList, Upload4
import requests
import sqlite3
import json
from utility import tool
import logging
logger = logging.getLogger("fileLogger")

def run():
    # {"title": tmp_data["title"], "id": video_id, "av": _["av"]}
    parser = tool.getSettingConf()
    work = GetPlayList.get_work_list()
    logger.info(json.dumps(work))
    proxy = dict(parser.items("Proxy"))
    account = tool.AccountManager("Anki")
    for i in work:
        logger.info("start:" + json.dumps(i))
        videoUrl = getVideo.getVideoUrl(i["id"])
        if len(videoUrl) == 0:
            continue
        dmer = tool.DownloadManager(url=videoUrl, proxy=proxy, files=i["id"])
        dmer.download()
        if dmer.waitForFinishing() == 1:
            # res = Upload3.upload(i, account, dmer)
            if i["multipart"] == "1":
                res = Upload4.uploadWithOldBvid(account.getCookies(), i, dmer.telFileLocate())
            else:
                res = Upload4.uploadWithNewBvid(account.getCookies(), i, dmer.telFileLocate())
            # res = Upload3.upload(account.getCookies(), i, dmer.telFileLocate())
            if type(res) == bool:
                continue
            res = json.loads(res)
            if res["code"] != 0:
                logger.error(res["message"])
                continue
            with tool.getDB() as db:
                db.execute("insert into data(vid,bvid,title) values(?,?,?);", (i["id"], res["data"]["bvid"], i["title"]))
                db.commit()
            logger.info("finished")
            dmer.deleteFile()
        else:
            logger.info("download failed")
