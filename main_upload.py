from utility import getVideo, GetPlayList, Upload3
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
        videoUrl = getVideo.getVideoUrl3(i["id"])
        dmer = tool.DownloadManager(url=videoUrl, proxy=proxy, files=i["id"])
        dmer.download()
        if dmer.waitForFinishing() == 1:
            # res = Upload3.upload(i, account, dmer)
            res = Upload3.upload(account.getCookies(), i, dmer.telFileLocate())
            if type(res) == bool:
                continue
            res = json.loads(res)
            if res["code"] != 0:
                logger.error(res["message"])
                continue
            with tool.getDB() as db:
                db.execute("insert into data(vid,aid,title) values(?,?,?);", (i["id"], res["data"]["aid"], i["title"]))
                db.commit()
            logger.info("finished")
            dmer.deleteFile()
        else:
            logger.info("download failed")
