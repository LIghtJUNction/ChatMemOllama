# ChatMemOllama

ChatMemOllama 是一个基于 FastAPI 和 WeChat 的聊天机器人项目，支持 AI 对话和管理员模式。

## 终极目标：
创造一个拥有持久记忆的私人AI数字人
像和其他人聊天一样，在微信上即可随时随地开聊

当前的AI架构不够先进，AI根本没有记忆，有的只是上下文，离真正的数字人相去甚远。但是我相信AI能及时将记忆固化为模型参数的这一天，迟早会来...或者有其他解决方案？

加入开发者群聊，共同进步
885986098


# 效果展示
## 将微信一系列表情包：[表情名]写在系统提示词里
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

请确保您的 `requirements.txt` 文件包含以下依赖项：

```plaintext
fastapi
wechatpy
uvicorn
requests
beautifulsoup4
mem0
tavily
```

您可以使用以下命令安装依赖：

```sh
pip install -r 

requirements.txt


```

## 配置文件

请在 `chatmemollama/config.json` 中配置以下

内容

：

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

### 管理员命令

- `ps` - 列出正在运行的模型
- `verify_status` - 确认身份（重启后对用户0免鉴权）
- `list` - 列出已有模型
- `models` - 切换模型
- `pull` - 拉取模型
- `exit` - 退出管理员模式
- `help` - 查看管理员命令帮助

## 贡献

欢迎提交问题和贡献代码！请确保您的代码符合项目的编码规范。

# 更新计划

重新打造项目核心代码 
将允许使用非本地AI

将各部分
- 微信交互类 
- AI调用类
- 用户管理类
这主要的类分开写到不同文件

加强逻辑处理部分

将项目模块化以更好的支持新功能

动态拓展函数调用

优化微信服务器5秒超时逻辑处理

-项目文件夹ChatMemOllama

 - AIsystem.py
 - WechatConfig.py
 - UserInfo.py
 - Main.py
 - Guide.py

## 后续考虑制作GUI管理界面


## 早期开发阶段 任何部分都可能会变！


## 许可证

本项目使用 [Apache2.0 许可证](LICENSE)
