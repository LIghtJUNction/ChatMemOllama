from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import PlainTextResponse
from wechatpy import parse_message, create_reply 
from wechatpy.utils import check_signature
from wechatpy.crypto import WeChatCrypto
from wechatpy.exceptions import InvalidSignatureException, InvalidAppIdException
import logging
import uvicorn
import ollama
import threading 
 
import time  
import mem0

# 配置文件 
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

# 比较新的
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

# 设置日志记录器
logging.basicConfig(level=logging.DEBUG, format='\033[94m%(levelname)s: \033[93m%(message)s\033[91m') 

logger = logging.getLogger(__name__)


class andim(): # 管理数据加密解密
    def __init__(self,WECHAT_TOKEN,APPID,EncodingAESKey,mem,ollama):
        self.WECHAT_TOKEN = WECHAT_TOKEN
        self.APPID = APPID
        self.EncodingAESKey = EncodingAESKey
        self.mem = mem          # 管理记忆
        self.ollama = ollama     # 本地ai模型
        self.crypto = WeChatCrypto(self.WECHAT_TOKEN, self.EncodingAESKey, self.APPID) # 加密解密
        self.memory = {}
        self.A = "初始消息"
        self.messages = [{
            "role": "system", 
            "content": '你是微信公众号#############的AI助手，你可以和我聊天。负责解答用户关于这个公众号的疑惑。你的管理员叫##########。openid:#管理员的openid#'
        }]
    async def get_msg_info(self,request: Request): # 获取请求参数 并检查
        msg_info={
            'timestamp': request.query_params.get('timestamp'),
            'nonce': request.query_params.get('nonce'),
            'signature': request.query_params.get('signature'),
            'msg_signature': request.query_params.get("msg_signature", ""),
            "echo_str" : request.query_params.get("echostr", ""),
            'openid': request.query_params.get("openid", ""),
            "body" : await request.body(),
            }# 'msg':msg
        
        try:
            check_signature(self.WECHAT_TOKEN, msg_info["signature"], msg_info["timestamp"], msg_info["nonce"])
        except InvalidSignatureException:
            print("无效的微信签名请求")
            raise HTTPException(status_code=403, detail="Invalid signature")
        return msg_info


    async def decode(self,msg_info):#解密函数 同
        msg_xml = self.crypto.decrypt_message(msg_info['body'], msg_info["msg_signature"], msg_info["timestamp"], msg_info["nonce"])
        msg = parse_message(msg_xml)
        msg_info["msg"] = msg
        return msg_info # 添加解密解析后的msg
    
    async def encode(self,A,msg_info):#加密函数  返回加密数据包 需要msg
        reply = create_reply(A,msg_info["msg"])
        result = self.crypto.encrypt_message(reply.render(), msg_info["nonce"],msg_info["timestamp"]) # 加密数据包
        return result # 加密后的xml
    

    async def get(self,request: Request):
        msg_info = await self.get_msg_info(request)
        result =msg_info["echo_str"]
        return result


    async def post(self,request: Request,AdminNotice = None): # post请求，解密消息并加密回复 > 从参数中提取msg_info并保存 > 按照openid建立用户对象字典和消息字典 admin对象只允许有一个 admin管理其他用户
        msg_info = await self.get_msg_info(request)
        if AdminNotice is None:
            msg_info = await self.decode(msg_info)
            # 
            if msg_info["msg"].type == "text": # 以下是关键词回复
                if msg_info["msg"].content == "继续":
                    A = self.A
                elif msg_info["msg"].content == "测试":
                    A = "发送消息测试成功！"
                else:
                    CHAT = threading.Thread(target=lambda: self.chat_whth_ollama(msg_info)) 
                    CHAT.start()
                    A = "请稍后发送继续获取结果"

            else:
                A = "不支持的消息类型"

            #
            result = await self.encode(A,msg_info)

        else:
            result = self.Admin_notice(AdminNotice,msg_info)

        return result

    async def Admin_notice(self,AdminNotice,msg_info):
        msg_info = await self.decode(msg_info)
        result = await self.encode(AdminNotice,msg_info)
        return result


    def chat_whth_ollama(self,msg_info):
        Q = msg_info["msg"].content
        openid = msg_info["openid"]
        m = self.mem

        addQ = threading.Thread(target=lambda: m.add(f"用户_{msg_info['openid']}:{Q}",user_id=openid))
        get_memory = threading.Thread(target=lambda: self.get_memory(msg_info))

        addQ.start()
        get_memory.start()

        addQ.join()
        get_memory.join()

        Q_memory,privious_memory = self.memory[openid]
        massages = self.messages
        message = {
            "role": "user",
            "content": f"用户提问：{Q}。 关于问题{Q}的提问&回答记忆：{Q_memory}。前面所有的提问&回答记忆：{privious_memory} 当前用户openid:{msg_info['openid']}",
        }
        massages.append(message)


        response =self.ollama.chat(model="llama3.1:latest",messages=massages,stream=False)
        A = response["message"]["content"]

        addA = threading.Thread(target=lambda: m.add(f"助理:{A}",user_id=msg_info["openid"]))

        addA.start()
        addA.join()
        self.A = A
        return A

    def get_memory(self,msg_info):
        Q = msg_info["msg"].content
        openid = msg_info["openid"]
        m = self.mem
        # 使用数据库的示例代码
        logger.debug(f"admin类get_memory行为函数*********Q:{Q} -----------开始获取记忆-----------")        
        openid = msg_info["openid"]
        # 添加记忆
        logger.info(f"添加记忆：user{Q}-----------user_id：{openid}")
        m.add(f"user:{Q}",user_id=openid)
        # 获取记忆
        logger.info(f"开始搜索相关记忆")
        Q_memory = m.search(Q,user_id= openid) 
        logger.info(f"记忆搜索完成：{Q_memory}-----------user_id：{openid}")    
        logger.info(f"开始获取先前记忆") 
        privious_memory = m.get_all(user_id=openid)
        logger.info(f"获取先前记忆完成：{privious_memory}-----------user_id:{openid}")   
        self.memory[openid] = [Q_memory,privious_memory]
        return Q_memory,privious_memory


if __name__ == '__main__':

    ollama_client = ollama.Client()
    m = mem0.Memory.from_config(config)    # 耗时
    lightjunction = andim(WECHAT_TOKEN = "在微信公众平台自行设置",APPID = "微信公众号的唯一id",EncodingAESKey = "随机生成的固定值，用于加密",mem=m,ollama=ollama_client)
    # 管理员为核心！

    app = FastAPI()
    @app.get("/wechat")
    async def wechat_get(request: Request):
        result = await lightjunction.get(request)  # z这是必须的步骤，以为直接调用异步函数返回的是一个协程对象 必须用await调用 或者 async.run()
        return PlainTextResponse(content=result)
# 参考格式如下
# POST /wechat?signature=待定&timestamp=待定&nonce=待定&openid=待定&encrypt_type=aes&msg_signature=待定 HTTP/1.1

    @app.post("/wechat")
    async def wechat_post(request: Request):
        result = await lightjunction.post(request)
        return PlainTextResponse(content=result)
    

    uvicorn.run(app, host="0.0.0.0", port=8000)







