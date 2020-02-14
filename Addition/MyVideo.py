import requests
import sqlite3
import re
from utility.conf import parser, channel, channels
api_key = parser.get("GoogleToken", "token")
# db = sqlite3.connect("../data/data.db")
url = "https://www.googleapis.com/youtube/v3/playlistItems?" + \
              "part=snippet&playlistId={0}&key={1}&maxResults=50".format("UUAuUUnT6oDeKwE6v1NGQxug", api_key)
api = "https://member.bilibili.com/x/web/archive/view?aid=54574684&history="
# cur = db.cursor()
# cur.execute("""create table data(vid text PRIMARY KEY NOT NULL,
#                                  aid Integer,
#                                  zht Boolean DEFAULT 0,
#                                  zhs Boolean DEFAULT 0,
#                                  en Boolean DEFAULT 0,
#                                  cid Integer);""")
# # cur.close()
# db.commit()
dct = {}
for i in requests.get(url).json()['items']:
    dct[i["snippet"]["title"]]=i["snippet"]["title"]["resourceId"]["videoId"]
for i in range(1, 4):
    url = api.format(i)
    res = requests.get(url).json()["data"]["videos"]
    for j in res:
        try:
            vid = re.findall("v=(.*?)\\n", j["description"])[0]
        except IndexError:
            continue
        print(j["title"])
        # try:
        #     cur.execute("insert into data(vid,aid) values('{0}',{1});".format(vid, j["aid"]))
        # except sqlite3.IntegrityError:
        #     continue
# db.commit()
