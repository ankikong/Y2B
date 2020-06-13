from typing import List
import os
import uuid
from utility import tool
import youtube_dl


class Video:
    def __init__(self, youtube_dlParams: dict = {}, channelParam: dict = {}):
        self.channelParam: dict = channelParam.copy()
        self.youtube_dlParams: dict = youtube_dlParams.copy()
        self.__uniq = channelParam["id"]
        self.__name = f"./tmp/{self.__uniq}.%(ext)s"
        self.__log = tool.getLogger()

    def download(self, proxy: str = "") -> bool:
        """ 阻塞下载视频,返回值表示是否下载成功
        """
        try:
            self.youtube_dlParams["proxy"] = proxy
            self.youtube_dlParams["outtmpl"] = self.__name
            self.youtube_dlParams["logger"] = self.__log
            self.youtube_dlParams["format"] = self.youtube_dlParams.get(
                "format", "bestvideo[ext=mp4]+bestaudio[ext=m4a]")
            url = self.channelParam["url"]
            self.__log.debug("start download")
            ydl = youtube_dl.YoutubeDL(self.youtube_dlParams)
            ydl.extract_info(url, download=True)
            self.__log.debug("finish download")
            return True
        except Exception as e:
            self.__log.error(str(e), exc_info=True)
        return False

    def path(self) -> str:
        """ 返回文件所在路径
        """
        for i in os.listdir("./tmp"):
            if self.__uniq in i:
                return f"./tmp/{i}"
        return ""

    def deleteFile(self):
        os.remove(self.path())


class Bean:
    """ 多平台通用接口,负责获取视频信息
    """

    proxy: str = None
    youtube_dl_params: dict = None

    @staticmethod
    def Init(data: dict) -> bool:
        """ 初始化类属性，初始化正常的话返回True
            setting.yaml平台的参数会被传进这里
            proxy，即代理配置要在这里初始化
            一些平台参数也在这里初始化
        """
        raise NotImplementedError("")

    @staticmethod
    def GetVideos(channel: dict) -> List[Video]:
        """ channel.yaml的每个节点会被传进来
            此函数，返回的list的每个Video的属性都必须被设置
        """
        pass

    @staticmethod
    def CheckSetting(channel: dict) -> bool:
        """
        """
