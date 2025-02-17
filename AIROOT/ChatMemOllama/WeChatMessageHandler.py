from robyn import Robyn
from robyn.responses import PlainTextResponse
from robyn.robyn import Request

from wechatpy import parse_message, create_reply
from wechatpy.utils import check_signature
from wechatpy.crypto import WeChatCrypto
from wechatpy.exceptions import InvalidSignatureException, InvalidAppIdException


class WeChatMessageHandler():
    def __init__(self,Config):
        self.Config = Config
        try:
            self.crypto = WeChatCrypto(Config.WechatToken, Config.EncodingAESKey, Config.APPID)
        except Exception as e:
            print(f"加密模块初始化失败!")
            raise ValueError("加密模块初始化失败,是不是忘了填3个必须参数,跳转至使用指南...")
            # 运行指南类 - - 微信配置交互函数
    async def check(self, request):  # 检查微信消息签名 // 使用本函数无需额外再调用_get_msg_info
        msg_info = await self._get_msg_info(request)
        try:
            check_signature(self.Config.WechatToken, msg_info["signature"], msg_info["timestamp"], msg_info["nonce"])
        except InvalidSignatureException:
            print("无效的微信签名请求")
            raise HTTPException(status_code=403, detail="无效的签名!")
        return msg_info

    async def _get_msg_info(self, request):
        msg_info = {
            'timestamp': request.query_params.get('timestamp'),
            'nonce': request.query_params.get('nonce'),
            'signature': request.query_params.get('signature'),
            'msg_signature': request.query_params.get("msg_signature", ""),
            "echo_str": request.query_params.get("echostr", ""),
            'openid': request.query_params.get("openid", ""),
            "body": await request.body()

            # k 对话历史记录最大长度
            # "msg": msg 解密后获得  msg_info["msg"].content ， 消息类型：msg_info["msg"].type 用户openid：msg_info["msg"].source 
            # "A" : A AI/程序处理后获得 AI_的响应
            # messages 由程序生成 这对话历史记录 一个列表
            # ...
        }
        return msg_info

    async def decode(self, msg_info):
        msg_xml = self.crypto.decrypt_message(msg_info['body'], msg_info["msg_signature"], msg_info["timestamp"], msg_info["nonce"])
        msg = parse_message(msg_xml)
        msg_info["msg"] = msg
        return msg_info  # 添加解密并且解析后的msg

    async def encode(self,msg_info):
        if msg_info["A"] is None:
            raise ValueError("msg_info[A] 未初始化或赋值为 None")
        
        reply = create_reply(msg_info["A"],msg_info["msg"])
        result = self.crypto.encrypt_message(reply.render(), msg_info["nonce"], msg_info["timestamp"])  # 加密数据包
        return result  # 加密后的xml


if __name__ == "__main__":
    import time
    # 参考格式如下
    # POST /wechat?signature=待定&timestamp=待定&nonce=待定&openid=待定&encrypt_type=aes&msg_signature=待定 HTTP/1.1

    WeChatMessageHandler = WeChatMessageHandler()
    ChatMemOllama_devTest = Robyn(__file__)
    # 启动
    # 提示 如果不添加" : Request "会报错  不能正确解析传入的请求 错误代码:422 Unprocessable Entity
    @ChatMemOllama_devTest.get("/wechat")
    async def wechat_get(request : Request):
        msg_info =  await WeChatMessageHandler.check(request)
        result = msg_info["echo_str"]
        return PlainTextResponse(content=result)
    @ChatMemOllama_devTest.post("/wechat")
    async def wechat_post(request : Request):
        msg_info = await WeChatMessageHandler.check(request)
        msg_info = await WeChatMessageHandler.decode(msg_info)
        print(msg_info)
        msg_info["A"] = f"连通测试- - - 你刚刚发送了Q:{msg_info["msg"].content}"
        result = await WeChatMessageHandler.encode(msg_info)
        return PlainTextResponse(content=result)
    
    ChatMemOllama_devTest.start(port=8009)