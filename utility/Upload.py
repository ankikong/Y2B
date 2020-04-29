# Upload.py 是把每个视频单独作为一个视频发布，而不是视频合集，即一个av下
# 只有一个cid
import requests
import json
import re
import os
import math
import base64
import time
import urllib3
import logging
from utility import conf
logger = logging.getLogger("fileLogger")
urllib3.disable_warnings()
# proxies = {"http": "http://127.0.0.1:8087", "https": "http://127.0.0.1:8087"}
proxies = None

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

def upload(data, cookie):
    source_url = "https://www.youtube.com/watch?v=" + data["id"]
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
    video_url = get_youtube_url(data["id"])
    while True:
        try:
            # file_size = requests.get(video_url, proxies=proxies, verify=False, headers={"Range": "bytes=0-10"}, timeout=(30, 30)).headers["Content-Range"]
            file_size = requests.post("https://bilibili-tw.appspot.com/get", data={"url": video_url, "header": json.dumps({"Range": "bytes=0-10"})}).headers["Content-Range"]
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
            "ssl": "0"
        }
    url = "https://member.bilibili.com/preupload"
    _data = s.post(url=url, params=param).text
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
    while now_size < file_size:
        new_end = min(now_size + upload_size, file_size - 1)
        tmp_header = {"Range": "bytes={}-{}".format(now_size, new_end)}
        while True:
            try:
                part = requests.post("https://bilibili-tw.appspot.com/get", data={"url": video_url, "header": json.dumps(tmp_header)})
                if part.status_code != 200:
                    logger.error("fail")
                    time.sleep(2)
                    continue
                part = part.content
                # part = requests.get(video_url, headers=tmp_header, proxies=proxies, verify=False, timeout=(20, 600)).content
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
        res = s.put(url=upload_url, params=param, data=part).text
        restore["parts"].append({"partNumber": index, "eTag": "etag"})
        logger.debug("{}/{}:".format(index, total_chunk) + res)
    param = {
        'output': 'json',
        'name': time.ctime() + ".mp4",
        'profile': 'ugcupos/yb',
        'uploadId': upload_id,
        'biz_id': biz_id
    }
    _data = s.post(upload_url, params=param, data=json.dumps(restore)).text
    logger.debug(_data)
    # upload done
    # post video info
    def cover(csrf):
        vid = data["id"]
        __url = "https://member.bilibili.com/x/vu/web/cover/up"
        __send = {"cover": "data:image/jpeg;base64," +\
                    base64.b64encode(requests.get("https://i1.ytimg.com/vi/{}/maxresdefault.jpg".format(vid)).content).decode(),
                    "csrf": csrf
                  }
        __res = s.post(url=__url, data=__send).json()
        
        return __res["data"]["url"].replace("http:", "").replace("https:", "")

    url = "https://member.bilibili.com/x/vu/web/add?csrf=" + csrf
    s.headers.pop("X-Upos-Auth")
    _data = s.get("https://member.bilibili.com/x/geetest/pre/add").text
    logging.debug(_data)
    tmp_title = "【中英/搬运】" + data["title"]
    send_data = {"copyright": 2, "videos": [{"filename": upos_uri.split(".")[0],
                                                "title": time.ctime(),
                                                "desc": ""}],
                    "source": source_url,
                    "tid": int(data["block"]),
                    "cover": cover(csrf),
                    "title": tmp_title[0:min(80, len(tmp_title))],
                    "tag": ','.join(data["tags"]),
                    "desc_format_id": 0,
                    "desc": data["title"] + "\n本视频由爬虫抓取，并由爬虫上传\n字幕请使用b站的外挂字幕,字幕上传需要时间,请等待\n" +
                            "测试阶段，可能出现数据不准\n",
                    "dynamic": "#" + "##".join(data["tags"]) + "#",
                    "subtitle": {
                        "open": 0,
                        "lan": ""
                    }
                }
    logger.debug(json.dumps(send_data))
    s.headers.update({"Content-Type": "application/json;charset=UTF-8"})
    res = s.post(url=url, json=send_data).text
    logger.debug(res)
    return res
