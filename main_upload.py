from utility import getVideo, GetPlayList, Upload
import json
from utility import tool
from queue import Queue
import threading

# 生产者-消费者模型
buffer = Queue()
# 全局唯一访问
unique = tool.UniquePool()
# 消费者线程
tid: threading.Thread = None


def run():
    # {"title": tmp_data["title"], "id": video_id, "av": _["av"]}
    work = GetPlayList.get_work_list()
    logger = tool.getLogger()
    account = tool.AccountManager("Anki")
    for i in work:
        logger.debug(json.dumps(i))
        logger.info("start: vid[{}], 1080P[{}], Multipart[{}]".format(
            i["id"], i["hd"], i["multipart"]))
        vmer = getVideo.VideoManager(i["id"], i["hd"])
        data = vmer.getVideo()
        if data[0]:
            if i["multipart"]:
                res = Upload.uploadWithOldBvid(
                    account.getCookies(), i, data[1])
            else:
                res = Upload.uploadWithNewBvid(
                    account.getCookies(), i, data[1])
            if type(res) == bool:
                continue
            res = json.loads(res)
            if res["code"] != 0:
                logger.error(res["message"])
                continue
            with tool.getDB() as db:
                db.execute("insert into data(vid,bvid,title) values(?,?,?);",
                           (i["id"], res["data"]["bvid"], i["title"]))
                db.commit()
            logger.info(f"finished, bvid[{res['data']['bvid']}]")
            vmer.deleteFile()
        else:
            logger.error("download failed")


def jobProducer():
    logger = tool.getLogger()
    logger.debug("start video Producer")
    try:
        workList = GetPlayList.get_work_list()
        cnt = 0
        for i in workList:
            if unique.checkAndInsert(i["id"]):
                cnt += 1
                buffer.put(i, block=True)
        logger.info(
            f"new: {cnt}, sum: {unique.size()}, rest: {buffer.qsize()}")
    except Exception:
        logger = tool.getLogger()
        logger.error(f"upload-P", exc_info=True)
    # logger.info("finish video Producer")


def __consume():
    account = tool.AccountManager("Anki")
    logger = tool.getLogger()
    logger.debug("start video Consumer")
    while True:
        i = buffer.get(block=True)
        logger.debug(json.dumps(i))
        logger.info("start: vid[{}], 1080P[{}], Multipart[{}]".format(
            i["id"], i["hd"], i["multipart"]))
        vmer = getVideo.VideoManager(i["id"], i["hd"])
        data = vmer.getVideo()
        if data[0]:
            logger.info("download done")
            cookie = account.getCookies()
            logger.info("get cookie done")
            if i["multipart"]:
                res = Upload.uploadWithOldBvid(
                    cookie, i, data[1])
            else:
                res = Upload.uploadWithNewBvid(
                    cookie, i, data[1])
            if type(res) == bool:
                continue
            res = json.loads(res)
            if res["code"] != 0:
                logger.error(res["message"])
                unique.remove(i["id"])
                continue
            with tool.getDB() as db:
                db.execute("insert into data(vid,bvid,title) values(?,?,?);",
                           (i["id"], res["data"]["bvid"], i["title"]))
                db.commit()
            logger.info(f"finished, bvid[{res['data']['bvid']}]")
            vmer.deleteFile()
        else:
            logger.error("download failed")
            unique.remove(i["id"])


def jobConsumer():
    global tid
    if tid is None or not tid.is_alive():
        tid = tool.Thread(target=__consume)
        tid.start()
