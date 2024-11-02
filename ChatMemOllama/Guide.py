from Config import Config
# 这是一个交互式指南

class Guide():
    def __init__(self):
        self.config = Config()
        self.config.load()

    def main(self):
        print("欢迎使用配置向导，请根据提示输入相应的信息。")

        # 获取 WECHAT_TOKEN
        wechat_token = input("请输入微信公众平台的 WECHAT_TOKEN：")
        self.config.set('WECHAT_TOKEN', wechat_token)

        # 获取 APPID
        appid = input("请输入微信公众平台的 APPID：")
        self.config.set('APPID', appid)

        # 获取 EncodingAESKey
        encoding_aes_key = input("请输入微信公众平台的 EncodingAESKey：")
        self.config.set('EncodingAESKey', encoding_aes_key)

        # 获取 AdminID
        admin_id = input("请输入管理员的微信 OpenID（可选）：")
        self.config.set('AdminID', admin_id)

        # 获取 Tavilykey
        tavily_key = input("请输入 Tavily 的 API 密钥(函数调用搜索能力)：")
        self.config.set('Tavilykey', tavily_key)

        # 获取 su_key
        su_key = input("请输入超级用户密钥（可选）：")
        self.config.set('su_key', su_key)

        # 选择 llm_mode
        llm_mode = input("请选择语言模型模式（local 或 online）：")
        self.config.set('llm_mode', llm_mode)

        # 配置 llm
        if llm_mode == 'local':
            print("您选择了本地模型模式，请配置本地模型。")
            local_model = input("请输入本地模型名称（例如：llama3.1:latest）：")
            base_url = input("请输入 Ollama 服务的基址（例如：http://localhost:11434）：")
            self.config.set_nested(local_model, 'llm', 'local_config', 'model')
            self.config.set_nested(base_url, 'llm', 'local_config', 'base_url')
        elif llm_mode == 'online':
            print("您选择了在线模型模式，请配置在线模型。")
            online_model = input("请输入在线模型名称（例如：gpt-4o")
            self.config.set_nested(online_model, 'llm', 'online_config', 'model')
            print("在线模型需要你提供一个 API 密钥，以便访问在线模型。以及一个基址。")
            APIKey = input("请输入在线模型的 API 密钥：")
            BaseUrl = input("请输入在线模型的基址：")
            self.config.set_nested(APIKey, 'llm', 'online_config', 'APIKey')
            self.config.set_nested(BaseUrl, 'llm', 'online_config', 'BaseUrl')

        
if __name__ == '__main__':
    guide = Guide()
    guide.main()
