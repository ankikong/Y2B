from utility.platform import bean
from utility.platform import youtube


class VideoFactory:

    @staticmethod
    def getBean(platform: str) -> bean:
        platform = platform.lower()
        if platform == "youtube":
            return youtube.Youtube
        else:
            return None
