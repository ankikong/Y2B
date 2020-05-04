import json
import os
import math
import base64
import time
from utility import tool
import threading


def uploadFile(cookie: dict, videoPath: str, enableParallel=False) -> str:
    logger = tool.getLogger()
    file_size = os.path.getsize(videoPath)
    s = tool.Session()
    s.cookies.update(cookie)
    limit: threading.Semaphore = None
    limitCnt = 0

    param = {
        "name": "{}.mp4".format(int(time.time())),
        "size": file_size,
        "r": "upos",
        "profile": "ugcupos/bup",
        "ssl": "0",
        "version": "2.7.1",
        "build": "2070100",
        "upcdn": "tx",
        "probe_version": "20200427",
    }
    url = "https://member.bilibili.com/preupload"
    _data = s.get(url=url, params=param).text
    logger.debug(_data)
    _data = json.loads(_data)
    upload_size = _data["chunk_size"]
    upos_uri = _data["upos_uri"].replace("upos:/", "").replace("/ugc/", "")
    biz_id = _data["biz_id"]
    endpoint = _data["endpoint"]
    auth = _data["auth"]
    if enableParallel:
        limit = threading.Semaphore(_data["threads"])
        limitCnt = _data["threads"]
        logger.info("use parallel upload, count:{}".format(_data["threads"]))

    logger.info("preupload done")
    # get upload id
    data_url = f"https:{endpoint}/ugc/{upos_uri}?uploads&output=json"
    s.headers.update({"X-Upos-Auth": auth})
    # while True:
    #     try:
    #         _data = s.post(url=data_url).json()
    #         upload_id = _data["upload_id"]
    #         break
    #     except (IndexError, KeyError):
    #         time.sleep(2)
    #         continue
    _data = s.post(url=data_url).json()
    upload_id = _data["upload_id"]
    logger.debug(json.dumps(_data))
    logger.info("get upload id done")
    # start upload
    # upload_size = 8 * 1024 * 1024
    upload_url = f"https:{endpoint}/ugc/{upos_uri}"
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

        def threadUpload(url, param, part, s):
            logger = tool.getLogger()
            res = s.put(url=upload_url, params=param,
                        data=part, wantStatusCode=200)
            logger.info(f"{param['partNumber']}/{param['chunks']}:{res.text}")
            limit.release()
        if enableParallel:
            limit.acquire()
            threading.Thread(target=threadUpload, args=(
                upload_url, param.copy(), part, s)).start()
        else:
            res = s.put(url=upload_url, params=param,
                        data=part, wantStatusCode=200)
            logger.info(f"{index - 1}/{total_chunk}:{res.text}")
        restore["parts"].append({"partNumber": index, "eTag": "etag"})
    for _ in range(limitCnt):
        limit.acquire()
    del limit
    file.close()
    # 上传完成
    param = {
        'output': 'json',
        'name': time.ctime() + ".mp4",
        'profile': 'ugcupos/bup',
        'uploadId': upload_id,
        'biz_id': biz_id,
    }
    _data = s.post(upload_url, params=param, json=restore).text
    logger.info(f"upload file done: {upos_uri}")
    logger.debug(_data)
    return upos_uri


def uploadWithOldBvid(cookie: dict, uploadInfo: dict, videoPath: str) -> str:
    logger = tool.getLogger()
    enableParallel = uploadInfo.get("enableParallel", False)
    upos_uri = uploadFile(cookie, videoPath, enableParallel=enableParallel)
    s = tool.Session()
    s.cookies.update(cookie)

    url = f"https://member.bilibili.com/x/vu/web/edit?csrf={cookie['bili_jct']}"

    # s.headers.pop("X-Upos-Auth")
    _rs = s.get(
        f"https://member.bilibili.com/x/web/archive/view?bvid={uploadInfo['bvid']}"
    ).json()["data"]
    # logger.debug(json.dumps(_rs["videos"]))
    videos = []
    for i in _rs["videos"]:
        if len(i['reject_reason']) > 0:  # 判断视频是否有错误，比如撞车、解码错误、违法违规等
            logger.debug(
                "{}-{}:{}".format(i["aid"], i["cid"], i["reject_reason"]))
            continue
        videos.append({"filename": i["filename"], "title": i["title"]})
    videos.append({"filename": upos_uri.split(".")[0],
                   "title": uploadInfo["title"][0:min(79, len(uploadInfo["title"]))],
                   "desc": uploadInfo["id"]
                   })
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
                 "bvid": uploadInfo["bvid"],
                 "handle_staff": False,
                 }
    logger.debug(json.dumps(send_data))
    # s.headers.update({"Content-Type": "application/json;charset=UTF-8"})
    res = s.post(url=url, json=send_data).text
    logger.debug(res)
    return res


def uploadWithNewBvid(cookie: dict, uploadInfo: dict, videoPath: str):
    logger = tool.getLogger()
    enableParallel = uploadInfo.get("enableParallel", False)
    upos_uri = uploadFile(cookie, videoPath, enableParallel=enableParallel)
    s = tool.Session()
    s.cookies.update(cookie)
    csrf = cookie["bili_jct"]

    def cover(csrf, uploadInfo):
        vid = uploadInfo["id"]
        __url = "https://member.bilibili.com/x/vu/web/cover/up"
        __imgURL = f"https://i1.ytimg.com/vi/{vid}/maxresdefault.jpg"
        __rs = s.get(__imgURL, useProxy=True, wantStatusCode=200)
        __send = {"cover": "data:image/jpeg;base64," +
                  base64.b64encode(__rs.content).decode(),
                  "csrf": csrf
                  }
        __res = s.post(url=__url, data=__send).json()

        return __res["data"]["url"].replace("http:", "").replace("https:", "")

    url = "https://member.bilibili.com/x/vu/web/add?csrf=" + csrf
    # s.headers.pop("X-Upos-Auth")
    _data = s.get("https://member.bilibili.com/x/geetest/pre/add").text
    logger.debug(_data)
    send_data = {"copyright": 2, "videos": [{"filename": upos_uri.split(".")[0],
                                             "title": uploadInfo["title"],
                                             "desc": ""}],
                 "source": "https://www.youtube.com/watch?v=" + uploadInfo["id"],
                 "tid": int(uploadInfo["tid"]),
                 "cover": cover(csrf, uploadInfo),
                 "title": uploadInfo["ptitle"],
                 "tag": ','.join(uploadInfo["tags"]),
                 "desc_format_id": 0,
                 "desc": uploadInfo["desc"],
                 "dynamic": "#" + "##".join(uploadInfo["tags"]) + "#",
                 "subtitle": {
                        "open": 0,
                        "lan": ""
    }
    }
    logger.debug(json.dumps(send_data))
    # s.headers.update({"Content-Type": "application/json;charset=UTF-8"})
    res = s.post(url=url, json=send_data).text
    logger.debug(res)
    return res

# if __name__ == "__main__":
#     get_youtube_url2("iCfr8N0Q8IA")
