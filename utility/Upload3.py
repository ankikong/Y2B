# Upload3.py 是把每个视频作为一个视频合集发布，即一个av下
# 会有很多个cid
# 因为需要av号，所以第一个视频必须手动上传并配置好封面等信息
# 与Upload2的区别在于：Upload3改为使用aria2下载完视频到硬盘后再上传
import requests
import json
import re
import os
import math
import base64
import time
import urllib3
import logging
from utility.getVideo import GetVideo
from utility import tool
logger = logging.getLogger("fileLogger")
urllib3.disable_warnings()
proxies = {"http": "http://127.0.0.1:10809", "https": "http://127.0.0.1:10809"}
# proxies = None

# def upload(videoInfo:dict, accountInfo:tool.AccountManager, dmer:tool.DownloadManager):

def upload(cookie:dict, uploadInfo:dict, videoPath:str):

    file_size = os.path.getsize(videoPath)
    s = requests.session()

    for i in cookie.keys():
        s.cookies.set(i, cookie[i])

    param = {
            "os": "upos",
            "upcdn": "ws",
            "name": "{}.mp4".format(int(time.time())),
            "size": file_size,
            "r": "upos",
            "profile": "ugcupos/yb",
            "ssl": "0",
            "version": "2.6.4",
            "build": "2060400",
    }
    url = "https://member.bilibili.com/preupload"
    _data = s.get(url=url, params=param).text
    _data = json.loads(_data)
    upos_uri = _data["upos_uri"].replace("upos:/", "").replace("/ugc/", "")
    biz_id = _data["biz_id"]
    endpoint = _data["endpoint"]
    auth = _data["auth"]
    logger.info("preupload done")
    #get upload id
    data_url = "https:{1}/ugc/{0}?uploads&output=json".format(upos_uri, endpoint)
    s.headers.update({"X-Upos-Auth": auth})
    while True:
        try:
            _data = s.post(url=data_url).json()
            upload_id = _data["upload_id"]
            break
        except (IndexError, KeyError):
            time.sleep(2)
            continue
    logger.info("get upload id done")
    # start upload
    upload_size = 4 * 1024 * 1024
    upload_url = "https:{0}/ugc/{1}".format(endpoint, upos_uri)
    total_chunk = math.ceil(file_size / upload_size)
    index = 1
    now_size = 0
    restore = {"parts": []}

    file = open(videoPath, "rb")
    # 分块下载&上传
    while now_size < file_size:
        new_end = min(now_size + upload_size, file_size - 1)
        part = file.read(upload_size)
        size = len(part)
        param = {
            "total": file_size,
            "partNumber": index,
            "uploadId": upload_id,
            "chunk": index - 1,
            "chunks": total_chunk,
            "size": size,
            "start": now_size,
            "end": new_end
        }
        now_size = new_end + 1
        index += 1
        while True:
            res = s.put(url=upload_url, params=param, data=part)
            if res.status_code == 200:
                res = res.text
                break
            time.sleep(10)
            logger.debug("{}/{}: failed".format(index, total_chunk))
        restore["parts"].append({"partNumber": index, "eTag": "etag"})
        logger.debug("{}/{}:".format(index, total_chunk) + res)
    file.close()
    # 上传完成
    param = {
        'output': 'json',
        'name': time.ctime() + ".mp4",
        'profile': 'ugcupos/yb',
        'uploadId': upload_id,
        'biz_id': biz_id,
        # 'access_key': accountInfo.getToken()
    }
    _data = s.post(upload_url, params=param, data=json.dumps(restore)).text
    logger.debug(_data)

    url = "https://member.bilibili.com/x/vu/web/edit?csrf=" + cookie["bili_jct"]
    s.headers.pop("X-Upos-Auth")
    _rs = s.get("https://member.bilibili.com/x/web/archive/view?aid={}".format(uploadInfo["av"])).json()["data"]
    videos = []
    for i in _rs["videos"]:
        if len(i['reject_reason']) > 0: # 判断视频是否有错误，比如撞车、解码错误、违法违规等
            logger.info("{}-{}:{}".format(i["aid"], i["cid"], i["reject_reason"]))
            continue
        videos.append({"filename": i["filename"], "title": i["title"]})
    videos.append({"filename": upos_uri.split(".")[0], "title": uploadInfo["title"][0:min(79, len(uploadInfo["title"]))], "desc": uploadInfo["id"]})
    send_data = {"copyright": 2, "videos": videos,
                    "source": _rs["archive"]["source"],
                    "tid": _rs["archive"]["tid"],
                    "cover": _rs["archive"]["cover"].split(":")[-1],
                    "title": _rs["archive"]["title"],
                    "tag": _rs["archive"]["tag"],
                    "desc_format_id": 0,
                    "desc": _rs["archive"]["desc"],
                    "dynamic": _rs["archive"]["dynamic"],
                    "subtitle": {
                        "open": 0,
                        "lan": ""
                    },
                    "aid": int(uploadInfo["av"]),
                    "handle_staff": False,
                }
    logger.debug(json.dumps(send_data))
    s.headers.update({"Content-Type": "application/json;charset=UTF-8"})
    res = s.post(url=url, json=send_data).text
    logger.debug(res)
    return res

# if __name__ == "__main__":
#     get_youtube_url2("iCfr8N0Q8IA")
