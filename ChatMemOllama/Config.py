import json
class Config:
    def __init__(self, filename='./ChatMemOllama/config.json'):
        self.filename = filename
        self.data = {}
        self.load()

    def load(self):
        """从配置文件中加载数据。"""
        try:
            with open(self.filename, 'r', encoding='utf-8') as f:
                self.data = json.load(f)
                self.WechatToken = self.get("WechatToken")
                self.APPID = self.get("APPID")
                self.EncodingAESKey = self.get("EncodingAESKey")
                self.AdminID = self.get("AdminID")
                self.Sukey = self.get("Sukey")
                self.LlmMode = self.get("LlmMode")
                self.Tavilykey = self.get("Tavilykey")
                self.check()
                print("配置读取完毕")
        except FileNotFoundError:
            print(f"配置文件 {self.filename} 不存在，已创建新的配置。")
            self.data = {}
        except json.JSONDecodeError as e:
            print(f"配置文件格式错误：{e}")
            self.data = {}
    def check(self):
        if self.get("LlmMode") == "online":
            if not self.get_nested('llm', 'OnlineConfig', 'APIKey'):
                raise ValueError("未设置 OnlineConfig.APIKey")
            if not self.get_nested('llm', 'OnlineConfig', 'BaseUrl'):
                raise ValueError("未设置 OnlineConfig.BaseUrl")
            
            self.Model=self.get_nested('llm', 'OnlineConfig', 'Model')
            self.APIKey=self.get_nested('llm', 'OnlineConfig', 'APIKey')
            self.BaseUrl=self.get_nested('llm', 'OnlineConfig', 'BaseUrl')
        elif self.get("LlmMode") == "local":
            self.Model=self.get_nested('llm', 'LocalConfig', 'Model')
            self.BaseUrl=self.get_nested('llm', 'LocalConfig', 'BaseUrl')


    def save(self):
        """将当前数据保存到配置文件中。"""
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self.data, f, ensure_ascii=False, indent=4)

    def get(self, key, default=None):
        """获取配置项的值。"""
        return self.data.get(key, default)

    def set(self, key, value):
        """设置配置项的值。"""
        self.data[key] = value

    def get_nested(self, *keys, default=None):
        """获取嵌套配置项的值。"""
        d = self.data
        for key in keys:
            if isinstance(d, dict):
                d = d.get(key, default)
            else:
                return default
        return d

    def set_nested(self, value, *keys):
        """设置嵌套配置项的值。"""
        d = self.data
        for key in keys[:-1]:
            d = d.setdefault(key, {})
        d[keys[-1]] = value


"""
from Config import Config

# 初始化配置类
config = Config()

# 获取配置项
wechat_token = config.get('WECHAT_TOKEN')
print(f"当前的 WECHAT_TOKEN: {wechat_token}")

# 设置新的配置项
config.set('WECHAT_TOKEN', 'new_wechat_token')
config.set('APPID', 'your_app_id')

# 设置嵌套的配置项
config.set_nested('llama3.1:latest', 'llm', 'local_config', 'model')
config.set_nested('http://localhost:11434', 'llm', 'local_config', 'base_url')

# 保存配置
config.save()

"""

if __name__ == "__main__":
    Config = Config()
    # debug
    print(Config.__dict__)  