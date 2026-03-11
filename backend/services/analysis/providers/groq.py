from backend.services.analysis.providers.base import OpenAICompatibleProvider


class GroqProvider(OpenAICompatibleProvider):
    base_url = "https://api.groq.com/openai/v1/chat/completions"
