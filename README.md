# ChatMemOllama
[![Stars](https://img.shields.io/github/stars/LIghtJUNction/ChatMemOllama?label=stars)](https://github.com/LIghtJUNction)
[![Download](https://img.shields.io/github/downloads/LIghtJUNction/ChatMemOllama/total)](https://github.com/LIghtJUNction/ChatMemOllama/releases)
[![Release](https://img.shields.io/github/v/release/LIghtJUNction/ChatMemOllama?label=release)](https://github.com/LIghtJUNction/ChatMemOllama/releases/latest)
[![License](https://img.shields.io/github/license/LIghtJUNction/ChatMemOllama?label=License)](https://choosealicense.com/licenses/gpl-3.0)

ChatMemOllama 是一个 WeChat公众号 的聊天机器人项目，支持 AI 对话和管理员模式。 包含关键词匹配回答 - AI模式与关键词匹配模式切换 - 优化5秒超时处理 - 微信公众号使用在线/本地AI大模型回答用户 - 函数调用能力 - 目前状态：开发中
![Designer](https://github.com/user-attachments/assets/31ac7b3c-850d-4e45-8870-bc2be83a1c5c)


[![Alt](https://repobeats.axiom.co/api/embed/61c5ea935a0eaf66e11c190407c20fa65da9ffa5.svg "Repobeats analytics image")](https://github.com/LIghtJUNction/ChatMemOllama/)


# 更新
[计划改用robyn以加快速度](https://github.com/sparckles/robyn)

# sponsor
[buy me a coffee](https://github.com/LIghtJUNction/lightjunction/tree/master/sponsor)


## 终极目标：

创造一个拥有持久记忆的私人AI数字人
像和其他人聊天一样，在微信上即可随时随地开聊


加入开发者群聊，共同进步
885986098


# 效果展示

### 在线搜索

![1730618598001](images/README/1730618598001.png)

![1730618625240](images/README/1730618625240.png)

### 查询课表

![1730618537808](images/README/1730618537808.png)

（这个函数调用属于个人用途，每个学校的格式可能有所不同，这里是通过抓包获取的课表信息  如果不会抓包可以试试直接套用我这个格式。）

## 将微信一系列表情包：[表情名]写在系统提示词里使用效果--模型llama3.1:8b

AI就学会了使用微信表情包和我进行对话
![效果一](images/README/1729082801293.png)

## 使用的模型为llama3.1

![效果二](images/README/1729082774724.png)

## 项目结构

```
doc/ 
chatmemollama/
  

ChatMemOllama_dev.py
    config.json
    LICENSE

README.md

    Users/
docs/
    zh_cn.md
images/
    README/
LICENSE
Old_version/
  

ChatMemOllama.py


    JustChat.py
  

readme.md




README.md




requirements.txt


```

## 安装依赖

正式版未发布-不提供具体的依赖安装指南

```plaintext
fastapi
wechatpy
uvicorn
requests
beautifulsoup4
mem0
tavily-Python
```

您可以使用以下命令安装依赖：

```sh
pip install -r 

requirements.txt


```

## 配置文件

`关于配置的解释` 

```json
{
    "WECHAT_TOKEN": "your_wechat_token",
    "APPID": "your_app_id",
    "EncodingAESKey": "your_encoding_aes_key",
    "AdminID": "your_admin_id",
    "mem0config": "your_mem0_config",
    "model": "your_model",
    "verify_status": "False",
    "Tavilykey": "your_tavily_key"
}
```

![1730622974167](images/README/1730622974167.png)

这是微信公众号的配置  -- 在URL/wechat 接收信息后转发给本地端口8000（默认）

## 运行项目

您可以使用以下命令启动项目：

```py
chatmemollama_dev.py
```

## 功能说明

### 用户命令

- `help` - 查看帮助
- `sudo su` - 进入管理员模式（仅限管理员）
- `AI` - 重新开启 AI 对话
- `exit` - 退出 AI 对话

### 管理员命令(旧版有-新版正在制作)

- `ps` - 列出正在运行的模型
- `verify_status` - 确认身份（重启后对用户0免鉴权）
- `list` - 列出已有模型
- `models` - 切换模型
- `pull` - 拉取模型
- `exit` - 退出管理员模式
- `help` - 查看管理员命令帮助

## 贡献

欢迎提交问题和贡献代码！请确保您的代码符合项目的编码规范。


## 后续考虑制作GUI管理界面

## 早期开发阶段 任何部分都可能会变！

## 许可证

本项目使用 [Apache2.0 许可证](LICENSE)
