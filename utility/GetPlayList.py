import json
import requests
import sqlite3
from utility.conf import parser, channel, channels
api_key = parser.get("GoogleToken", "token")
proxies = {"http": "http://127.0.0.1:10809", "https": "http://127.0.0.1:10809"}

def get_work_list():
    db = sqlite3.connect("data/data.db")
    cur = db.cursor()
    _return = []
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
            db_res = cur.execute("select count(vid) from data where vid='{}';".format(video_id)).fetchone()[0]
            if int(db_res) != 0:
                # print(video_id)
                continue
            _return.append({"title": tmp_data["title"], "id": video_id, "av": _["av"]})
    return _return


if __name__ == "__main__":
    # res = get_work_list()
    # print(res)
    pass
