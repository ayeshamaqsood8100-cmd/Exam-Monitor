from backend.services.analysis.providers.base import OpenAICompatibleProvider


class OpenRouterProvider(OpenAICompatibleProvider):
    base_url = "https://openrouter.ai/api/v1/chat/completions"
    title_header = ("HTTP-Referer", "https://markaz.local")
