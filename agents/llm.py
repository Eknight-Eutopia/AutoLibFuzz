from langchain.chat_models import BaseChatModel, init_chat_model
from config.config import config

class BaseLLMModel:
    _instance = None
    _initialized = False

    def __new__(cls, *args, **kwargs):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance
    
    def __init__(self):
        if self._initialized:
            return
        self.config = config["llm"]
        self._initialized = True
    
    def create_model(self) -> BaseChatModel:
        model = init_chat_model(
            base_url=self.config["api_base"],
            api_key=self.config["api_key"],
            model=self.config["base_model"],
            default_headers={
                "User-Agent": "curl/8.0",
            }
        )
        return model
    
llm_base = BaseLLMModel()