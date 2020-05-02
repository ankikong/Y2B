# Y2B

把Youtube上的视频转投到哔哩哔哩

## 食用方法

1. 先执行`pip install -r requirements.txt`,然后再执行`python init.py`
2. 在conf文件夹,`setting.conf`,在里面填写b站账号密码,再填写`GoogleApi`的密钥
3. 因为目前还不支持区分单独投稿还是合集投稿,所以目前全部为合集投稿,第一个视频需要手动投稿
4. `channel.conf`是指定搬运的`Youtube`频道
5. 需要安装aria2c，并开启jsonrpc
6. 改完上述配置文件,直接`python main.py`就好了

## 软件依赖

- aria2
- ffmpeg

## aria2c 参考配置

``` conf
enable-rpc=true
disable-ipv6=false
rpc-allow-origin-all=true
rpc-listen-all=true
#event-poll=select
rpc-listen-port=6800
#rpc-secret=44a70bf2-fbf5-42f2-93c6-96359e3e53ee
#rpc-private-key=keys\server.key
#rpc-certificate=keys\server.crt
#rpc-secret=token
#rpc-user=user
#rpc-passwd=passgd

dir=D:\Downloads\aria\
disk-cache=128M
#file-allocation=prealloc
continue=true

input-file=D:\APP\aria2\aria2.session
save-session=D:\APP\aria2\aria2.session
save-session-interval=30

max-concurrent-downloads=1
max-connection-per-server=16
min-split-size=1M
split=10
max-overall-download-limit=0
max-download-limit=0
max-overall-upload-limit=0
max-upload-limit=0
allow-overwrite=true
auto-file-renaming=true

follow-torrent=true
listen-port=51413
bt-max-peers=55
enable-dht=true
enable-dht6=true
dht-listen-port=6881-6999
bt-enable-lpd=false
enable-peer-exchange=true
#bt-request-peer-speed-limit=50K
peer-id-prefix=-UT2210-
user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/69.0.3497.100 Safari/537.36
seed-ratio=1.0
#force-save=false
bt-hash-check-seed=true
bt-seed-unverified=true
bt-save-metadata=true

```

## 更新记录

- 2020.05.02
  - 增加自定义选项
  - 新增1080P
- 2020.05.01
  - 修复一些奇奇怪怪的bug
- 2020.04.29
  - 出现编码性错误，把之前所有的提交记录全部删除
