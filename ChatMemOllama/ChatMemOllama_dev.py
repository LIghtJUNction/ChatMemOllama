from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from wechatpy import parse_message, create_reply 
from wechatpy.utils import check_signature
from wechatpy.crypto import WeChatCrypto
from wechatpy.exceptions import InvalidSignatureException, InvalidAppIdException
# import logging 吐出来的日志太多了
import asyncio
import uvicorn
import ollama # 用于处理消息
import threading  # 用于多线程
import requests   
from bs4 import BeautifulSoup
import json
import time
import mem0 # 用于存储用户信息--少用 pip insatll mem0ai 本地部署需要安装qdrant作为向量存储库
import random # 用于生成随机数
import string # 用于生成随机字符串
from urllib.parse import urlparse # 用于解析url
import re # 用于正则匹配
import pickle # 用于保存对象
import os # 用于文件操作
import datetime # 用于处理日期和时间
import _thread # 用于多线程



class WechatConfig():
    def __init__(self):
        """
        初始化
        功能：
        1. 从配置文件 ./ChatMemOllama/config.json 读取配置并赋值给实例变量。
        2. 生成一个随机的 8 位字符串作为 su_key。
        3. 从用户对象文件夹 ./ChatMemOllama/Users 读取用户对象，并将其保存在字典 self.users 中。
        实例变量：
        - WECHAT_TOKEN: 从配置文件中读取的微信令牌。
        - APPID: 从配置文件中读取的应用 ID。
        - AESKey: 从配置文件中读取的编码 AES 密钥。
        - AdminID: 从配置文件中读取的管理员 ID。
        - mem0config: 从配置文件中读取的 mem0 配置。
        - su_key: 随机生成的 8 位字符串。
        - users: 存储用户对象的字典，键为用户 ID，值为用户对象。
        异常处理：
        - 如果用户对象文件夹不存在，提示用户创建文件夹。
        - 如果读取用户对象时发生其他错误，打印错误信息并提示可能是第一次运行没有用户对象。
        """
        # 从目录 ./ChatMemOllama/.config 读取配置并赋值
        with open("./ChatMemOllama/config.json", "r+") as f:
            config = json.load(f)
            self.WECHAT_TOKEN = config["WECHAT_TOKEN"]
            self.APPID = config["APPID"]
            self.AESKey = config["EncodingAESKey"] # AESKey 为EncodingAESKey 简化一下
            self.AdminID = config["AdminID"]
            self.mem0config = config["mem0config"]
            self.model = config["model"]
            self.verify_status = config["verify_status"]
            if self.verify_status == "False":
                self.su_key = ''.join(random.choices(string.ascii_letters + string.digits, k=8))
                # 保存 su_key 到配置文件
                config["su_key"] = self.su_key
            # 将指针移动到文件开头
            f.seek(0)
            # 将更新后的 config 写回文件
            json.dump(config, f, indent=4)
            # 截断文件以防止新内容比旧内容短时出现残留
            f.truncate()
        self.crypto = WeChatCrypto(self.WECHAT_TOKEN, self.AESKey, self.APPID)
        self.model = "llama3.1" # 默认模型
        self.system_prompt = "你是一个努力假扮人类的AI" # 系统提示词
        # 从目录 ./ChatMemOllama/Users 读取用户对象并保存在字典 self.users 中 TODO
        self.users = {}
        # 读取用户对象文件夹 遍历后按照 openid:obj 成对保存在字典中 空值不报错 TODO
        try:
            user_folder = "./ChatMemOllama/Users"
            for userid in os.listdir(user_folder):
                user_file_path = os.path.join(user_folder, userid)
                try:
                    if os.path.getsize(user_file_path) > 0:  # 检查文件是否为空
                        with open(user_file_path, "rb") as f:
                            self.users[userid] = pickle.load(f) # 加载用户对象
                    else:
                        print(f"文件 {user_file_path} 是空的，跳过加载。")
                except (EOFError, pickle.UnpicklingError):
                    print(f"无法加载文件 {user_file_path}，文件可能已损坏或为空。")
        except FileNotFoundError:
            print(f"文件夹 {user_folder} 不存在，请创建文件夹以保存用户对象。")
        
        self.AI_system = AIsystem(self.model ,self )

    def set_config(self, **kwargs):
        valid_keys = ["WECHAT_TOKEN", "APPID", "AESKey", "AdminID", "mem0config", "su_key", "model", "verify_status"]
        with open("./ChatMemOllama/config.json", "r") as f:
            config = json.load(f)
        
        for key, value in kwargs.items():
            if key in valid_keys:
                setattr(self, key, value)
                config[key] = value
        
        with open("./ChatMemOllama/config.json", "w") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

    def save_user(self, user):
        # with open(f"./Users/{user.openid}", "wb") as f:
        #     pickle.dump(user, f)
        print("保存用户对象 todo")

    def delete_user(self, openid):
        os.remove(f"./ChatMemOllama/Users/{openid}")

    async def check(self, request):  # 检查微信消息签名
        msg_info = await self.get_msg_info(request)
        try:
            check_signature(self.WECHAT_TOKEN, msg_info["signature"], msg_info["timestamp"], msg_info["nonce"])
        except InvalidSignatureException:
            print("无效的微信签名请求")
            raise HTTPException(status_code=403, detail="Invalid signature")
        return msg_info

    async def get_msg_info(self, request):
        msg_info = {
            'timestamp': request.query_params.get('timestamp'),
            'nonce': request.query_params.get('nonce'),
            'signature': request.query_params.get('signature'),
            'msg_signature': request.query_params.get("msg_signature", ""),
            "echo_str": request.query_params.get("echostr", ""),
            'openid': request.query_params.get("openid", ""),
            "body": await request.body()
        }
        return msg_info

    async def decode(self, msg_info):
        msg_xml = self.crypto.decrypt_message(msg_info['body'], msg_info["msg_signature"], msg_info["timestamp"], msg_info["nonce"])
        msg = parse_message(msg_xml)
        msg_info["msg"] = msg

        return msg_info # 添加解密并且解析后的msg
    
    async def encode(self,A,msg_info):
        reply = create_reply(A,msg_info["msg"])
        if reply is None:  
            raise ValueError("reply 对象未正确初始化或赋值为 None")  

        result = self.crypto.encrypt_message(reply.render(), msg_info["nonce"],msg_info["timestamp"]) # 加密数据包
        return result # 加密后的xml
    
    async def GET(self,request):  # 相当于收到GET请求执行的主函数
        msg_info = await self.check(request)
        return msg_info["echo_str"]

    async def POST(self,request):  # 相当于收到POST请求执行的主函数
        msg_info = await self.check(request)
        msg_info = await self.decode(msg_info)
        # 这里开始处理消息 用户提问是 msg_info["msg"].content ， 消息类型：msg_info["msg"].type 用户openid：msg_info["msg"].source 
        Q = msg_info["msg"].content

        if msg_info["msg"].type == "text":
            # 这里将问题Q传递给管道处理 看下面
            A = await self.pipe(Q,msg_info)
        else:
            A = "暂时不支持非文本消息"

        # 加密响应并回答
        result = await self.encode(A,msg_info)
        return result

    # 管道 接受Q 输出A
    """
    若 在4秒内没有回复，系统提前回复“正在处理中，请稍等” + 进度：x% 
    若 用户在4秒内急不可耐连着发，系统回复“已收到您的消息，正在处理中，请稍等” + 进度：x% "虽然不立马处理，但会将其保存至历史记录中" 
    若 用户发送"继续"，系统将准备好的对话直接发送给用户
    若 用户发送"继续"，但是上一条消息未准备就绪，系统将回复"上一条消息未准备就绪，请稍等" + 进度：x%
    若 用户发送"新对话"，系统将清空除了system之外的所有对话记录

    """ 
    async def pipe(self,Q,msg_info):
        openid = msg_info["msg"].source
        # 查看是否存在这个用户 如果不存在则创建
        if (openid not in self.users and len(self.users) >= 1 ):
            # 嗨嗨嗨
            self.users[openid] = user(openid,self.AI_system) # 欢迎新用户 & 初始化新用户
            self.save_user(self.users[openid]) # 保存用户对象
            A = await self.users[openid].pipe(Q,init = True ) # 初始化响应


        elif (openid not in self.users and len(self.users) == 0 ): # 用户0，享有root权限
            self.set_config(AdminID = openid) # 记录管理员id
            self.users[openid] = Admin(openid,self.AI_system,self) # 初始化管理员
            self.save_user(self.users[openid])
            A = await self.users[openid].pipe(Q,init = True , IsAdmin = True) # 初始化响应

        elif openid in self.users: # 第一层 关键词回复
            if Q == self.su_key :
                self.users[openid].sudo = "True"

                A = "管理员,你好!🤗     |\n *已进入管理员菜单🤖 \n *请输入 help 查看帮助😶‍🌫️"
            elif Q == "sudo su":
                if openid == self.AdminID:
                    self.users[openid].sudo = "True"
                    A = "管理员,你好!🤗     |\n *已进入管理员菜单🤖 \n *请输入 help 查看帮助😶‍🌫️"
                else:
                    A = "你没有权限进入管理员模式/（请检查你是否为用户零）"
            elif self.users[openid].sudo == "True":
                A = self.users[openid].AdminMenu(Q)
            else:
                A = await self.users[openid].pipe(Q) # 传到用户处理

        return A

# AIsystem可以访问Wecahtconfig
class AIsystem:
    def __init__(self, model, wechat_config):
        self.model = model
        self.wechat_config = wechat_config
        self.ollama_async_client = ollama.AsyncClient()
        self.mem0 = mem0.Memory.from_config(wechat_config.mem0config)


        self.active_chats = {} # 存储对话状态
    async def init(self,openid):
        Q = f"介绍一下你自己 尽量简短"
        self.active_chats[openid] = {"done": False, "progress": 0 , "Q": Q , "responsed_content": "" , "A" : "" , "messages": [] , "tmp": ""}
        self.active_chats[openid]["messages"].append({"role": "system", "content": self.wechat_config.system_prompt})
        self.active_chats[openid]["messages"].append({"role": "user", "content": Q})
        response = await self.ollama_async_client.chat(model=self.model,messages=self.active_chats[openid]["messages"],stream=False) 
        self.active_chats[openid]["A"] = response["message"]["content"]
        self.active_chats[openid]["done"] = True

    async def stream_respond(self, openid, Q):
        if openid not in self.active_chats:
            self.init(openid)# 初始化对话状态

        else:
            self.active_chats[openid]["done"] = False
            self.active_chats[openid] = {"ID":openid, "done": False, "progress": 0 , "Q": Q , "responsed_content": "" , "A" : "" , "messages": []}
            self.active_chats[openid]["messages"].append({"role": "system", "content": self.wechat_config.system_prompt})
            self.active_chats[openid]["messages"].append({"role": "user", "content": Q})
            async for response in await self.ollama_async_client.chat(model=self.model,messages=self.active_chats[openid]["messages"],stream=True):
                self.active_chats[openid]["responsed_content"] += response["message"]["content"]
                self.active_chats[openid]["A"] += response["message"]["content"]
                self.active_chats[openid]["progress"] += 10

                if response["done"]:
                    self.active_chats[openid]["done"] = True
                    self.active_chats[openid]["progress"] = 100
                    self.active_chats[openid]["messages"].append({"role": "assistant", "content": self.active_chats[openid]["A"]})
                    break

    async def AI_call(self, openid, Q):

        """
        监控 active_chats[openid]["done"] 状态 4 秒，如果状态在 4 秒内变为 True，
        则执行 stream_respond，否则直接返回。

        :param openid: 用户的 openid
        :param Q: 待处理的内容
        :param active_chats: 包含聊天状态的字典
        :param stream_respond: 异步流式响应函数
        :return: 返回聊天的响应内容或超时提示
        """
        if openid not in self.active_chats:
            await self.init(openid)
            self.active_chats[openid]["tmp"] = self.active_chats[openid]["A"]
            self.active_chats[openid]["A"] = ""
            return self.active_chats[openid]["tmp"] + "回答完毕1"
        
        asyncio.create_task(self.stream_respond(openid, Q))

        # 将用户的 openid 和 提问先提交 给 stream_respond

        try:
            # 监控 4 秒内的状态变化
            await asyncio.wait_for(self.cheak_status(openid), timeout=4.0)
        except asyncio.TimeoutError:
            # 如果超时（4 秒内状态未变为 True），直接返回提示
            self.active_chats[openid]["tmp"] = self.active_chats[openid]["responsed_content"]
            self.active_chats[openid]["responsed_content"] = "" # 清空响应内容
            return f"{self.active_chats[openid]["tmp"]}... \n  进度：{self.active_chats[openid]['progress']}%"

        # 如果 4 秒内状态变为 True，执行 stream_respond 并返回响应内容
        self.active_chats[openid]["tmp"] = self.active_chats[openid]["A"]
        self.active_chats[openid]["A"] = ""
        
        return self.active_chats[openid]["tmp"] + "回答完毕2"
        

    async def cheak_status(self,openid):
        while self.active_chats[openid]["done"] == False:
            await asyncio.sleep(0.2)

# user实例 无法调用wechatconfig ，可以调用AIsystem
# admin可以调用 wechatconfig
class user():
    def __init__(self, openid , AI_system : AIsystem ):
        self.openid = openid
        self.name = ""
        self.gender = None  # 性别属性 未设置
        self.age = None # 年龄属性 未设置
        self.cache = ""  # 缓存
        self.AI_system = AI_system

    def get_user_info():
        pass    

    def set_user_info():
        pass

    async def pipe(self,Q,init = False , IsAdmin = False): # 管道 第二层
        if init and not IsAdmin: 
            A = "欢迎！ 🤗 你可以直接用自然语言问我提出你的要求，你还可以查看 我的历史文章：README.MD"
        elif init and IsAdmin :
            A = "管理员你好！🤗 \n 已保存至config.json! \n 关于如何进入管理员模式，请查看config.json - 'su_key' 的值 ！并输入key进行鉴权！"
        else: # 非首次使用，正常逻辑
            print(f"用户 ： {Q} ")
            A = await self.AI_system.AI_call(self.openid,Q)
        return A
    


class Admin(user):
    def __init__(self, openid , model, wechat_config :WechatConfig ):
        super().__init__(openid,model)  # 继承user类
        self.wechat_config = wechat_config
        self.sudo = "False" # 正常模式
    def AdminMenu(self,Q):
        if self.sudo == "True":
            if Q == "ps":
                return "todo"
            elif Q == "verify_status":
                if self.wechat_config.verify_status == "False":
                    self.wechat_config.verify_status = "True"
                    self.wechat_config.set_config(verify_status = "True")
                    return "身份验证成功，开启自动登录"
                else:
                    return "身份验证已开启，无需重复验证"
            elif Q == "list":
                return "todo"
            elif Q == "models":
                return "todo"
            elif Q == "pull":
                return "todo"
            elif Q == "exit":
                self.sudo = "False"
                return "todo"
            elif Q == "help":
                return "verify --确认身份(重启后对用户0免鉴权) \n ps --列出正在运行的模型 \n list  --列出已有模型  \n models --切换模型 \n pull -- 拉取模型 \n exit -- 退出管理员模式(输入sudo su再次进入)"
        else:
            return "你没有权限访问管理员菜单"
    def AdminTools(self):
        pass
    
    

if __name__ == "__main__":

    MyWechatConfig = WechatConfig() # 从config.json读取配置并设置第一个使用本系统的user为用户0，即管理员
    # 参考格式如下
    # POST /wechat?signature=待定&timestamp=待定&nonce=待定&openid=待定&encrypt_type=aes&msg_signature=待定 HTTP/1.1
    ChatMemOllama = FastAPI()
    @ChatMemOllama.get("/wechat")
    async def wechat_get(request: Request):
        result = await MyWechatConfig.GET()  # z这是必须的步骤，以为直接调用异步函数返回的是一个协程对象 必须用await调用 或者 async.run()
        return PlainTextResponse(content=result)

    @ChatMemOllama.post("/wechat")
    async def wechat_post(request: Request):
        result = await MyWechatConfig.POST(request)
        return PlainTextResponse(content=result)
    
    uvicorn.run(ChatMemOllama, host="0.0.0.0", port=8000)






