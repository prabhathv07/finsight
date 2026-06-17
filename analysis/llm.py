"""LLM commentary.

A commentator is any callable that takes the summary text and returns
commentary. The Gemini implementation lives here; the analysis service
takes the callable as an argument so tests can pass a fake one and never
touch the network or need a key.
"""

PROMPT = (
    "You are a market analyst writing a short pre-market briefing for retail "
    "traders. Using only the data below, summarize the setup for the day: the "
    "tone of futures and macro, notable sector and watchlist moves, and the "
    "main risks. Be concise and specific. Do not give individual financial "
    "advice. Data follows.\n\n"
)


def strip_code_fence(text):
    """Drop a leading ```/```html fence if the model wraps its reply."""
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```", 2)[1]
        if text.startswith("html"):
            text = text[4:]
        text = text.strip()
    return text


class GeminiCommentator:
    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _client_or_create(self):
        if self._client is None:
            # Imported here so the package loads without google-genai present.
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def __call__(self, summary_text):
        client = self._client_or_create()
        response = client.models.generate_content(
            model=self.model,
            contents=PROMPT + summary_text,
        )
        return strip_code_fence(response.text)
