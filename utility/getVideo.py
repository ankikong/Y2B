import re
import os
from utility import tool
import youtube_dl
from urllib import parse
import json


class VideoManager:
    def __init__(self, vid: str, hd: bool = False):
        self.vid: str = vid
        self._dmer1: tool.DownloadManager = None
        self._dmer2: tool.DownloadManager = None
        self._o: str = None
        self._hd: bool = hd
        self._vURL: str = None
        self._sURL: str = None

    def getVideo(self):
        rs = {}
        proxy = tool.settingConf.get("Proxy")
        jsonrpc = tool.settingConf["Aria"]["jsonrpc"]
        ffmpegArgs = tool.settingConf["FFMPEG"]["args"]
        ffmpegPath = tool.settingConf["FFMPEG"]["path"]
        logger = tool.getLogger()
        opt = {"logger": logger}
        if proxy is not None:
            opt["proxy"] = proxy
        _tmpRs: dict = None
        try:
            ydl = youtube_dl.YoutubeDL(opt)
            _tmpRs = ydl.extract_info(
                f"https://www.youtube.com/watch?v={self.vid}", download=False)
        except:
            logger.info(f"[{self.vid}] youtube-dl failed, try another way...")
        try:
            if _tmpRs is None:
                _tmpRs = self.getVideoUrl()
        except:
            logger.info(f"[{self.vid}] another way failed, noway..")
            logger.debug("", exc_info=True)
            return False, ""
        headers: dict = None
        for i in _tmpRs["formats"]:
            rs[i["format_id"]] = i
            headers = i["http_headers"]

        urlv = None
        urls = None
        for i in ["299", "137", "298"]:
            if self._hd and rs.get(i) is not None:
                if rs[i]["protocol"] == "http_dash_segments":
                    # urlv = rs[i]['fragment_base_url']
                    logger.error("分段视频，暂未支持")
                    return False, ""
                else:
                    urlv = rs[i]["url"]
                break

        for i in ["141", "140", "139"]:
            if urlv is not None and rs.get(i) is not None:
                if rs[i]["protocol"] == "http_dash_segments":
                    # urls = rs[i]['fragment_base_url']
                    logger.error("分段视频，暂未支持")
                    return False, ""
                else:
                    urls = rs[i]["url"]
                break

        if urlv is None or urls is None:
            urlv = None
            urls = None
            for i in ["22", "18"]:
                if rs.get(i) is not None:
                    if rs[i]["protocol"] == "http_dash_segments":
                        urlv = rs[i]['fragment_base_url']
                    else:
                        urlv = rs[i]["url"]
                    break

        logger.info(f"{self.vid}:v[{urlv is not None}],a[{urls is not None}]")
        logger.debug(f"v[{urlv}]")
        logger.debug(f"a[{urls}]")
        if urlv is None:
            return False, ""
        cmd = ffmpegPath + ' -i "{}" -i "{}" ' + ffmpegArgs + ' "{}"'

        self._dmer1 = tool.DownloadManager(
            urlv,
            proxy=proxy,
            jsonrpc=jsonrpc,
            files=self.vid + "_v",
            headers=headers)
        self._dmer1.download()
        if urls is not None:
            self._dmer2 = tool.DownloadManager(
                urls,
                proxy=proxy,
                jsonrpc=jsonrpc,
                files=self.vid + "_s",
                headers=headers)
            self._dmer2.download()
            if self._dmer2.waitForFinishing() != 1:
                return False, ""
        if self._dmer1.waitForFinishing() != 1:
            return False, ""

        if self._dmer2 is not None:
            _a = self._dmer2.telFileLocate()
            _v = self._dmer1.telFileLocate()
            self._o = self._dmer1.getDirs() + self.vid + "_merged.mp4"
            if os.path.exists(self._o):
                os.remove(self._o)
            nowCmd = cmd.format(_a, _v, self._o)
            logger.info("cmd: " + nowCmd)
            cmdRes = os.system(nowCmd)
            logger.info(f"ffmpeg result:{cmdRes}")
            if cmdRes != 0:
                return False, ""
            return True, self._o
        else:
            return True, self._dmer1.telFileLocate()

    def deleteFile(self):
        self._dmer1.deleteFile()
        if self._dmer2 is not None:
            self._dmer2.deleteFile()
            os.remove(self._o)

    # 无奈的加回来了
    def getVideoUrl(self):
        s = tool.Session()
        s.headers.update({
            "Sec-Fetch-Dest": "empty",
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36",
            "Content-Type": "application/json;charset=UTF-8",
            "Accept": "*/*",
            "Origin": "https://www.y2b.xyz",
            "Sec-Fetch-Site": "same-origin",
            "Sec-Fetch-Mode": "cors",
            "Referer": "https://www.y2b.xyz/",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-TW;q=0.6",
        })
        raw = s.get("https://www.y2b.xyz/", useProxy=True,
                    wantStatusCode=200).text
        csrf = re.findall('csrf_token = "([^"]+)', raw)[0]
        s.headers.update({
            "X-XSRF-TOKEN": parse.unquote(s.cookies.get_dict()["XSRF-TOKEN"]),
            "X-CSRF-TOKEN": csrf
        })
        rs = s.post("https://www.y2b.xyz/analysis",
                    json={"url": f"https://www.youtube.com/watch?v={self.vid}",
                          "channel": "one"},
                    useProxy=True,
                    wantStatusCode=200).json()
        s.close()
        return rs
    
    def getVideoUrlByYoutubeApi(self):
        s = tool.Session()
        s.headers.update({
            "X-Requested-With": "XMLHttpRequest",
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.163 Safari/537.36",
            "Accept": "*/*",
            "Origin": "https://www.youtube.com/",
            "Referer": "https://www.youtube.com/",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-TW;q=0.6",
        })
        url = f"https://www.youtube.com/get_video_info?video_id={self.vid}"
        rs = s.get(url, useProxy=True).text
        a = parse.parse_qs(rs.text)
        a = json.loads(a['player_response'][0])['streamingData']['adaptiveFormats']

        s.close()

# if __name__ == "__main__":
#     print(GetVideo.getUrl("https://www.youtube.com/watch?v=7FDyF8gVoL8"))
    # download2("bBrUrgNf5y8")
    # s = GetVideo("https://www.youtube.com/watch?v=7FDyF8gVoL8")
    # print(s.first())
