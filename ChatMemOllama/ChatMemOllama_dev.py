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
        with open("./config.json", "r+") as f:
            config = json.load(f)
            self.WECHAT_TOKEN = config["WECHAT_TOKEN"]
            self.APPID = config["APPID"]
            self.AESKey = config["EncodingAESKey"] # AESKey 为EncodingAESKey 简化一下
            self.AdminID = config["AdminID"]
            self.mem0config = config["mem0config"]
            self.model = config["model"]
            self.su_key = ''.join(random.choices(string.ascii_letters + string.digits, k=8))

        self.users = {}
        # 读取用户对象文件夹 遍历后按照 openid:obj 成对保存在字典中 空值不报错
        try:
            user_folder = "./Users"
            for userid in os.listdir(user_folder):
                with open(f"./User/{userid}", "rb") as f:
                    self.users[userid] = pickle.load(f) # 加载用户对象
        except FileNotFoundError:
            print(f"文件夹 {user_folder} 不存在,请创建文件夹以保存用户对象。")
        except Exception as e:
            print(f"读取用户对象时发生错误: {e} 也许是第一次运行还没有用户(非管理)对象，忽略即可。")
        
        self.AI_system = AIsystem(self.model ,self )


    def set_config(self, **kwargs):
        valid_keys = ["WECHAT_TOKEN", "APPID", "AESKey", "AdminID"]
        with open("./config.json", "r") as f:
            config = json.load(f)
        
        for key, value in kwargs.items():
            if key in valid_keys:
                setattr(self, key, value)
                config[key] = value
        
        with open("./config.json", "w") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

    async def check_signature(self, request):  # 检查微信消息签名
        try:
            check_signature(self.WECHAT_TOKEN, request.query_params["signature"], request.query_params["timestamp"], request.query_params["nonce"])
        except InvalidSignatureException:
            return "无效的签名"
        except InvalidAppIdException:
            return "无效的AppID"
        return "成功"

    def get_crypto(self):

        self.crypto = WeChatCrypto(self.WECHAT_TOKEN, self.AESKey, self.APPID)
        return self.crypto

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
        self.get_crypto()

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
        print(await self.check_signature(request))
        msg_info = await self.get_msg_info(request)
        return msg_info["echo_str"]

    async def POST(self,request):  # 相当于收到POST请求执行的主函数
        print(await self.check_signature(request))
        msg_info = await self.get_msg_info(request)
        msg_info = await self.decode(msg_info) # 解密并解析消息
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
            A = await self.users[openid].pipe(Q,init = True ) # 初始化响应


        elif (openid not in self.users and len(self.users) == 0 ): # 用户0，享有root权限
            self.set_config(AdminID = openid) # 记录管理员id
            self.users[openid] = Admin(openid,self.AI_system,self) # 初始化管理员
            A = await self.users[openid].pipe(Q,init = True , IsAdmin = True) # 初始化响应

        elif openid in self.users:
            # 在AI_system内设置超时为4秒
            A = await self.AI_system.AI_call_stream(openid,Q)



        # 调度消息
        # 检查是否有未处理消息
        
        return A

# AIsystem可以访问Wecahtconfig
class AIsystem():
    def __init__(self,model,wechat_config : WechatConfig): 
        self.model = model
        self.wechat_config = wechat_config
        self.ollama_client = ollama.Client()
        self.ollama_async_client = ollama.AsyncClient()
        self.mem0 = mem0.Memory.from_config(wechat_config.mem0config)
        self.task = {}



    def AI_kernel(self):
        
        pass

    async def AI_call_stream(self,openid , Q):
        # 开始计时4秒 流式生成回复
        start_time = time.time()

        async for response in self.ollama_async_client(model="llama3.1:latest", messages=self.wechat_config.users[openid].messages, stream=True):
            response_time = datetime.fromisoformat(response['created_at'].replace("Z", "+00:00")).timestamp()

            


    def AI_tools(self):
        pass



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
        self.system_prompt = "你是一个幽默的AI"
        self.messages = [{
            "role": "system", 
            "content": self.system_prompt
        }
        ]

    def get_user_info():
        pass    

    def set_user_info():
        pass

    async def pipe(self,Q,init = False , IsAdmin = False):
        if init and not IsAdmin: 
            A = "欢迎！ 🤗 你可以直接用自然语言问我提出你的要求，你还可以查看 我的历史文章：README.MD"
        elif init and IsAdmin :
            A = "管理员你好！已保存至config.json，关于如何进入管理员模式，请查看config.json - 'su_key' 的值 ！并输入key进行鉴权！"
        else: # 非首次使用，正常逻辑
            print(f"用户 ： {Q} ")
            A = await self.AI_system.AI_call(Q)
        return A
    

class Admin(user):
    def __init__(self, openid , model, wechat_config :WechatConfig ):
        super().__init__(openid,model)  # 继承user类
        self.wechat_config = wechat_config

    def AdminMenu(self):
        pass

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






