import requests
import json
def check_status():
    cookie = json.load(open("config.json", encoding="utf8"))["cookie"]
    url = "https://api.bilibili.com/x/web-interface/nav"
    res = requests.get(url, headers={"cookie": cookie}).json()
    return res["data"]["isLogin"]

def download(url, proxy={}, dirs="D:/", file="", jsonrpc="http://localhost:6800/jsonrpc"):
    proxyConv = {}
    if proxy.get("http") is not None:
        proxyConv["http-proxy"] = proxy.get("http")
    if proxy.get("https") is not None:
        proxyConv["https-proxy"] = proxy.get("https")
    data = {
        "jsonrpc": "2.0",
        "method": "aria2.addUri",
        "id": 1,
        "params": [[url],
            {
                "dir": dirs,
                "max-connection-per-server": "16",
                **proxyConv
            }
        ]
    }
    # print(json.dumps(data))
    return requests.post(jsonrpc, json=data).json()

def telStatus(gid, jsonrpc="http://localhost:6800/jsonrpc"):
    data = {
        "jsonrpc": "2.0",
        "method": "aria2.tellStatus",
        "id": 1,
        "params": [str(gid)]
    }
    return requests.post(jsonrpc, json=data).json()

def telFinished(gid, jsonrpc="http://localhost:6800/jsonrpc"):
    rs = telStatus(gid, jsonrpc=jsonrpc)["result"]
    if rs["status"] == 'complete':
        return 1
    if rs["status"] == 'active' or rs["status"] == 'waiting':
        return 0
    if rs["status"] == 'error':
        return -1
    return -1

def telFileSize(gid, jsonrpc="http://localhost:6800/jsonrpc"):
    return int(telStatus(gid, jsonrpc=jsonrpc)["result"]["totalLength"])

def telFileLocate(gid, jsonrpc="http://localhost:6800/jsonrpc"):
    return telStatus(gid, jsonrpc=jsonrpc)["result"]["files"][0]["path"]
