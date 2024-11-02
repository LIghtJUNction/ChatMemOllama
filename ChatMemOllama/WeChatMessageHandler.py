# WechatConfig.py
from fastapi import HTTPException
from wechatpy import parse_message, create_reply
from wechatpy.utils import check_signature
from wechatpy.crypto import WeChatCrypto
from wechatpy.exceptions import InvalidSignatureException, InvalidAppIdException

class WeChatMessageHandler():
    def __init__(self,Config):
        self.Config = Config
        self.crypto = WeChatCrypto(Config.WechatToken, Config.WechatToken, Config.WechatToken)

    async def check(self, request):  # 检查微信消息签名 // 使用本函数无需额外再调用_get_msg_info
        msg_info = await self._get_msg_info(request)
        try:
            check_signature(self.WechatToken, msg_info["signature"], msg_info["timestamp"], msg_info["nonce"])
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
            # "msg": msg 解密后获得  msg_info["msg"].content ， 消息类型：msg_info["msg"].type 用户openid：msg_info["msg"].source 
            # "A" : A AI/程序处理后获得 
        }
        return msg_info

    async def decode(self, msg_info):
        msg_xml = self.crypto.decrypt_message(msg_info['body'], msg_info["msg_signature"], msg_info["timestamp"], msg_info["nonce"])
        msg = parse_message(msg_xml)
        msg_info["msg"] = msg
        return msg_info  # 添加解密并且解析后的msg

    async def encode(self, A, msg_info):
        reply = create_reply(A, msg_info["msg"])
        if reply is None:
            raise ValueError("reply 对象未正确初始化或赋值为 None")

        result = self.crypto.encrypt_message(reply.render(), msg_info["nonce"], msg_info["timestamp"])  # 加密数据包
        return result  # 加密后的xml

# do one thing and do it well