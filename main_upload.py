from utility import getVideo, GetPlayList, Upload
import json
from utility import tool
from queue import Queue
import threading
from utility.platform.factory import VideoFactory

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
    account = tool.QRLogin()
    for i in work:
        logger.debug(json.dumps(i))
        logger.info("start: vid[{}], 1080P[{}], Multipart[{}]".format(
            i["id"], i["hd"], i["multipart"]))
        vmer = getVideo.VideoManager(i["id"], i["hd"])
        data = vmer.getVideo()
        if data[0]:
            if i["multipart"]:
                success, res, upos_uri = Upload.uploadWithOldBvid(
                    account.getCookies(), i, data[1])
            else:
                success, res, upos_uri = Upload.uploadWithNewBvid(
                    account.getCookies(), i, data[1])
            if not success:
                continue
            upos_uri = upos_uri.split(".")[0]
            res = json.loads(res)
            if res["code"] != 0:
                logger.error(res["message"])
                continue
            with tool.getDB() as db:
                db.execute("insert into data(vid,bvid,title,filename) values(?,?,?,?);",
                           (i["id"], res["data"]["bvid"], i["title"], upos_uri))
                db.commit()
            logger.info(f"finished, bvid[{res['data']['bvid']}]")
            vmer.deleteFile()
        else:
            logger.error("download failed")


def jobProducer():
    logger = tool.getLogger()
    logger.debug("start video Producer")
    channel = tool.channelConf
    db = tool.getDB()
    workList = []
    for i in channel.data:
        per = channel[i]
        plat = per["platform"]
        bean = VideoFactory.getBean(plat)
        workList += bean.GetVideos(per, tool.settingConf["Platform"][plat])
    try:
        cnt = 0
        for i in workList:
            video_id = i.channelParam["id"]
            db_res = db.execute(
                "select count(vid) from data where vid=?;", (video_id, )).fetchone()[0]
            if int(db_res) != 0:
                # print(video_id)
                continue
            if unique.checkAndInsert(video_id):
                cnt += 1
                buffer.put(i, block=True)
        logger.info(
            f"new: {cnt}, sum: {unique.size()}, rest: {buffer.qsize()}")
    except Exception:
        logger = tool.getLogger()
        logger.error(f"upload-P", exc_info=True)
    db.close()
    # logger.info("finish video Producer")


def __consume():
    account = tool.QRLogin()
    logger = tool.getLogger()
    logger.debug("start video Consumer")
    proxy = tool.settingConf["Proxy"]
    while True:
        i = buffer.get(block=True)
        channelInfo = i.channelParam
        logger.debug(json.dumps(channelInfo))
        logger.info("start: vid[{}], Multipart[{}]".format(
            channelInfo["id"], channelInfo["multipart"]))
        # vmer = getVideo.VideoManager(i["id"], i["hd"])
        data = i.download(proxy)

        if data:
            fpath = i.path()
            if len(fpath) <= 0:
                continue
            if channelInfo["multipart"]:
                success, res, upos_uri = Upload.uploadWithOldBvid(
                    account.getCookies(), channelInfo, fpath)
            else:
                success, res, upos_uri = Upload.uploadWithNewBvid(
                    account.getCookies(), channelInfo, fpath)
            if not success:
                continue
            upos_uri = upos_uri.split(".")[0]
            res = json.loads(res)
            if res["code"] != 0:
                logger.error(res["message"])
                continue
            with tool.getDB() as db:
                db.execute("insert into data(vid,bvid,title,filename) values(?,?,?,?);",
                           (channelInfo["id"], res["data"]["bvid"], channelInfo["title"], upos_uri))
                db.commit()
            logger.info(f"finished, bvid[{res['data']['bvid']}]")
            i.deleteFile()
        else:
            logger.error("download failed")


def jobConsumer():
    global tid
    if tid is None or not tid.is_alive():
        tid = tool.Thread(target=__consume)
        tid.start()
