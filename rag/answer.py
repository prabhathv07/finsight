"""Answer generation for retrieved context.

An answerer is a callable that takes the question and the assembled context
and returns prose. The Gemini implementation reuses the same client and
fence-stripping as the daily commentator; tests inject a fake so no key or
network is needed.
"""

from analysis.llm import strip_code_fence

PROMPT = (
    "You are FinSight's research assistant. Answer the user's question using "
    "only the briefing excerpts provided below. Each excerpt is labelled with "
    "its briefing date. Cite the dates you rely on inline, like (2026-01-06). "
    "If the excerpts do not contain the answer, say so plainly rather than "
    "guessing. Do not give individual financial advice.\n\n"
)


def build_context(results):
    """Render retrieved (chunk, score) pairs into a labelled context block."""
    blocks = []
    for chunk, _score in results:
        label = f"[{chunk.run_date.isoformat()} | {chunk.source}]"
        blocks.append(f"{label}\n{chunk.content}")
    return "\n\n".join(blocks)


class GeminiAnswerer:
    name = "gemini"

    def __init__(self, api_key, model):
        self.api_key = api_key
        self.model = model
        self._client = None

    def _client_or_create(self):
        if self._client is None:
            from google import genai

            self._client = genai.Client(api_key=self.api_key)
        return self._client

    def __call__(self, question, context):
        client = self._client_or_create()
        contents = f"{PROMPT}QUESTION: {question}\n\nBRIEFING EXCERPTS:\n{context}"
        response = client.models.generate_content(
            model=self.model, contents=contents
        )
        return strip_code_fence(response.text)
