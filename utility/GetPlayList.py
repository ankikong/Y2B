import json
from utility import tool


def get_work_list():
    logger = tool.getLogger()
    api_key = tool.settingConf["GoogleToken"]
    db = tool.getDB()
    _return = []
    channel = tool.channelConf
    s = tool.Session()
    for i in channel.data:
        settings = channel[i]
        pages = int(settings["pages"])
        params = {
            "part": "snippet",
            "playlistId": settings["id"],
            "key": api_key,
            "maxResults": settings["countPerPage"],
            "pageToken": None
        }
        for _ in range(pages):
            url = "https://www.googleapis.com/youtube/v3/playlistItems"
            _res: dict = s.get(url, params=params, useProxy=True).json()
            if _res.get("error") is not None:
                _res = _res["error"]
                logger.error(
                    f"code[{_res['code']}],message[{_res['message']}]")
                logger.error(f"获取视频失败，请检查配置文件setting.yaml的[{i}]")
                break
            for __ in _res["items"]:
                tmp_data = __["snippet"]
                video_id = tmp_data["resourceId"]["videoId"]
                db_res = db.execute(
                    "select count(vid) from data where vid=?;", (video_id, )).fetchone()[0]
                if int(db_res) != 0:
                    # print(video_id)
                    continue
                tmpTitle = tmp_data["title"]
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
                desc = desc.replace("\\n", "\n")
                desc = desc[0:min(250, len(desc))]
                tmpRs["desc"] = desc

                _return.append(tmpRs)
            params["pageToken"] = _res.get("nextPageToken", None)
            if _res.get("nextPageToken", None) is None:
                break
    db.close()
    return _return


if __name__ == "__main__":
    # res = get_work_list()
    # print(res)
    pass
