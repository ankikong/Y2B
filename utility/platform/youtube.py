import os
from .bean import Bean, Video
from typing import List
import json
from utility import tool
import re
from random import randint


class Youtube(Bean):

    @staticmethod
    def GetVideos(channel: dict, settings: dict = {}) -> List[Video]:
        def getKey(item):
            return item["snippet"]["publishedAt"]

        logger = tool.getLogger()
        _return = []
        if not channel.get("enable", False):
            return _return
        api_key = settings["GoogleToken"]
        s = tool.Session()
        params = {
            "part": "snippet",
            channel["type"]: channel["param"],
            "key": api_key[randint(0, len(api_key)-1)],
            # "maxResults": settings.get("countPerPage", 10),
            "maxResults": 50,
            "order": "date",
            "pageToken": None
        }
        if channel["type"] == "q":
            url = "https://www.googleapis.com/youtube/v3/search"
        elif channel["type"] == "playlistId":
            url = "https://www.googleapis.com/youtube/v3/playlistItems"
        _res: dict = s.get(url, params=params, useProxy=True).json()
        if _res.get("error") is not None:
            _res = _res["error"]
            logger.error(
                f"code[{_res['code']}],message[{_res['message']}]")
            logger.error(f"获取视频失败，请检查配置文件setting.yaml，或可能为配额已用完")
            return []
        _res["items"].sort(key=getKey, reverse=True)
        for __ in _res["items"][0:channel.get("countPerPage", 10)]:
            tmp_data = __["snippet"]
            id_tmp = tmp_data.get("resourceId") or __.get("id")
            video_id = id_tmp["videoId"]
            tmpTitle = tmp_data["title"]
            stitle = tmp_data["title"]
            if channel.get("titleTranslate", False):
                tmpTitle = tool.translateG(tmpTitle)
            logger.debug(tmpTitle)
            # if not filters(channel, tmpTitle):
            #     logger.debug(f"{tmpTitle} not fixed")
            #     continue
            tmpRs = channel.copy()
            tmpRs.update({
                "title": tmpTitle[0:min(80, len(tmpTitle))],  # 破站限制长度
                "id": video_id,
                "url": f"https://www.youtube.com/watch?v={video_id}",
                "ptitle": str(channel.get("title", "")).format(title=tmpTitle,
                                                               ctitle=tmp_data["channelTitle"],
                                                               ptime=tmp_data["publishedAt"],
                                                               surl=f"https://www.youtube.com/watch?v={video_id}",
                                                               stitle=stitle),
                "desc": str(channel.get("desc", "")).format(title=tmpTitle,
                                                            ctitle=tmp_data["channelTitle"],
                                                            ptime=tmp_data["publishedAt"],
                                                            surl=f"https://www.youtube.com/watch?v={video_id}",
                                                            stitle=stitle)
            })
            # tmpRs["tags"] = tmpRs.get("tags", "").split(",")

            ptitle = tmpRs.get("ptitle", "")
            ptitle = ptitle[0:min(80, len(ptitle))]
            tmpRs["ptitle"] = ptitle

            desc = tmpRs.get("desc", "")
            desc = desc[0:min(250, len(desc))]
            tmpRs["desc"] = desc
            _return.append(Video(channelParam=tmpRs))
        s.close()
        return _return
