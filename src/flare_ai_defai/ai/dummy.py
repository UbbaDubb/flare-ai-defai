class DummyResponse:
    def __init__(self, text: str):
        self.text = text


class DummyAIProvider:
    def reset(self):
        pass

    def send_message(self, message: str):
        return DummyResponse(f"[SIMULATED AI] You said: {message}")

    def generate(
        self,
        prompt: str,
        response_mime_type: str | None = None,
        response_schema: dict | None = None,
    ):
        return DummyResponse("[SIMULATED AI RESPONSE]")
