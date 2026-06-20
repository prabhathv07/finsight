"""Embeddings.

Like the commentator, an embedder is just a callable: it takes a list of
texts and returns a list of vectors. The Gemini implementation lives here;
the indexing and retrieval code take the callable as an argument so tests can
pass a deterministic fake and never touch the network or need a key.
"""

import math


class GeminiEmbedder:
    name = "gemini"

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

    def __call__(self, texts):
        client = self._client_or_create()
        response = client.models.embed_content(model=self.model, contents=texts)
        # google-genai returns an object with .embeddings, each having .values.
        return [list(e.values) for e in response.embeddings]


def cosine_similarity(a, b):
    """Plain cosine similarity for the SQLite retrieval path."""
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    if na == 0 or nb == 0:
        return 0.0
    return dot / (na * nb)
