import requests
import json
from urllib import parse
import sqlite3
import xml.etree.ElementTree as Et
from html import unescape
import re
import logging
from pypinyin import lazy_pinyin, Style
from utility import tool
api = "https://www.youtube.com/api/timedtext?lang={}&v={}&fmt=srv1"
# fmt = ["zh-CN", "zh-TW", "en"]
parser = tool.getSettingConf()
header = dict(parser.items("BiliHeader"))

s = requests.session()
s.headers.update(header)
db = sqlite3.connect("data/data.db")
cur = db.cursor()
csrf = re.findall("bili_jct=(.*?);", header['cookie'])[0]
logger = logging.getLogger("fileLogger")


def to_bili(sou):
    _bili = {
        "font_size": 0.4,
        "font_color": "#FFFFFF",
        "background_alpha": 0.5,
        "background_color": "#9C27B0",
        "Stroke": "none",
        "body": []
    }
    _per = {"from": 0, "to": 7, "location": 2, "content": ""}
    _sou = Et.fromstring(sou)
    _lines = _sou.findall("text")
    # last = 0
    for _ in _lines:
        start = float(_.get("start"))
        dur = float(_.get("dur"))
        end = start + dur
        start, end = round(start, 2), round(end, 2)
        if _.text is None:
            continue
        _sub = unescape(_.text)
        _sub = re.sub("\\[Music\\]|\\[Applause\\]|\\[Laughter\\]", "", _sub).replace("\n", " ")
        _per["from"], _per["to"], _per["content"] = start, end, _sub
        last_json = _per.copy()
        _bili["body"].append(last_json)
        # print(round(start, 2), round(end, 2))
        # if round(end - start, 3) < 0.5:
        #     raise Exception("internal too short")
        # if last > start:
        #     raise Exception("time error")
        # last = end
    # print(json.dumps(_bili, ensure_ascii=False))
    return json.dumps(_bili, ensure_ascii=False)


def get_sub(video_id, lan):
    proxy = dict(parser.items("Proxy"))
    _url = api.format(lan.replace("-US", ""), video_id)
    _sou = s.get(url=_url, proxies=proxy).text
    if len(_sou) == 0:
        return None
    _return = to_bili(_sou)
    return _return


def send_subtitle(aid, lan, cid, fix=False, vid=None, add=None):
    # cid = s.get("https://api.bilibili.com/x/web-interface/view?aid={}".format(aid)).json()["data"]["cid"]
    _api = "https://api.bilibili.com/x/v2/dm/subtitle/draft/save"
    if not fix:
        sou = get_sub(vid, lan)
    else:
        sou = add
    if sou is None:
        return False
    send_data = {"type": 1,
                 "oid": cid,
                 "aid": aid,
                 "lan": lan,
                 "data": sou,
                 "submit": "true",
                 "sign": "false",
                 "csrf": csrf
                 }
    # print(re.findall("bili_jct=(.*?);", cookie)[0])
    # print(parse.urlencode(send_data))
    # print(json.dumps(send_data, ensure_ascii=False))
    _res = s.post(url=_api, data=parse.urlencode(send_data).replace("+", "%20").encode()).json()
    if _res["code"] != 0:
        logger.error(str(aid) + json.dumps(_res))
        return False
    logger.info("subtitle success: {}".format(aid))
    return True

def fix_sub():
    import time
    wait_api = "https://api.bilibili.com/x/v2/dm/subtitle/search/author/list?status=3&page=1&size=100"
    res = s.get(wait_api).json()["data"]["subtitles"]
    for _ in res:
        tmp_url = "https://api.bilibili.com/x/v2/dm/subtitle/show?oid={}&subtitle_id={}".format(_['oid'], _["id"])
        data = s.get(tmp_url).json()["data"]
        reject_comment = data["reject_comment"].split(':')[-1].split(',')
        subtitle_url = data["subtitle_url"]
        sub = s.get(subtitle_url).text
        for i in reject_comment:
            if "zh" in _["lan"]:
                sub = sub.replace(i, "".join(lazy_pinyin(i.replace('#', ""), style=Style.TONE)))
            else:
                sub = sub.replace(i, "#".join(i))
        if send_subtitle(_["aid"], lan=_["lan"], cid=_["oid"], fix=True, add=sub):
            res = s.post("https://api.bilibili.com/x/v2/dm/subtitle/del", data={"oid": _["oid"], "csrf": csrf, "subtitle_id": _["id"]}).json()
            if res["code"] != 0:
                logger.error(res["message"])
            else:
                logger.info("fix done:" + str(_['oid']))
        time.sleep(10)
        # break



if __name__ == "__main__":
    # res = get_sub("qaIghx4QRN4", "en")
    # print(res)
    # res = send_subtitle(vid="wxStlzunxCw", aid=46961283, lan="zh-CN")
    # print(res)
    fix_sub()
    pass
