from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from wechatpy import parse_message, create_reply
from wechatpy.utils import check_signature
from wechatpy.crypto import WeChatCrypto
from wechatpy.exceptions import InvalidSignatureException, InvalidAppIdException
import asyncio
import uvicorn
import ollama
import threading
import requests
from bs4 import BeautifulSoup
import json
import time
import mem0
import random
import string
from urllib.parse import urlparse
import re
import pickle
import os
import datetime
import _thread
from tavily import TavilyClient
from typing import List, Dict, Any


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
            self.Tavilykey = config["Tavilykey"]
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

                A = "管理员,你好!🤗 -- 鉴权通过!  \n *已进入管理员菜单🤖 \n *请输入 help 查看帮助😶‍🌫️"
            elif Q == "sudo su":
                if openid == self.AdminID:
                    self.users[openid].sudo = "True"
                    A = "管理员,你好!🤗   \n *已进入管理员菜单🤖 \n *请输入 help 查看帮助😶‍🌫️"
                else:
                    A = "你没有权限进入管理员模式/（请检查你是否为用户零）"
            elif self.users[openid].sudo == "True":
                A = self.users[openid].AdminMenu(Q) # 管理员控制菜单模式
            else:
                A = await self.users[openid].pipe(Q) # 管理员AI对话模式

        return A

class AIsystem:
    def __init__(self, model, wechat_config):
        self.model = model
        self.wechat_config = wechat_config
        self.ollama_async_client = ollama.AsyncClient()
        self.mem0 = mem0.Memory.from_config(wechat_config.mem0config)
        self.system_prompt = "  你的身份: 智能助手 /n 你的能力 : 在线搜索 以及 获取当前时间 /n 你的说话方式: 带有微信表情符号 例如: [骷髅][捂脸][破涕为笑][憨笑][微笑][色][便便][旺柴][得意][发呆][流泪][微笑][害羞][色][闭嘴][睡][大哭][尴尬][调皮][呲牙][呲牙][惊讶][难过][抓狂][囧][吐][偷笑][愉快][白眼][傲慢][困][惊恐][憨笑][悠闲][咒骂][疑问][嘘][晕][衰][敲打][再见][抠鼻][擦汗][鼓掌][坏笑][右哼哼][鄙视][委屈][快哭了][亲亲][可怜][笑脸][嘿哈][无语][奸笑][生病][加油][机智][打脸][社会社会][好的][爱心][嘴唇][心碎][拥抱][强][合十][拳头][勾引][菜刀][凋谢][咖啡][炸弹][蛋糕][便便][月亮][太阳][庆祝][红包][發][福][烟花][爆竹][猪头][转圈][发抖][发抖] 例如: 你好[微笑] /n 你的对话环境:微信公众号 " # 默认系统提示词
        self.active_chats = {} # 存储对话状态


        # AI工具相关
        self.search_client = TavilyClient(api_key=self.wechat_config.Tavilykey) # 免费额度是1000次/月
        self.tools = [
            {
            "type": "function",
            "function": {
                "name": "search_online",
                "description": "在线搜索，请先翻译为英文再搜索",
                "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "The search query"},
                },
                "required": ["query"],
                },
            },
            },
            ##################################################
            {
            "type": "function",
            "function": {
                "name": "get_time",
                "description": "这是默认调用工具,获取当前时间",
                "parameters": {
                "type": "object",
                "properties": {},
                "required": [],
                },
            },
            }
        ]
        
    async def init(self,openid,Q):
        """
        初始化AI 对话 -- 引导用户并设置用户的属性
        """
        self.active_chats[openid] = {
            "A": "",
            "responsed_content": "",
            "done": "False",
            "tmp": ""
        }
        self.wechat_config.users[openid].init_messages()
        self.active_chats[openid]["done"] = "True"
        return "欢迎！ 我需要先了解一下你 \n 你的名字是什么？(我应该如何称呼你?) \n 你的年龄呢？(我应该知道你的年龄吗?) \n 你的性别呢？(我应该知道你的性别吗?) \n 你也可以不回答这些问题，直接问我你的问题。 \n 你可以随时输入 exit 退出AI对话。(输入AI重新开启) \n 输入help 或者-h 查看帮助"
    
    
    async def AI_call(self, openid, Q):
        """
        AI调用函数，返回AI的回复。
        """
        print(f"AI_call invoked with openid: {openid}, Q: {Q}")
        
        if openid not in self.active_chats:
            print(f"Initializing chat for openid: {openid}")
            return await self.init(openid, Q)
        else:
            chat_status = self.active_chats[openid]
            print(f"Chat status for openid {openid}: {chat_status}")
            
            if chat_status["done"] == "False" or (chat_status["done"] == "True" and chat_status["responsed_content"]):
                print(f"Returning temporary response for openid: {openid}")
                return self._tmp_(openid, "responsed_content")
            elif chat_status["done"] == "True" and not chat_status["responsed_content"]:
                print(f"Saving user message for openid: {openid}, Q: {Q}")
                self.wechat_config.users[openid].save_message("user", Q)
                
                if "-s" in Q or "-S" in Q:
                    print(f"Tool search requested for openid: {openid}")
                    tools = [self.tools[0]]
                    tool_calls = await self._tool_calling(openid, tools)
                    print(f"Tool calls for openid {openid}: {tool_calls}")
                    
                    if tool_calls:
                        results = await self._format_results(openid, await self._execute_tool_calls(openid, tool_calls))
                        print(f"Tool results for openid {openid}: {results}")
                        self.wechat_config.users[openid].save_message("tool", await self._format_results(openid, await self._execute_tool_calls(openid, tool_calls)))
                        await self._stream_respond(openid, Q)
                        return self._tmp_(openid, "responsed_content")
                    else:
                        print(f"Returning temporary response A for openid: {openid}")
                        return self._tmp_(openid, "A")
                else:
                    print(f"不使用在线搜索功能,用户: {openid}")
                    tools = [self.tools[1]]
                    tool_calls = await self._tool_calling(openid, tools)
                    print(f"Tool calls for openid {openid}: {tool_calls}")
                    
                    if tool_calls:
                        results = await self._format_results(openid, await self._execute_tool_calls(openid, tool_calls))
                        print(f"Tool results for openid {openid}: {results}")
                        self.wechat_config.users[openid].save_message("tool", await self._format_results(openid, await self._execute_tool_calls(openid, tool_calls)))
                        await self._stream_respond(openid, Q)
                        return self._tmp_(openid, "responsed_content")
                    else:
                        print(f"Returning temporary response A for openid: {openid}")
                        return self._tmp_(openid, "A")
            else:
                return "好好检查下代码吧! "                   

            

    # 以下是AI工具相关的函数

    def _tmp_(self,openid , _ ):
        self.active_chats[openid]["tmp"] = self.active_chats[openid][_]
        self.active_chats[openid][_] = ""
        return self.active_chats[openid]["tmp"]


    async def _tool_calling(self,openid,tools):
        """
        调用工具函数，返回工具函数的结果。
        """
        self.active_chats[openid]["done"] == "False"
        if openid not in self.active_chats:
            return "未找到对话状态"
        response = await self.ollama_async_client.chat(
            model=self.model,
            messages=self.wechat_config.users[openid].messages,
            tools=tools
        )
        print("应该调用的工具?完整响应：",response)

        tool_calls = response['message'].get('tool_calls')
        if tool_calls:
            self.active_chats[openid]["done"] = "True"
            return tool_calls
        else:
            print("不调用")
            self.active_chats[openid]["A"] = response['message']['content']
            self.active_chats[openid]["done"] = "True"
            return "" # 供判断使用

    async def _stream_respond(self,openid,Q):
        """
        异步流式响应函数，用于处理用户的提问并返回响应内容。
        处理流程： 用户提问 -> 保存用户提问 -> 调用AI选择工具并提取参数 -> 执行工具 并将结果添加至messages ->  调用 ollama 生成回复 -> 保存回复 -> 返回回复
        """

        self.active_chats[openid]["done"] = "False"
        async for response in await self.ollama_async_client.chat(model=self.model,messages=self.wechat_config.users[openid].messages,stream=True):
            self.active_chats[openid]["responsed_content"] += response["message"]["content"]
            self.active_chats[openid]["A"] += response["message"]["content"]
            print(response["message"]["content"], end='', flush=True)
        self.active_chats[openid]["done"] = "True"

    # 可以使用@staticmethod装饰器将方法标记为静态方法，静态方法不会接收隐式的第一个参数 self
    async def _search_online(self,openid, query) -> str:  # 在线搜索AI-工具 统一使用下标_开头 好区分  #耗时
        # 判断query是否达到了5个字符
        if len(query) < 5:
            query = "latest " + query
        try:
            print("ai使用了本函数搜索：", query)
            search_results = self.search_client.search(query,max_results=1)
            print(f"搜索结果：{search_results}" )
            return json.dumps(search_results["results"])
        except Exception as e:
            return f"搜索失败，错误原因: {str(e)} -- 可能是免费搜索次数用完了/搜索字数不够"

    # 默认调用工具    
    async def _get_time(self,openid) -> str: # 获取时间 默认工具 不耗时  
        print("AI使用了本函数获取时间---用户ID：",openid)
        result = {
            "timestamp": datetime.datetime.now().isoformat()
        }
        return json.dumps(result, ensure_ascii=False, indent=4)
        
    async def _execute_tool_calls(self,openid, tool_calls: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        results = []
        for tool in tool_calls:
            func_name = "_" + tool['function']['name'] # 为了和一般函数区分，加上下划线
            args = tool['function'].get('arguments', {}) # 获取参数 
            args['openid'] = openid  # 额外添加一个openid的参数

            function_to_call = getattr(self, func_name, None)
            if function_to_call is None:
                print(f"未找到函数：{func_name}")
                continue
            try:
                print(f"调用 {func_name} 参数：{args}")
                result = await function_to_call(**args) 
   
                results.append({"function": tool['function']['name'], "result": result})
            except Exception as e:
                print(f"调用 {func_name} 出错，参数：{args}，错误：{e}")
                results.append({"function": tool['function']['name'], "result": {"error": str(e)}})
        return results

    async def _format_results(self, openid, results: List[Dict[str, Any]]) -> str:
        formatted_results = []
        for result in results:
            if isinstance(result['result'], dict) and 'error' in result['result']:
                formatted_results.append(f"错误: {result['result']['error']}")
            else:
                formatted_results.append(f"结果: {result['result']}")
        return "\n".join(formatted_results)

class user():
    def __init__(self, openid , AI_system : AIsystem ):
        self.openid = openid
        self.name = ""
        self.gender = None  # 性别属性 未设置
        self.age = None # 年龄属性 未设置
        self.cache = ""  # 缓存
        self.AI_system = AI_system
        self.K = 20 # 用于控制消息记录长度
        self.messages = [] # 消息上下文记录
        self.system_prompt = self.AI_system.system_prompt # 默认系统提示词
        self.menu = False # 菜单状态

    def get_user_info(self):
        pass    

    def set_user_info(self):
        pass

    def init_messages(self):
        self.save_message("system",self.system_prompt)
        return self.messages

    
    def save_message(self,role,content):
        if len(self.messages) >= self.K:
            self.messages.append({"role": role, "content": content})
            self.messages.pop(1) # 删除最早的一般消息
        else:
            self.messages.append({"role": role, "content": content})


    async def pipe(self,Q,init = False , IsAdmin = False): # 管道 第二层
        if init and not IsAdmin: 
            A = "欢迎！ 🤗 你可以直接用自然语言问我提出你的要求，你还可以查看 我的历史文章：README.MD"
        elif init and IsAdmin :
            A = "管理员你好！🤗 \n 已保存至config.json! \n 关于如何进入管理员模式，请查看config.json - 'su_key' 的值 ！并输入key进行鉴权！"

        elif Q == "exit":
            self.menu = True
            A = "退出AI对话"


        else: # 非首次使用，正常逻辑
            print(f"用户 ： {Q} ")
            A = await self.AI_system.AI_call(self.openid,Q)
        return A
    
    def menu(self,Q):
        if Q == "help" or Q == "-h":
            return "help -- 查看帮助 \n sudo su -- 进入管理员模式(仅限管理员) \n AI -- 重新开启AI对话 \n exit -- 退出AI对话"
        elif Q == "AI":
            self.menu = False
            return "AI对话已重新开启"
        elif Q == "sudo su":
            return "你没有权限进入管理员模式"
        elif Q == "1":
            return "todo"
        elif Q == "2":
            return "todo"
        elif Q == "3":
            return "todo"    
class Admin(user):
    def __init__(self, openid ,AI_system, wechat_config :WechatConfig ):
        super().__init__(openid,AI_system)  # 继承user类
        self.wechat_config = wechat_config
        self.K = 30 # 用于控制消息记录长度
        self.sudo = "False" # 正常模式 True 为管理员菜单模式
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
    # 检测qdrant服务是否在端口6333开启
    try:
        response = requests.get("http://localhost:6333")
        if response.status_code == 200:
            print("Qdrant 服务正在运行")
        else:
            print("Qdrant 服务未在端口 6333 运行! \n qdrant是mem0需要使用的向量数据库 \n 请到https://github.com/LIghtJUNction/ChatMemOllama 查看教程 ")
    except requests.ConnectionError:
       raise HTTPException(status_code=500, detail="无法连接到 Qdrant 服务")

    # 检测ollama是否在端口11434(默认)运行
    try:
        response = requests.get("http://localhost:11434")
        if response.status_code == 200:
            print("Ollama 服务正在运行 🤖 ")
        else:
            print("Ollama 服务未在端口 11434(默认端口) 运行! ")
    except requests.ConnectionError:
        
        raise HTTPException(status_code=500, detail="无法连接到 Ollama 服务")
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






