from configparser import ConfigParser
from logging import config
import requests
from utility import login
import main_upload
config.fileConfig("setting.conf")

parser = ConfigParser()
parser.read("setting.conf")

def loginAndCheck():
    header = dict(parser.items("BiliHeader"))
    url = "https://api.bilibili.com/x/web-interface/nav"
    res = requests.get(url, headers=header).json()
    if not res["data"]["isLogin"]:
        token = parser.get("BiliToken", "token")
        refreshToken = parser.get("BiliToken", "refreshToken")
        login.refreshToken(token, refreshToken)
        cookie = login.get_cookies(token)
        parser.set("BiliHeader", "Cookie", cookie.replace('%','%%'))
        parser.write(open("setting.conf", "w"))

loginAndCheck()
main_upload.run()
# import main_sub2
# main_sub2.run()
