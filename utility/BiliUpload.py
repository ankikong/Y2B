import requests
import json
import re
import os
import math
import base64
import time


class Upload:
    def __init__(self, url, video_path, video, tag, title, block):
        cookie = json.load(open("config.json", encoding="utf8"))["cookie"]
        # with open("./cookies.txt") as tmp:
        #     cookie = tmp.read()
        self.file = video_path + '/' + video
        self.title = title
        self.source = url

        self.tag = ""
        self.block = block
        for _ in tag:
            self.tag += _ + ','
        self.tag = self.tag[:-1]
        self.video_path = video_path + '/'
        # 4MB
        self.upload_size = 4 * 1024 * 1024
        self.file_size = os.path.getsize(self.file)
        self.mid = re.findall('DedeUserID=(.*?);', cookie + ';')[0]
        self.csrf = re.findall('bili_jct=(.*?);', cookie + ';')[0]
        self.header = {
            'Accept': 'application/json, text/javascript, */*; q=0.01',
            'Referer': 'https://space.bilibili.com/{}/#!/'.format(self.mid),
            'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/5' +
                          '37.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',
            'cookie': cookie,
            "Origin": "https://member.bilibili.com",
        }
        self.file_name = self.file.split("/")[-1]
        self.s = requests.session()
        self.s.headers.update(self.header)
        self.restore = {"parts": []}

    def first(self):
        param = {
            "os": "upos",
            "upcdn": "ws",
            "name": self.file_name,
            "size": os.path.getsize(self.file),
            "r": "upos",
            "profile": "ugcupos/yb",
            "ssl": "0"
        }
        url = "https://member.bilibili.com/preupload"
        _data = self.s.post(url=url, params=param).json()
        self.upos_uri = _data["upos_uri"].replace("upos:/", "").replace("/ugc/", "")
        self.biz_id = _data["biz_id"]
        self.endpoint = _data["endpoint"]
        self.auth = _data["auth"]

    def second(self):
        url = "https:{1}/ugc/{0}?uploads&output=json".format(self.upos_uri, self.endpoint)
        # self.header["X-Upos-Auth"] = self.auth
        self.s.headers.update({"X-Upos-Auth": self.auth})
        # _req = request.Request(headers=self.header, url=url, data="".encode())
        while True:
            try:
                _data = self.s.post(url=url).json()
                # _data = request.urlopen(_req).read().decode()
                # _data = json.loads(_data)
                self.upload_id = _data["upload_id"]
                break
            except (IndexError, KeyError):
                time.sleep(2)
                continue

    def third(self):
        url = "https:{0}/ugc/{1}".format(self.endpoint, self.upos_uri)
        total_chunk = math.ceil(self.file_size / self.upload_size)
        index = 1
        now_size = 0
        with open(self.file, "rb") as file:
            while True:
                part = file.read(self.upload_size)
                if not part:
                    break
                size = len(part)
                param = {
                    "total": self.file_size,
                    "partNumber": index,
                    "uploadId": self.upload_id,
                    "chunk": index - 1,
                    "chunks": total_chunk,
                    "size": size,
                    "start": now_size,
                    "end": now_size + size
                }

                index += 1
                now_size += size
                res = self.s.put(url=url, params=param, data=part).text
                self.restore["parts"].append({"partNumber": index, "eTag": "etag"})
                print(res)
        param = {
            'output': 'json',
            'name': self.file_name,
            'profile': 'ugcupos/yb',
            'uploadId': self.upload_id,
            'biz_id': self.biz_id
        }
        _data = self.s.post(url, params=param, data=json.dumps(self.restore)).text
        print(_data)

    def fourth(self):
        url = "http://member.bilibili.com/x/vu/web/add?csrf=" + self.csrf
        header = self.header.copy()
        header["Content-Type"] = "application/json;charset=UTF-8"
        header["csrf"] = self.csrf
        send_data = {"copyright": 2, "videos": [{"filename": self.upos_uri.split(".")[0],
                                                 "title": self.title,
                                                 "desc": ""}],
                     "source": self.source,
                     "tid": self.block,
                     "cover": self.cover(self.file.split(".")[0] + ".jpg", self.csrf),
                     "title": "【中英/搬运】" + self.title,
                     "tag": self.tag,
                     "desc_format_id": 0,
                     "desc": "本视频由爬虫抓取，并由爬虫上传\n字幕请使用b站的外挂字幕,字幕上传需要时间,请等待\n" +
                             "测试阶段，可能出现数据不准\n",
                     "dynamic": "#" + "##".join(self.tag.split(",")) + "#",
                     "subtitle": {
                         "open": 0,
                         "lan": ""
                        }
                     }
        print(send_data)
        res = self.s.post(url=url, data=json.dumps(send_data)).text
        print(res)
        return res

    def cover(self, file, csrf):
        vid = self.source.split('=')[-1]
        __url = "https://member.bilibili.com/x/vu/web/cover/up"
        __send = {"cover": "data:image/jpeg;base64," +\
                    base64.b64encode(requests.get("https://i1.ytimg.com/vi/{}/maxresdefault.jpg".format(vid)).content).decode(),
                    "csrf": csrf
                  }
        __res = self.s.post(url=__url, data=__send).json()
        return __res["data"]["url"].replace("http:", "").replace("https:", "")

    def main(self):
        self.first()
        self.second()
        self.third()
        return self.fourth()
