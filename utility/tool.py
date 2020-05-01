#!/usr/bin/python
# -*- coding: utf-8 -*-
import json, time
import requests
from base64 import b64encode
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from hashlib import md5
from urllib import parse
import os
import logging.config
# pycryptodome pycrypto


# config tool start

from configparser import ConfigParser
import sqlite3

settingConf = "conf/setting.conf"
channelConf = "conf/channel.conf"
dbPath = "data/data.db"

logging.config.fileConfig(settingConf)

def _run(file):
    parser = ConfigParser()
    content = parser.read(file, encoding="utf8")
    return parser, content

def getSettingConf():
    return _run(settingConf)[0]

def getChannelConf():
    return _run(channelConf)

def getDB():
    return sqlite3.connect(dbPath)

# config tool end


# download tool start

class DownloadManager:
    def __init__(self, url, proxy={}, dirs="E:/", files=None, jsonrpc="http://localhost:6800/jsonrpc"):
        self.url = url
        self.proxy = proxy
        self.dirs = dirs
        self.files = files
        self.jsonrpc = jsonrpc
        self._session = requests.session()
        self._gid = None
        self._fd = None

    def download(self):
        proxyConv = {}
        if self.proxy.get("http") is not None:
            proxyConv["http-proxy"] = self.proxy.get("http")
        if self.proxy.get("https") is not None:
            proxyConv["https-proxy"] = self.proxy.get("https")
        data = {
            "jsonrpc": "2.0",
            "method": "aria2.addUri",
            "id": 1,
            "params": [[self.url],
                {
                    "max-connection-per-server": "16",
                    "out": self.files,
                    **proxyConv
                }
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
        return self.telStatus()["result"]["files"][0]["path"]

    def telFinished(self):
        rs = self.telStatus()["result"]
        if rs["status"] == 'complete':
            return 1
        if rs["status"] == 'active' or rs["status"] == 'waiting':
            return 0
        if rs["status"] == 'error':
            return -1
        return -1
    
    def waitForFinishing(self):
        while True:
            rs = self.telFinished()
            if rs == 1:
                return 1
            elif rs == -1:
                return -1
            else:
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
			ttmp.append(i + "=" + str(tmp[i]))
		tmp = "&".join(ttmp)
	return tmp + "&sign=" + md5((tmp + APP_SECRET).encode("utf-8")).hexdigest()

def getSign2(params:dict) -> dict:
    tmp = []
    for i in params:
        tmp.append("{}={}".format(i, parse.quote_plus(str(params[i]))))
    tmp.sort()
    tmp = "&".join(tmp)
    params["sign"] = md5((tmp + APP_SECRET).encode("utf-8")).hexdigest()
    return params

class AccountManager:

    def __init__(self, accountName):
        """ accountName means the AccountName in the setting.conf
            这里的accountName就是setting.conf里面的AccountName
        """
        self.__setting = getSettingConf()
        self.__profileName = accountName
        self.__data = dict(self.__setting.items(accountName))
        self.mid = None
        self.cookie = None

    @staticmethod
    def loginWithIdAndPwd(userid,password):
        baseurl="https://passport.bilibili.com/api/v3/oauth2/login"
        url = 'https://passport.bilibili.com/api/oauth2/getKey'

        s = requests.session()
        # s.verify = False
        s.headers.update(header)

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
        token = s.post(url, params=keyData, proxies=proxy).json()["data"]
        key = token['key'].encode()
        _hash=token['hash'].encode()

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
        page_temp = s.post(baseurl, params=item, proxies=proxy).json()

        if(page_temp['code'] != 0):
            raise Exception(page_temp['message'])

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
        parser = getSettingConf()
        usr = self.__data.get("account")
        pwd = self.__data.get("password")
        if usr is None or pwd is None:
            # 配置文件没有账号密码，无法登录
            raise Exception("Please input you account and password into " + settingConf)
        token, reToken = AccountManager.loginWithIdAndPwd(usr, pwd)
        self.__data["token"] = token
        self.__data["refreshtoken"] = reToken
        parser.set(self.__profileName, "token", token)
        parser.set(self.__profileName, "refreshtoken", reToken)
        with open(settingConf, "w") as _tmp:
            parser.write(_tmp)

    @staticmethod
    def refreshTokenWithTokenAndRToken(token, refreshtoken):
        """ Postpone expiration; 推迟token的过期时间(续命)
        """
        url = "https://passport.bilibili.com/api/oauth2/refreshToken"
        params = {"access_token": token, "refresh_token": refreshtoken, "appkey": APP_KEY}
        params = getSign(params)
        header["Content-Type"] = 'application/x-www-form-urlencoded; charset=UTF-8'
        res = requests.post(url, data=params, headers=header).text
        return res

    def refreshToken(self):
        """ Postpone expiration; 推迟token的过期时间(续命)
        """
        token, reToken = self.__data["token"], self.__data["refreshtoken"]
        return AccountManager.refreshTokenWithTokenAndRToken(token, reToken)

    def __getPersonInfo(self):
        token = self.__data.get("token", "")
        url = "https://api.bilibili.com/x/web-interface/nav?access_key=" + token
        res = requests.get(url).json()
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
        return self.__data["token"]

    def userInformation(self):
        _data = {}
        rs = self.__getPersonInfo()
        _data["uname"] = rs["data"]["uname"]
        _data["mid"] = rs["data"]["mid"]
        return _data
    
    def __getCookie(self):
        url = "https://passport.bilibili.com/api/login/sso?" + getSign({"access_key": self.getToken(), "appkey": APP_KEY})
        # print(url)
        s = requests.session()
        s.get(url)
        return s.cookies.get_dict()

    def getCookies(self):
        """ use token to get cookies
            通过token获取cookies
        """
        if self.cookie is None:
            self.cookie = self.__getCookie()
        return self.cookie

# verify tool end

if __name__ == "__main__":
    ac = AccountManager("Anki")
    print(ac.getToken())
    print(ac.userInformation())
    print(ac.getMid())
    cookie = ac.getCookies()
    rs = requests.get("https://api.bilibili.com/x/web-interface/nav", cookies=cookie).text
    print(rs)
