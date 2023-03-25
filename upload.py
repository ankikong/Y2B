import json
import os
import re
import subprocess
import time
import requests
import xmltodict
import yaml
import argparse
import logging
import sys


UPLOAD_SLEEP_SECOND = 60 * 2  # 2min
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
        logging.error(f"gist 格式错误，重新初始化:{e}")
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


def get_file_size(filename):
    sz = os.path.getsize(filename)
    return int(sz/1024/1024)


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
            logging.debug(f'vid:{i["detail"]["vid"]} 已被上传')
            continue
        logging.debug(f'vid:{i["detail"]["vid"]} 待上传')
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


def download_video(url, out, format):
    try:
        msg = subprocess.check_output(
            ["yt-dlp", url, "-f", format, "-o", out], stderr=subprocess.STDOUT)
        logging.debug(msg[-512:])
        logging.info(f"视频下载完毕，大小：{get_file_size(out)} MB")
        return True
    except subprocess.CalledProcessError as e:
        out = e.output.decode("utf8")
        if "This live event will begin in" in out:
            logging.info("直播预告，跳过")
            return False
        if "Requested format is not available" in out:
            logging.debug("视频无此类型：" + format)
            return False
        if "This video requires payment to watch" in out:
            logging.info("付费视频，跳过")
            return False
        logging.error("未知错误:" + out)
        raise e


def download_cover(url, out):
    res = requests.get(url, verify=VERIFY).content
    with open(out, "wb") as tmp:
        tmp.write(res)


def upload_video(video_file, cover_file, _config, detail):
    title = detail['title']
    if len(title) > 80:
        title = title[:80]
    yml = {
        "line": "kodo",
        "limit": 3,
        "streamers": {
            video_file: {
                "copyright": 2,
                "source": detail['origin'],
                "tid": _config['tid'],  # 投稿分区
                "cover": cover_file,  # 视频封面
                "title": title,
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
    with open("config.yaml", "w", encoding="utf8") as tmp:
        t = yaml.dump(yml, Dumper=yaml.Dumper)
        logging.debug(f"biliup 业务配置：{t}")
        tmp.write(t)
    p = subprocess.Popen(
        ["biliup", "upload", "-c", "config.yaml"],
        stdout=subprocess.PIPE,
    )
    p.wait()
    if p.returncode != 0:
        raise Exception(p.stdout.read())
    buf = p.stdout.read().splitlines(keepends=False)
    if len(buf) < 2:
        raise Exception(buf)
    try:
        data = buf[-2]
        data = data.decode()
        data = re.findall("({.*})", data)[0]
    except Exception as e:
        logging.error(f"输出结果错误:{buf}")
        raise e
    logging.debug(f'上传完成，返回：{data}')
    return json.loads(data)


def process_one(detail, config):
    logging.info(f'开始：{detail["vid"]}')
    format = ["webm", "flv", "mp4"]
    v_ext = None
    for ext in format:
        if download_video(detail["origin"], detail["vid"] + f".{ext}", f"{ext}"):
            v_ext = ext
            logging.info(f"使用格式：{ext}")
            break
    if v_ext is None:
        logging.error("无合适格式")
        return False
    download_cover(detail["cover_url"], detail["vid"] + ".jpg")
    ret = upload_video(detail["vid"] + f".{v_ext}",
                       detail["vid"] + ".jpg", config, detail)
    os.remove(detail["vid"] + f".{v_ext}")
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
        if ret is None:
            continue
        i["ret"] = ret
        uploaded[i["detail"]["vid"]] = i
        update_gist(gist_id, token, UPLOADED_VIDEO_FILE, uploaded)
        logging.info(
            f'上传完成,vid:{i["detail"]["vid"]},aid:{ret["data"]["aid"]},bvid:{ret["data"]["bvid"]}')
        logging.debug(f"防验证码，暂停 {UPLOAD_SLEEP_SECOND} 秒")
        time.sleep(UPLOAD_SLEEP_SECOND)
    os.system("biliup renew 2>&1 > /dev/null")
    with open("cookies.json", encoding="utf8") as tmp:
        data = tmp.read()
        update_gist(gist_id, token, COOKIE_FILE, json.loads(data))
    os.remove("cookies.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("token", help="github api token", type=str)
    parser.add_argument("gistId", help="gist id", type=str)
    parser.add_argument("--logLevel", help="log level, default is info",
                        default="INFO", type=str, required=False)
    args = parser.parse_args()
    logging.basicConfig(
        stream=sys.stdout,
        level=logging.getLevelName(args.logLevel),
        format='%(filename)s:%(lineno)d %(asctime)s.%(msecs)03d %(levelname)s: %(message)s',
        datefmt="%H:%M:%S",
    )
    upload_process(args.gistId, args.token)
