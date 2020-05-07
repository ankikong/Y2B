#!/usr/bin/python
# -*- coding: utf-8 -*-
import json
import time
import requests
from base64 import b64encode
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from hashlib import md5
from urllib import parse
import os
import logging.config
import threading
import yaml
import sqlite3
# pycryptodome pycrypto


# config tool start
_settingConf = "conf/setting.yaml"
_channelConf = "conf/channel.yaml"
_loggingConf = "conf/logging.yaml"
_dbPath = "data/data.db"


class Config:
    SETTING = _settingConf
    CHANNEL = _channelConf
    LOGGING = _loggingConf

    def __init__(self, file):
        self.__select = file
        self.__lock = threading.Lock()
        with open(file, encoding="utf8") as tmp:
            self.data: dict = yaml.load(tmp.read(), Loader=yaml.FullLoader)
        if file == Config.LOGGING:
            _tmp: str = self.data["handlers"]["file"]["filename"]
            self.data["handlers"]["file"]["filename"] = _tmp.format(
                time.strftime("%Y-%m-%d"))

    def __getitem__(self, k):
        return self.data[k]

    def __setitem__(self, k, v):
        self.data[k] = v

    def get(self, k, val=None):
        return self.data.get(k, val)

    def save(self):
        if self.__select == Config.LOGGING:
            return
        self.__lock.acquire()
        with open(self.__select, "w", encoding="utf8") as tmp:
            yaml.dump(self.data, tmp)
        self.__lock.release()


loggingConf = Config(Config.LOGGING)
settingConf = Config(Config.SETTING)
channelConf = Config(Config.CHANNEL)

# 初始化logger
logging.config.dictConfig(loggingConf.data)


def getLogger() -> logging.Logger:
    return logging.getLogger("fileLogger")


def getDB():
    return sqlite3.connect(_dbPath)

# config tool end

# my requests session start


class Session(requests.Session):

    def __init__(self):
        super(Session, self).__init__()
        self.proxy = settingConf["Proxy"]
        self.timeouts: tuple = (120, 240)
        self.retryDelay: int = 1
        self.retry: int = 8
        self.headers.update({
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-TW;q=0.6",
            # "cache-control": "max-age=0",
            # "Sec-Fetch-Dest": "empty",
            # "Sec-Fetch-Mode": "cors",
            # "Sec-Fetch-Site": "same-site"
        })

    def req(self, method: str, url: str, useProxy: bool = False, wantStatusCode: int = None, **args) -> requests.models.Response:
        args = args.copy()
        if useProxy:
            args["proxies"] = self.proxy
        # if args.get("headers") is None:
        #     args["headers"] = {
        #         "referer": url,
        #         "origin": url
        #     }
        if args.get("timeout") is None:
            args["timeout"] = self.timeouts
        nowDelay = self.retryDelay
        logger = getLogger()
        for _ in range(self.retry):
            try:
                rs = self.request(method, url, **args)
                if wantStatusCode is None or rs.status_code == wantStatusCode:
                    return rs
                else:
                    reqHead = dict(rs.request.headers)
                    if reqHead.get("Cookie", None) is not None:
                        reqHead.pop("Cookie")
                    logger.debug(f"want[{wantStatusCode}], "
                                 f"get[{rs.status_code}], "
                                 f"url[{rs.url}], "
                                 f"headers[{dict(rs.headers)}], "
                                 f"rs[{rs.text}], "
                                 f"req.head[{reqHead}]"
                                 f"retrying...")
            except Exception:
                logger.debug("retrying......", exc_info=True)
            time.sleep(nowDelay)
            nowDelay += nowDelay
        logger.error(f"network, {method} {url} want[{wantStatusCode}]")
        raise Exception("check network status")

    def get(self, url, useProxy: bool = False, wantStatusCode: int = None, **args) -> requests.models.Response:
        return self.req("GET", url, useProxy, wantStatusCode, **args)

    def post(self, url, useProxy: bool = False, wantStatusCode: int = None, **args) -> requests.models.Response:
        return self.req("POST", url, useProxy, wantStatusCode, **args)

    def put(self, url, useProxy: bool = False, wantStatusCode: int = None, **args) -> requests.models.Response:
        return self.req("PUT", url, useProxy, wantStatusCode, **args)

# my requests session end

# download tool start


class DownloadManager:
    def __init__(self, url, headers=None, proxy={}, dirs="E:/", files=None, jsonrpc="http://localhost:6800/jsonrpc"):
        self.url = url
        self.proxy = proxy
        self.dirs = dirs
        self.files = files
        self.jsonrpc = jsonrpc
        self._session = requests.session()
        self._gid = None
        self._fd = None
        self.__retry = 3
        self.headers = headers

    def download(self):
        proxyConv = {}
        if self.proxy.get("http") is not None:
            proxyConv["http-proxy"] = self.proxy.get("http")
        if self.proxy.get("https") is not None:
            proxyConv["https-proxy"] = self.proxy.get("https")
        data = {
            "jsonrpc": "2.0",
            "method": "aria2.addUri",
            "id": int(time.time()),
            "params": [[self.url], {
                "max-connection-per-server": "16",
                "out": self.files,
                "header": self.getHeaders(),
                **proxyConv}
            ]
        }
        # print(json.dumps(data))
        rs = self._post(data)
        self._gid = rs['result']
        return rs

    def _post(self, json):
        return self._session.post(url=self.jsonrpc, json=json).json()

    def telStatus(self):
        data = {
            "jsonrpc": "2.0",
            "method": "aria2.tellStatus",
            "id": 1,
            "params": [str(self._gid)]
        }
        return self._post(data)

    def telFileSize(self):
        return int(self.telStatus()["result"]["totalLength"])

    def telFileLocate(self):
        return self.telStatus()["result"]["files"][0]["path"].replace("//", "/")

    def telFinished(self):
        rs = self.telStatus()["result"]
        logger = getLogger()
        total = int(rs["totalLength"])
        if total == 0:
            total = 1
        completedLength = int(rs["completedLength"])
        percent = (completedLength / total) * 100
        logger.info(f"file download: {percent:.4}%")
        if rs["status"] == 'complete':
            return 1
        if rs["status"] == 'active' or rs["status"] == 'waiting':
            return 0
        if rs["status"] == 'error':
            logger.debug(json.dumps(rs))
            logger.error(rs["errorMessage"])
            return -1
        logger.debug(json.dumps(rs))
        logger.error("unknown error")
        return -1

    def waitForFinishing(self):
        retry = 0
        while True:
            rs = self.telFinished()
            if rs == 1:
                return 1
            elif rs == -1:
                logger = getLogger()
                if retry < self.__retry:
                    self.download()
                    retry += 1
                    logger.error(f"download failed, retry [{retry}] times")
                else:
                    logger.debug(json.dumps(self.getOptions()))
                    return -1
            time.sleep(10)

    def getFile(self):
        if self._fd is None:
            filePath = self.telFileLocate()
            self._fd = open(filePath, "rb")
        return self._fd

    def close(self, deleteFile=False):
        if self._fd is not None:
            self._fd.close()
            self._fd = None

    def deleteFile(self):
        filePath = self.telFileLocate()
        if os.path.exists(filePath):
            os.remove(filePath)

    def getDirs(self):
        rs = self._post(
            {"jsonrpc": "2.0", "method": "aria2.getGlobalOption", "id": 1, "params": []})
        return (str(rs["result"]["dir"]).replace("\\", "/") + "/").replace("//", "/")

    def getOptions(self):
        rs = self._post({
            "jsonrpc": "2.0",
            "method": "aria2.getOption",
            "id": 1,
            "params": [self._gid]
        })
        return rs

    def getHeaders(self):
        header = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/81.0.4044.129 Safari/537.36",
            "Accept": "*/*",
            "Origin": "https://www.youtube.com",
            "Referer": "https://www.youtube.com/",
            "Accept-Encoding": "gzip, deflate, br",
            "Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-TW;q=0.6",
        }
        if self.headers is not None:
            header = self.headers
        rs = []
        for i in header:
            rs.append(f"{i}: {header[i]}")
        return rs
# download tool end


# verify tool start

# proxy = {"https": "https://127.0.0.1:8888"}
proxy = None

APP_KEY = '1d8b6e7d45233436'
APP_SECRET = '560c52ccd288fed045859ed18bffd973'

APP_KEY4 = '4409e2ce8ffd12b8'
APP_SECRET4 = '59b43e04ad6965f34319062b478f83dd'

APP_KEY3 = '4ebafd7c4951b366'
APP_SECRET3 = '8cb98205e9b2ad3669aad0fce12a4c13'

APP_KEY2 = "27eb53fc9058f8c3"
APP_SECRET2 = "c2ed53a74eeefe3cf99fbd01d8c9c375"

header = {
    "Display-ID": "XZDA0A8D4BE3EA66CA7BA1C05CB00E8A56143-1584023167",
    "Buvid": "XZDA0A8D4BE3EA66CA7BA1C05CB00E8A56143",
    "User-Agent": "Mozilla/5.0 BiliDroid/5.39.0 (bbcallen@gmail.com)",
    "Device-ID": "KREhESMUJxAnQ3FBPUE6Rz8OaV1vDHwWcg",
    # "Content-Type": "application/x-www-form-urlencoded; charset=utf-8",
    "Accept-Encoding": "gzip",
}


def getSign(tmp):
    if type(tmp) is dict:
        ttmp = []
        for i in sorted(tmp.keys()):
            ttmp.append(f"{i}={tmp[i]}")
        tmp = "&".join(ttmp)
    return tmp + "&sign=" + md5((tmp + APP_SECRET).encode("utf-8")).hexdigest()


def getSign2(params: dict) -> dict:
    tmp = []
    for i in params:
        tmp.append(f"{i}={parse.quote_plus(str(params[i]))}")
    tmp.sort()
    tmp = "&".join(tmp)
    params["sign"] = md5((tmp + APP_SECRET).encode("utf-8")).hexdigest()
    return params


class AccountManager:

    def __init__(self, accountName):
        """ accountName means the AccountName in the setting.conf
            这里的accountName就是setting.conf里面的AccountName
        """
        self.__setting = settingConf
        self.__profileName = accountName
        self.mid = None
        self.cookie = None
        self.__s = Session()
        self.__s.headers = header

    def loginWithIdAndPwd(self, userid, password):
        baseurl = "https://passport.bilibili.com/api/v3/oauth2/login"
        url = 'https://passport.bilibili.com/api/oauth2/getKey'

        # s = requests.Session()
        # s.verify = False
        # s.headers.update(header)

        keyItem = {
            "appkey": APP_KEY,
            "build": "5390000",
            "channel": "bili",
            "mobi_app": "android",
            "platform": "android",
            "ts": int(time.time()),
        }

        # keyData = "appkey=" + APP_KEY
        keyData = getSign2(keyItem)
        # header["Content-Type"] = 'application/x-www-form-urlencoded; charset=UTF-8'
        token = self.__s.post(url, params=keyData,
                              proxies=proxy).json()["data"]
        key = token['key'].encode()
        _hash = token['hash'].encode()

        key = RSA.importKey(key)
        cipher = PKCS1_v1_5.new(key)
        tmp = cipher.encrypt(_hash + password.encode())
        userid = str(userid)
        password = b64encode(tmp).decode()
        # password = parse.quote_plus(password)
        items = {
            "appkey": APP_KEY,
            "build": "5390000",
            "channel": "bili",
            "mobi_app": "android",
            "password": password,
            "platform": "android",
            "ts": int(time.time()),
            "username": userid,
        }
        # item = "appkey=" + APP_KEY + "&password=" + password + "&username=" + userid
        item = getSign2(items)
        page_temp = self.__s.post(baseurl, params=item, proxies=proxy).json()
        if(page_temp['code'] != 0):
            logger = getLogger()
            logger.error(page_temp['message'])
            logger.error("check network, account, password settings...")
            exit("error")

        # print(page_temp)
        access_key = page_temp["data"]['token_info']['access_token']
        refresh_token = page_temp["data"]['token_info']["refresh_token"]
        return access_key, refresh_token

    def login(self):
        """ Login with usrname and password in `setting.conf`. 
            用setting.conf里面的账号密码登录
        """
        if self.checkIsLogin():
            return
        usr = self.__setting[self.__profileName].get("Account")
        pwd = self.__setting[self.__profileName].get("Password")
        if usr is None or pwd is None:
            # 配置文件没有账号密码，无法登录
            logger = getLogger()
            logger.error("no account, password in settings.yaml")
            exit("error")
        token, reToken = self.loginWithIdAndPwd(usr, pwd)
        self.__setting[self.__profileName]["token"] = token
        self.__setting[self.__profileName]["refreshtoken"] = reToken
        self.save()

    def save(self):
        self.__setting.save()

    def refreshTokenWithTokenAndRToken(self, token, refreshtoken):
        """ Postpone expiration; 推迟token的过期时间(续命)
        """
        url = "https://passport.bilibili.com/api/oauth2/refreshToken"
        params = {"access_token": token,
                  "refresh_token": refreshtoken, "appkey": APP_KEY}
        params = getSign(params)
        header["Content-Type"] = 'application/x-www-form-urlencoded; charset=UTF-8'
        res = self.__s.post(url, data=params, headers=header).text
        return res

    def refreshToken(self):
        """ Postpone expiration; 推迟token的过期时间(续命)
        """
        token, reToken = self.__setting[self.__profileName]["token"], self.__setting[self.__profileName]["refreshtoken"]
        return self.refreshTokenWithTokenAndRToken(token, reToken)

    def __getPersonInfo(self):
        token = self.__setting[self.__profileName].get("token", "")
        url = "https://api.bilibili.com/x/web-interface/nav?access_key=" + token
        res = self.__s.get(url).json()
        return res

    def checkIsLogin(self):
        """ check whether token is expired; 检查配置文件中token是否过期
        """
        res = self.__getPersonInfo()
        return res["data"]["isLogin"]

    def getMid(self):
        """ get user mid; 获取账号的mid
        """
        if self.mid is None:
            res = self.__getPersonInfo()
            self.mid = res["data"]["mid"]
        return self.mid

    def getToken(self):
        """ check whether token is expired and return token. If expired,relogin.
            检查配置文件中的token是否过期，并返回token。如果过期了的话，会重新登录
        """
        self.login()
        self.refreshToken()
        return self.__setting[self.__profileName]["token"]

    def userInformation(self):
        _data = {}
        rs = self.__getPersonInfo()
        _data["uname"] = rs["data"]["uname"]
        _data["mid"] = rs["data"]["mid"]
        return _data

    def __getCookie(self):
        if int(time.time()) - self.__setting[self.__profileName].get("ts", 0) > 1e5:
            url = "https://passport.bilibili.com/api/login/sso?" + \
                getSign({"access_key": self.getToken(), "appkey": APP_KEY})
            # print(url)
            self.__s.get(url)
            tmp = self.__s.cookies.get_dict()
            self.__setting[self.__profileName]["cookie"] = tmp
            self.__setting[self.__profileName]["ts"] = int(time.time())
            self.save()
            return tmp
        else:
            return self.__setting[self.__profileName]["cookie"]

    def getCookies(self):
        """ use token to get cookies
            通过token获取cookies
        """
        if self.cookie is None:
            self.cookie = self.__getCookie()
        return self.cookie

# verify tool end

# unique pool start


class UniquePool:
    def __init__(self):
        self.__pool = set()
        self.__lock = threading.Lock()

    def checkAndInsert(self, key) -> bool:
        self.__lock.acquire()
        rs = key not in self.__pool
        self.__pool.add(key)
        self.__lock.release()
        return rs

    def remove(self, key) -> bool:
        self.__lock.acquire()
        rs = key in self.__pool
        if rs:
            self.__pool.remove(key)
        self.__lock.release()
        return rs

    def size(self):
        return len(self.__pool)

# unique pool stop

# MyThreadTool


class Thread(threading.Thread):
    def __init__(self, **args):
        threading.Thread.__init__(self, **args)

    def run(self):
        try:
            if self._target:
                self._target(*self._args, **self._kwargs)
        except Exception:
            logger = getLogger()
            logger.error("Thread:", exc_info=True)
            del logger
        finally:
            # Avoid a refcycle if the thread is running a function with
            # an argument that has a member that points to the thread.
            del self._target, self._args, self._kwargs

# MyThreadTool end


if __name__ == "__main__":
    ac = AccountManager("Anki")
    print(ac.getToken())
    print(ac.userInformation())
    print(ac.getMid())
    cookie = ac.getCookies()
    # rs = requests.get("https://api.bilibili.com/x/web-interface/nav", cookies=cookie).text
    # print(rs)
    # print(Session.get("https://baidu.com", proxies={"https":"http://127.0.0.1:8888"}, verify=False))
    # print(Session.post("https://baidu.com", proxies={"https":"http://127.0.0.1:8888"}, headers={"fuck": "fuck"}, verify=False))
    pass
