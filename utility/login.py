#!/usr/bin/python
# -*- coding: utf-8 -*-
import json,time,hashlib
from urllib.parse import urlencode
import requests
from base64 import b64encode
from Crypto.Cipher import PKCS1_v1_5
from Crypto.PublicKey import RSA
from hashlib import md5
from urllib import parse
# pycryptodome pycrypto

proxy = None

APP_KEY2 = '1d8b6e7d45233436'
APP_SECRET2 = '560c52ccd288fed045859ed18bffd973'

APP_KEY = '4409e2ce8ffd12b8'
APP_SECRET = '59b43e04ad6965f34319062b478f83dd'

APP_KEY3 = '4ebafd7c4951b366'
APP_SECRET3 = '8cb98205e9b2ad3669aad0fce12a4c13'

header = {
	"User-Agent": "Mozilla/5.0 BiliDroid/5.53.1",
	"Accept-encoding": "gzip",
	"Buvid": "000ce0b9b9b4e342ad4f421bcae5e0ce",
	"Display-ID": "146771405-1521008435",
	"Accept-Language": "zh-CN",
	"Accept": "text/html,application/xhtml+xml,*/*;q=0.8",
	"Connection": "keep-alive",
}

PCHeader = {
	"Upgrade-Insecure-Requests": "1",
	"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/80.0.3987.100 Safari/537.36",
	"Sec-Fetch-Dest": "document",
	"Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.9",
	"Sec-Fetch-Site": "none",
	"Sec-Fetch-Mode": "navigate",
	"Accept-Encoding": "gzip, deflate, br",
	"Accept-Language": "zh-CN,zh;q=0.9,en-US;q=0.8,en;q=0.7,zh-TW;q=0.6"
}

def getSign(tmp):
	if type(tmp) is dict:
		ttmp = []
		for i in sorted(tmp.keys()):
			ttmp.append(i + "=" + tmp[i])
		tmp = "&".join(ttmp)
	return tmp + "&sign=" + md5((tmp + APP_SECRET).encode()).hexdigest()


def login(userid,password):
	baseurl="https://passport.bilibili.com/api/v2/oauth2/login"
	url = 'http://passport.bilibili.com/api/oauth2/getKey'

	keyData = "appkey=" + APP_KEY
	keyData = getSign(keyData)
	header["Content-Type"] = 'application/x-www-form-urlencoded; charset=UTF-8'
	token = requests.post(url, data=keyData, headers=header).json()["data"]
	key = token['key'].encode()
	_hash=token['hash'].encode()

	key = RSA.importKey(key)
	cipher = PKCS1_v1_5.new(key)
	tmp = cipher.encrypt(_hash + password.encode())

	password = b64encode(tmp)
	password = parse.quote_plus(password)
	userid = parse.quote_plus(userid)
	item = "appkey=" + APP_KEY + "&password=" + password + "&username=" + userid
	item = getSign(item)
	page_temp = requests.post(baseurl, data=item, proxies=proxy, headers=header).json()

	if(page_temp['code'] != 0):
		print(page_temp['message'])
		raise Exception(page_temp['message'])

	print(page_temp)
	access_key = page_temp["data"]['token_info']['access_token']
	refresh_token = page_temp["data"]['token_info']["refresh_token"]
	return access_key, refresh_token


def get_cookies(access_key):
	session = requests.Session()
	url ="https://passport.bilibili.com/api/login/sso?"
	item = {'access_key': access_key,
			'appkey': APP_KEY, 
			'gourl': 'https%3a%2f%2faccount.bilibili.com%2faccount%2fhome',
			}
	item = "access_key=" + access_key + "&appkey=" + APP_KEY + "&gourl=https%3A%2F%2Faccount.bilibili.com%2Faccount%2Fhome"
	session.get(url + getSign(item))
	cookie = ""
	tmp = session.cookies.get_dict()
	for i in tmp:
		cookie += "{}={}; ".format(i, tmp[i])
	return cookie.strip()


def refreshToken(token, refreshtoken):
	url = "https://passport.bilibili.com/api/oauth2/refreshToken"
	params = {"access_token": token, "refresh_token": refreshtoken, "appkey": APP_KEY}
	params = getSign(params)
	header["Content-Type"] = 'application/x-www-form-urlencoded; charset=UTF-8'
	res = requests.post(url, data=params, headers=header).text
	return res


def checkToken(token):
	url = "https://passport.bilibili.com/api/v3/oauth2/info"
	param = "access_token=" + token + "&appkey=" + APP_KEY
	param = getSign(param)
	# header["Content-Type"] = 'application/x-www-form-urlencoded; charset=UTF-8'
	res = requests.get(url + param, headers=header).content.decode()
	return res


def getCookie():
	pass


if __name__ == "__main__":
	pass
	# print(login("", ""))
	# print(get_cookies(""))
	# refreshToken('', '')
	# checkToken("")
