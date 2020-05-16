import json
from utility import tool
import re


def filters(settings: dict, title: str) -> bool:
    if settings.get("restrict") is None:
        return True
    rs = settings.get("restrict")
    contain = rs.get("contain")
    exclude = rs.get("exclude")
    priority = rs.get("priority", "exclude")
    if priority == "exclude":
        if exclude is not None and re.search(exclude, title, flags=re.IGNORECASE) is not None:
            return False
        if contain is None or re.search(contain, title, flags=re.IGNORECASE) is not None:
            return True
        return False
    else:
        if contain is None and \
                exclude is not None and \
                re.search(exclude, title, flags=re.IGNORECASE) is not None:
            return False
        if contain is not None and \
                re.search(contain, title, flags=re.IGNORECASE) is not None:
            return True
        return False


def getYTB(settings: dict) -> list:
    logger = tool.getLogger()
    _return = []
    if not settings.get("enable", False):
        return _return
    api_key = tool.settingConf["GoogleToken"]
    db = tool.getDB()
    s = tool.Session()
    params = {
        "part": "snippet",
        settings["type"]: settings["param"],
        "key": api_key,
        "maxResults": settings.get("countPerPage", 10),
        "order": "date",
        "pageToken": None
    }
    pages = int(settings.get("pages", 1))
    if settings["type"] == "q":
        url = "https://www.googleapis.com/youtube/v3/search"
    elif settings["type"] == "playlistId":
        url = "https://www.googleapis.com/youtube/v3/playlistItems"
    for _ in range(pages):
        _res: dict = s.get(url, params=params, useProxy=True).json()
        if _res.get("error") is not None:
            _res = _res["error"]
            logger.error(
                f"code[{_res['code']}],message[{_res['message']}]")
            logger.error(f"获取视频失败，请检查配置文件setting.yaml")
            break
        for __ in _res["items"]:
            tmp_data = __["snippet"]
            id_tmp = tmp_data.get("resourceId") or __.get("id")
            video_id = id_tmp["videoId"]
            db_res = db.execute(
                "select count(vid) from data where vid=?;", (video_id, )).fetchone()[0]
            if int(db_res) != 0:
                # print(video_id)
                continue
            tmpTitle = tmp_data["title"]
            logger.debug(tmpTitle)
            if not filters(settings, tmpTitle):
                logger.debug(f"{tmpTitle} not fixed")
                continue
            tmpRs = settings.copy()
            tmpRs.update({
                "title": tmpTitle[0:min(80, len(tmpTitle))],  # 破站限制长度
                "id": video_id,
                "ptitle": str(settings.get("title", "")).format(title=tmpTitle,
                                                                ctitle=tmp_data["channelTitle"],
                                                                ptime=tmp_data["publishedAt"],
                                                                surl="https://www.youtube.com/watch?v=" + video_id),
                "desc": str(settings.get("desc", "")).format(title=tmpTitle,
                                                             ctitle=tmp_data["channelTitle"],
                                                             ptime=tmp_data["publishedAt"],
                                                             surl="https://www.youtube.com/watch?v=" + video_id)
            })
            # tmpRs["tags"] = tmpRs.get("tags", "").split(",")

            ptitle = tmpRs.get("ptitle", "")
            ptitle = ptitle[0:min(80, len(ptitle))]
            tmpRs["ptitle"] = ptitle

            desc = tmpRs.get("desc", "")
            desc = desc[0:min(250, len(desc))]
            tmpRs["desc"] = desc

            _return.append(tmpRs)
        params["pageToken"] = _res.get("nextPageToken", None)
        if _res.get("nextPageToken", None) is None:
            break
    db.close()
    return _return


def get_work_list():
    _return = []
    channel = tool.channelConf
    for i in channel.data:
        settings: dict = channel[i]
        if settings["platform"] == "youtube":
            _return += getYTB(settings)
    return _return


if __name__ == "__main__":
    # res = get_work_list()
    # print(res)
    pass
