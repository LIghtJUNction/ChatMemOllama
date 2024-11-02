import Config
# 这是一个交互式指南
import Config

def main():
    print("欢迎使用配置向导，请根据提示输入相应的信息。")

    config = Config.Config()

    # 获取 WECHAT_TOKEN
    wechat_token = input("请输入微信公众平台的 WECHAT_TOKEN：")
    config.set('WECHAT_TOKEN', wechat_token)

    # 获取 APPID
    appid = input("请输入微信公众平台的 APPID：")
    config.set('APPID', appid)

    # 获取 EncodingAESKey
    encoding_aes_key = input("请输入微信公众平台的 EncodingAESKey：")
    config.set('EncodingAESKey', encoding_aes_key)

    # 获取 AdminID
    admin_id = input("请输入管理员的微信 OpenID（可选）：")
    config.set('AdminID', admin_id)

    # 获取 Tavilykey
    tavily_key = input("请输入 Tavily 的 API 密钥(函数调用搜索能力)：")
    config.set('Tavilykey', tavily_key)

    # 获取 su_key
    su_key = input("请输入超级用户密钥（可选）：")
    config.set('su_key', su_key)

    # 选择 llm_mode
    llm_mode = input("请选择语言模型模式（local 或 online）：")
    config.set('llm_mode', llm_mode)

    # 配置 llm
    if llm_mode == 'local':
        print("您选择了本地模型模式，请配置本地模型。")
        local_model = input("请输入本地模型名称（例如：llama3.1:latest）：")
        base_url = input("请输入 Ollama 服务的基址（例如：http://localhost:11434）：")
        config.set_nested(local_model, 'llm', 'local_config', 'model')
        config.set_nested(base_url, 'llm', 'local_config', 'base_url')
    elif llm_mode == 'online':
        print("您选择了在线模型模式，请配置在线模型。")
        online_model = input("请输入在线模型名称（例如：gpt-4）：")
        api_key = input("请输入在线模型的 API 密钥：")
        base_url = input("请输入在线模型的基址（如果有）：")
        config.set_nested(online_model, 'llm', 'online_config', 'model')
        config.set_nested(api_key, 'llm', 'online_config', 'API_key')
        config.set_nested(base_url, 'llm', 'online_config', 'base_url')
    else:
        print("无效的 llm_mode，默认为 local 模式。")
        config.set('llm_mode', 'local')

    # 配置 embedder
    print("请配置嵌入模型（embedder）。")
    embedder_provider = input("请输入嵌入模型提供者（例如：ollama）：")
    embedder_model = input("请输入嵌入模型名称（例如：nomic-embed-text:latest）：")
    embedder_base_url = input("请输入嵌入模型的基址（例如：http://localhost:11434）：")
    config.set_nested(embedder_provider, 'embedder', 'provider')
    config.set_nested(embedder_model, 'embedder', 'config', 'model')
    config.set_nested(embedder_base_url, 'embedder', 'config', 'ollama_base_url')

    # 保存配置
    config.save()
    print("配置已保存到", config.filename)

if __name__ == '__main__':
    main()
