# Y2B

把Youtube上的视频转投到哔哩哔哩

## 食用方法

1. 先执行`pip install -r requirements.txt`,然后再执行`python init.py`
2. 在conf文件夹,`setting.conf`,在里面填写b站账号密码,再填写`GoogleApi`的密钥
3. 把`setting.conf`里面的**所有中文全部删掉**，不然会报错
4. 因为目前还不支持区分单独投稿还是合集投稿,所以目前全部为合集投稿,第一个视频需要手动投稿
5. `channel.conf`是指定搬运的`Youtube`频道
6. 需要安装aria2c，并开启jsonrpc
7. 改完上述配置文件,直接`python main.py`就好了

## 软件依赖

- aria2
- ffmpeg

## aria2c 参考配置

[aria.conf](./conf/aria.conf)

## 更新记录

- 2020.05.03
  - 迁移配置文件为yaml
  - 修复封面丢失的问题
  - 修复字幕投递
- 2020.05.02
  - 增加自定义选项
  - 新增1080P
- 2020.05.01
  - 修复一些奇奇怪怪的bug
- 2020.04.29
  - 出现编码性错误，把之前所有的提交记录全部删除
