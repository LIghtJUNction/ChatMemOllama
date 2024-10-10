from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from wechatpy import parse_message, create_reply 
from wechatpy.utils import check_signature
from wechatpy.crypto import WeChatCrypto
from wechatpy.exceptions import InvalidSignatureException, InvalidAppIdException
# import logging 吐出来的日志太多了
import uvicorn
import ollama # 用于处理消息
import threading  # 用于多线程
import requests   
from bs4 import BeautifulSoup
import json
import time
import mem0 # 用于存储用户信息--少用 pip insatll mem0ai 本地部署需要安装qdrant作为向量存储库
import random # 用于生成随机数
from urllib.parse import urlparse # 用于解析url
import re # 用于正则匹配
import pickle # 用于保存对象
import os # 用于文件操作



class WechatConfig():
    def __init__(self):
        # 从目录 ./ChatMemOllama/.config 读取配置并赋值
        with open("./ChatMemOllama/config.json","r") as f:
            config = json.load(f)
            self.WECHAT_TOKEN = config["WECHAT_TOKEN"]
            self.APPID = config["APPID"]
            self.AESKey = config["EncodingAESKey"] # AESKey 为EncodingAESKey 简化一下
            self.AdminID = config["AdminID"]

        self.users = {}
        # 读取用户对象文件夹 遍历后按照 openid:obj 成对保存在字典中 空值不报错
        try:
            user_folder = "./ChatMemOllama/Users"
            for userid in os.listdir(user_folder):
                with open(f"./ChatMemOllama/User/{userid}", "rb") as f:
                    self.users[userid] = pickle.load(f)
        except FileNotFoundError:
            print(f"文件夹 {user_folder} 不存在,请创建文件夹以保存用户对象。")
        except Exception as e:
            print(f"读取用户对象时发生错误: {e} 也许是第一次运行还没有用户(非管理)对象，忽略即可。")

            
    def set_config(self, **kwargs):
        valid_keys = ["WECHAT_TOKEN", "APPID", "AESKey", "AdminID"]
        with open("./ChatMemOllama/config.json", "r") as f:
            config = json.load(f)
        
        for key, value in kwargs.items():
            if key in valid_keys:
                setattr(self, key, value)
                config[key] = value
        
        with open("./ChatMemOllama/config.json", "w") as f:
            json.dump(config, f, ensure_ascii=False, indent=4)

    def check_signature(self, request):
        try:
            check_signature(self.WECHAT_TOKEN, request.query_params["signature"], request.query_params["timestamp"], request.query_params["nonce"])
        except InvalidSignatureException:
            return "无效的签名"
        except InvalidAppIdException:
            return "无效的AppID"
        return "成功"

    def get_crypto(self,openid):
        if openid != self.AdminID:
            return "您没有权限获取加密对象"
        else:     
            if (self.WECHAT_TOKEN == "" or self.APPID == "" or self.AESKey == ""):
                return "请先设置WECHAT_TOKEN,APPID,AESKey" # todo
            else:
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
        print(self.check_signature(request))
        msg_info = self.get_msg_info(request)
        return msg_info["echo_str"]


    async def POST(self,request):  # 相当于收到POST请求执行的主函数
        print(self.check_signature(request))
        msg_info = self.get_msg_info(request)
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
        if (openid not in self.users & len(self.users) >= 1 ):
            # 欢迎新用户
            self.users[openid] = user(openid,msg_info)
            self.users[openid].pipe(Q,init = True)


        elif (openid not in self.users & len(self.users) == 0 ):
            self.set_config(AdminID = openid)
            # 未完待续



            
            
           
        # 调度消息
        # 检查是否有未处理消息
        
        return A

class Admin():
    def __init__(self,openid,):
        self.AdminID = openid

    def AdminMenu():
        pass

    def pipe(Q):
  
        A = "尊敬的用户0，您好！🎉 您已被授予管理员权限，享受更多功能吧！🚀  --- 已进入管理员菜单模式   **1."



class user():
    def __init__(self, openid):
        self.openid = openid
        self.nickname = ""
    def AI_chat():
        pass
            
    
    def get_user_info():
        pass    

    def set_user_info():
        pass

    def pipe(Q):

        return A

    



class AIsystem():
    def __init__(self,Admin = Admin()):
        self.__module__ = "AIsystem"
        self.Admin = Admin()

    def AI_kernel():
        pass
    
    def AI_call():
        pass

    def AI_tools():
        pass




if __name__ == "__main__":
    config = {
         "vector_store": {
             "provider": "qdrant",
             "config": {
                 "collection_name": "test",
                 "host": "localhost",
                 "port": 6333,
                 "embedding_model_dims": 768,  # Change this according to your local model's dimensions
             },
         },
     
    # 比较新的 基于图的存储库
        # "graph_store": {
        #     "provider": "neo4j",
        #     "config": {
        #         "url": "neo4j+s://localhost:7687",
        #         "username": "neo4j",
        #         "password": ""
        #     },
        #     # "custom_prompt": "Please only extract entities containing sports related relationships and nothing else.", 
        # },

        "llm": {
            "provider": "ollama",
            "config": {
                "model": "llama3.1:latest",
                "temperature": 0,
                "max_tokens": 8000,
                "ollama_base_url": "http://localhost:11434",  # Ensure this URL is correct
            },
        },
        "embedder": {
            "provider": "ollama",
            "config": {
                "model": "nomic-embed-text:latest",
                # Alternatively, you can use "snowflake-arctic-embed:latest"
                "ollama_base_url": "http://localhost:11434",
            },
        },   
    # 和向量存储库一起使用

        "version": "v1.1",
                    }
    
    lightjunction = Admin()
    # 参考格式如下
    # POST /wechat?signature=待定&timestamp=待定&nonce=待定&openid=待定&encrypt_type=aes&msg_signature=待定 HTTP/1.1
    ChatMemOllama = FastAPI()
    @ChatMemOllama.get("/wechat")
    async def wechat_get(request: Request):
        result = await lightjunction.get(request)  # z这是必须的步骤，以为直接调用异步函数返回的是一个协程对象 必须用await调用 或者 async.run()
        return PlainTextResponse(content=result)

    @ChatMemOllama.post("/wechat")
    async def wechat_post(request: Request):
        result = await lightjunction.post(request)
        return PlainTextResponse(content=result)
    
    uvicorn.run(ChatMemOllama, host="0.0.0.0", port=8000)






