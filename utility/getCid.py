import requests
import sqlite3
import re
import time
db = sqlite3.connect("data/data.db")
cur = db.cursor()

def getCid(data, cookie):
    mid = re.findall('DedeUserID=(.*?);', cookie + ';')[0]
    header = {
        'Accept': 'application/json, text/javascript, */*; q=0.01',
        'Referer': 'https://space.bilibili.com/{}/#!/'.format(mid),
        'User-Agent': 'Mozilla/5.0 (Windows NT 6.1; WOW64) AppleWebKit/5' +
                      '37.36 (KHTML, like Gecko) Chrome/57.0.2987.133 Safari/537.36',
        'cookie': cookie,
        "Origin": "https://member.bilibili.com",
    }
    s = requests.session()
    s.headers.update(header)
    _rs = s.get("https://member.bilibili.com/x/web/archive/view?aid={}&history=".format(data["av"])).json()["data"]
    for i in _rs["videos"]:
        cur.execute('update data set cid=(?) where title like (?)', (str(i["cid"]), i["title"][:min(len(i["title"]), 60)] + "%"))
        db.commit()

def getTitle():
    api = "https://www.googleapis.com/youtube/v3/videos?part=snippet&id={}&key={}"
    rs = cur.execute("select vid, title from data").fetchall()
    for i in rs:
        if i[1] is not None and len(i[1]) != 0:
            continue
        i = i[0]
        url = api.format(i)
        _rs = requests.get(url).json()
        title = _rs["items"][0]["snippet"]["title"]
        print(title)
        cur.execute("update data set title=(?) where vid=(?)", (title, i))
        print(i, title)
        db.commit()
        time.sleep(2)

if __name__ == "__main__":
    data = {
        "av": "54574684"
    }
    cookie = "fts=1527332025; balh_season_ss23820=1; im_notify_type_23207406=0; balh_season_ss21680=1; LIVE_BUVID=966582cd498f30550017a37c0f61b3f0; LIVE_BUVID__ckMd5=6d24497bffb84d61; balh_season_ep101791=1; balh_season_5551=1; balh_season_ep96714=1; balh_season_ep98553=1; balh_season_ep96703=1; balh_season_ss25689=1; balh_baipao_zomble_land_saga=Y; buvid3=20400FDD-D2EC-477A-8DB7-633F9A5EA0036719infoc; CURRENT_FNVAL=16; _uuid=D8C76277-C4E9-8FA5-2732-15DDCE8AA97F97784infoc; balh_server=https://www.biliplus.com; balh_season_ss25848=1; balh_is_close_do_not_remind=Y; gr_user_id=236053a5-db4f-4aa6-83b9-e2aac000aba5; s_cc=true; s_sq=%5B%5BB%5D%5D; stardustpgcv=0606; stardustvideo=1; _ga=GA1.2.324290134.1557309803; rpdid=|(ku|kmklJm~0J'ull~J|mm~m; sid=db4ogbo4; im_seqno_23207406=47; im_local_unread_23207406=0; DedeUserID=23207406; DedeUserID__ckMd5=d8f03070e37650e8; SESSDATA=86a2cf31%2C1565272447%2C909f1f71; bili_jct=021e229f07060fd4eb1d34ca7030f32d; CURRENT_QUALITY=80; finger=b3372c5f; bp_t_offset_23207406=282212757606319841"
    getCid(data, cookie)
    # getTitle()
