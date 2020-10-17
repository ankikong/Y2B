import json
import os
import re
import subprocess
import requests
import xmltodict
import yaml
import argparse

UPLOADED_VIDEO_FILE = "uploaded_video.json"
CONFIG_FILE = "config.json"
COOKIE_FILE = "cookie.json"
VERIFY = os.environ.get("verify", "1") == "1"
PROXY = {
    "https": os.environ.get("https_proxy", None)
}


def get_gist(_gid, token):
    """通过 gist id 获取已上传数据"""
    rsp = requests.get(
        "https://api.github.com/gists/" + _gid,
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
        },
        verify=VERIFY,
    )
    if rsp.status_code == 404:
        raise Exception("gist id 错误")
    if rsp.status_code == 403 or rsp.status_code == 401:
        raise Exception("github TOKEN 错误")
    _data = rsp.json()
    uploaded_file = _data.get("files", {}).get(
        UPLOADED_VIDEO_FILE, {}).get("content", "{}")
    c = json.loads(_data["files"][CONFIG_FILE]["content"])
    t = json.loads(_data["files"][COOKIE_FILE]["content"])
    try:
        u = json.loads(uploaded_file)
        return c, t, u
    except Exception as e:
        print("gist 格式错误，重新初始化:", e)
    return c, t, {}


def update_gist(_gid, token, file, data):
    rsp = requests.post(
        "https://api.github.com/gists/" + _gid,
        json={
            "description": "y2b暂存数据",
            "files": {
                file: {
                    "content": json.dumps(data, indent="  ", ensure_ascii=False)
                },
            }
        },
        headers={
            "Accept": "application/vnd.github+json",
            "Authorization": "Bearer " + token,
        },
        verify=VERIFY,
    )
    if rsp.status_code == 404:
        raise Exception("gist id 错误")
    if rsp.status_code == 422:
        raise Exception("github TOKEN 错误")


def get_video_list(channel_id: str):
    res = requests.get(
        "https://www.youtube.com/feeds/videos.xml?channel_id=" + channel_id).text
    res = xmltodict.parse(res)
    ret = []
    for elem in res.get("feed", {}).get("entry", []):
        ret.append({
            "vid": elem.get("yt:videoId"),
            "title": elem.get("title"),
            "origin": "https://www.youtube.com/watch?v=" + elem["yt:videoId"],
            "cover_url": elem["media:group"]["media:thumbnail"]["@url"],
            # "desc": elem["media:group"]["media:description"],
        })
    return ret


def select_not_uploaded(video_list: list, _uploaded: dict):
    ret = []
    for i in video_list:
        if _uploaded.get(i["detail"]["vid"]) is not None:
            continue
        ret.append(i)
    return ret


def get_all_video(_config):
    ret = []
    for i in _config:
        res = get_video_list(i["channel_id"])
        for j in res:
            ret.append({
                "detail": j,
                "config": i
            })
    return ret


def download_video(url, out):
    subprocess.run(["yt-dlp", url, "-o", out], check=True)


def download_cover(url, out):
    res = requests.get(url, verify=VERIFY).content
    with open(out, "wb") as tmp:
        tmp.write(res)


def upload_video(video_file, cover_file, _config, detail):
    yml = {
        "line": "qn",
        "limit": 3,
        "streamers": {
            video_file: {
                "copyright": 2,
                "source": detail['origin'],
                "tid": _config['tid'],  # 投稿分区
                "cover": cover_file,  # 视频封面
                "title": detail['title'],
                "desc_format_id": 0,
                "desc": "搬运：" + detail["origin"],
                "dolby": 0,  # 杜比音效
                "dynamic": "",
                "subtitle": {
                    "open": 0,
                    "lan": ""
                },
                "tag": _config['tags'],
                "open_subtitle": False,
            }
        }
    }
    with open("config.yaml", "w") as tmp:
        t = yaml.dump(yml, Dumper=yaml.Dumper)
        tmp.write(t)
    p = subprocess.Popen(
        ["biliup", "upload", "-c", "config.yaml"],
        shell=True,
        stdout=subprocess.PIPE,
    )
    p.wait()
    if p.returncode != 0:
        raise Exception(p.stdout.read())
    buf = p.stdout.read().splitlines(keepends=False)
    if len(buf) < 2:
        raise Exception(buf)
    data = buf[-2]
    data = data.decode()
    data = re.findall("({.*})", data)[0]
    return json.loads(data)


def process_one(detail, config):
    download_video(detail["origin"], detail["vid"] + ".webm")
    download_cover(detail["cover_url"], detail["vid"] + ".jpg")
    ret = upload_video(detail["vid"] + ".webm",
                       detail["vid"] + ".jpg", config, detail)
    os.remove(detail["vid"] + ".webm")
    os.remove(detail["vid"] + ".jpg")
    return ret


def upload_process(gist_id, token):
    config, cookie, uploaded = get_gist(gist_id, token)
    with open("cookies.json", "w", encoding="utf8") as tmp:
        tmp.write(json.dumps(cookie))
    need_to_process = get_all_video(config)
    need = select_not_uploaded(need_to_process, uploaded)
    for i in need:
        ret = process_one(i["detail"], i["config"])
        i["ret"] = ret
        uploaded[i["detail"]["vid"]] = i
        update_gist(gist_id, token, UPLOADED_VIDEO_FILE, uploaded)
    os.remove("cookies.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("token", help="github api token", type=str)
    parser.add_argument("gistId", help="gist id", type=str)
    args = parser.parse_args()
    upload_process(args.gistId, args.token)
