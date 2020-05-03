import requests
import re
import time
import logging
import platform
import os
from utility import tool
from urllib import parse
from html import unescape
import re
import youtube_dl

logger = logging.getLogger("fileLogger")


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
        proxy = tool.settingConf["Proxy"]
        jsonrpc = tool.settingConf["Aria"]["jsonrpc"]
        ffmpegArgs = tool.settingConf["FFMPEG"]["args"]
        ffmpegPath = tool.settingConf["FFMPEG"]["path"]
        opt = {"logger": logger}
        if proxy is not None:
            opt["proxy"] = proxy.get("http")
        ydl = youtube_dl.YoutubeDL(opt)
        _tmpRs = ydl.extract_info(
            "https://www.youtube.com/watch?v=" + self.vid, download=False)

        for i in _tmpRs["formats"]:
            rs[i["format_id"]] = i

        urlv = None
        urls = None
        for i in ["299", "137"]:
            if self._hd and rs.get(i) is not None:
                urlv = rs[i]["url"]
                break

        for i in ["141", "140", "139"]:
            if urlv is not None and rs.get(i) is not None:
                urls = rs[i]["url"]
                break

        if urlv is None or urls is None:
            urlv = None
            urls = None
            for i in ["22", "18"]:
                if rs.get(i) is not None:
                    urlv = rs[i]["url"]
                    break

        if urlv is None:
            raise Exception("no video")
        cmd = ffmpegPath + ' -i "{}" -i "{}" ' + ffmpegArgs + ' "{}"'

        self._dmer1 = tool.DownloadManager(
            urlv, proxy=proxy, jsonrpc=jsonrpc, files=self.vid + "_v")
        self._dmer1.download()
        if urls is not None:
            self._dmer2 = tool.DownloadManager(
                urls, proxy=proxy, jsonrpc=jsonrpc, files=self.vid + "_s")
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
            if os.system(nowCmd) != 0:
                return False, ""
            return True, self._o
        else:
            return True, self._dmer1.telFileLocate()

    def deleteFile(self):
        self._dmer1.deleteFile()
        if self._dmer2 is not None:
            self._dmer2.deleteFile()
            os.remove(self._o)

# if __name__ == "__main__":
#     print(GetVideo.getUrl("https://www.youtube.com/watch?v=7FDyF8gVoL8"))
    # download2("bBrUrgNf5y8")
    # s = GetVideo("https://www.youtube.com/watch?v=7FDyF8gVoL8")
    # print(s.first())
