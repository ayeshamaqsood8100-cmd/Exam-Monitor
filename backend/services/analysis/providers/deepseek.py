from backend.services.analysis.providers.base import OpenAICompatibleProvider


class DeepSeekProvider(OpenAICompatibleProvider):
    base_url = "https://api.deepseek.com/chat/completions"
