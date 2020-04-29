# Upload2.py 是把每个视频作为一个视频合集发布，即一个av下
# 会有很多个cid
# 因为需要av号，所以第一个视频必须手动上传并配置好封面等信息
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
logger = logging.getLogger("fileLogger")
urllib3.disable_warnings()
proxies = {"http": "http://127.0.0.1:10809", "https": "http://127.0.0.1:10809"}
# proxies = None

def get_youtube_url(vid):
    url = "https://www.youtube.com/watch?v=" + vid
    header = {"Content-Type": "application/x-www-form-urlencoded", 
                "Origin": "null",
                "content-type": "application/x-www-form-urlencoded",
                "accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8",
                "accept-encoding": "gzip, deflate, br",
                }
    s = requests.post("http://www.lilsubs.com/", data={"url": url}, headers=header).text
    s = s.split('<h3>Download Links</h3>')[1].split('HD720 Video')[0]
    s = re.findall('href="(.*?)"', s)[0]
    logger.debug(s)
    return s

def get_youtube_url2(vid):
    url = "https://www.findyoutube.net"
    s = requests.session()
    s.proxies = proxies
    s.headers.update({
        "origin": "https://www.findyoutube.net",
        "referer": "https://www.findyoutube.net/"
    })
    rs = s.get(url).text
    csrf = re.findall('csrf_token" type="hidden" value="([^"]+)', rs)[0]
    post = {
        "url": "https://www.youtube.com/watch?v=" + vid,
        "proxy": "Random",
        "submit": "Download",
        "csrf_token": csrf
    }
    rs = s.post("https://www.findyoutube.net/result", data=post).text
    return rs
    

def upload(data, cookie):
    # source_url = "https://www.youtube.com/watch?v=" + data["id"]
    mid = re.findall('DedeUserID=(.*?);', cookie + ';')[0]
    csrf = re.findall('bili_jct=(.*?);', cookie + ';')[0]
    header = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Referer': 'https://space.bilibili.com/{}/#!/'.format(mid),
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/5' +
                          '37.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',
            'cookie': cookie,
            "Origin": "https://member.bilibili.com",
    }
    s = requests.session()
    s.headers.update(header)
    # file info
    # video_url = get_youtube_url(data["id"])
    video_url = GetVideo.getUrl("https://www.youtube.com/watch?v=" + data["id"])
    while True:
        try:
            file_size = s.get(video_url, proxies=proxies, verify=False, headers={"Range": "bytes=0-10"}, timeout=(30, 30)).headers["Content-Range"]
            break
        except (requests.ConnectionError, requests.ReadTimeout, requests.ConnectTimeout):
            logger.error("get YouTuBe video failed")
            time.sleep(10)
    file_size = int(file_size.split('/')[-1])
    logger.info("get info done")
    # preupload
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

    # 分块下载&上传
    while now_size < file_size:
        new_end = min(now_size + upload_size, file_size - 1)
        tmp_header = {"Range": "bytes={}-{}".format(now_size, new_end), "Connection": "Keep-Alive"}
        while True:
            try:
                part = s.get(video_url, headers=tmp_header, proxies=proxies, verify=False, timeout=(20, 600)).content
                break
            except Exception as e:
                logger.error(str(e))
                time.sleep(2)
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

    # 下载&上传完成
    param = {
        'output': 'json',
        'name': time.ctime() + ".mp4",
        'profile': 'ugcupos/yb',
        'uploadId': upload_id,
        'biz_id': biz_id
    }
    _data = s.post(upload_url, params=param, data=json.dumps(restore)).text
    logger.debug(_data)
    url = "https://member.bilibili.com/x/vu/web/edit?csrf=" + csrf
    s.headers.pop("X-Upos-Auth")
    _data = s.get("https://member.bilibili.com/x/geetest/pre/add").text
    logging.debug(_data)
    _rs = s.get("https://member.bilibili.com/x/web/archive/view?aid={}&history=".format(data["av"])).json()["data"]
    videos = []
    for i in _rs["videos"]:
        if len(i["desc"]) != 0: # 判断视频是否有错误，比如撞车、解码错误、违法违规等
            continue
        videos.append({"filename": i["filename"], "title": i["title"]})
    videos.append({"filename": upos_uri.split(".")[0], "title": data["title"][0:min(79, len(data["title"]))], "desc": data["id"]})
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
                    "aid": int(data["av"]),
                    "handle_staff": False,
                }
    logger.debug(json.dumps(send_data))
    s.headers.update({"Content-Type": "application/json;charset=UTF-8"})
    res = s.post(url=url, json=send_data).text
    logger.debug(res)
    return res

# if __name__ == "__main__":
#     get_youtube_url2("iCfr8N0Q8IA")
