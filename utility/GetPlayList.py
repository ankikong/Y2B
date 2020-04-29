import json
import requests
import sqlite3
from utility import tool


def get_work_list():
    parser = tool.getSettingConf()
    api_key = parser.get("GoogleToken", "token")
    proxies = dict(parser.items("Proxy"))
    db = sqlite3.connect("data/data.db")
    _return = []
    channel = tool.getChannelConf()[0]
    for i in channel:
        if i == 'DEFAULT':
            continue
        _ = dict(channel.items(i))
        url = "https://www.googleapis.com/youtube/v3/playlistItems?" + \
              "part=snippet&playlistId={0}&key={1}&maxResults=50".format(_["id"], api_key)
        _res = requests.get(url, proxies=proxies).json()
        for __ in _res["items"]:
            tmp_data = __["snippet"]
            video_id = tmp_data["resourceId"]["videoId"]
            db_res = db.execute("select count(vid) from data where vid='{}';".format(video_id)).fetchone()[0]
            if int(db_res) != 0:
                # print(video_id)
                continue
            _return.append({"title": tmp_data["title"], "id": video_id, "av": _["av"]})
    db.close()
    return _return


if __name__ == "__main__":
    # res = get_work_list()
    # print(res)
    pass
