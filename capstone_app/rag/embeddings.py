"""A minimal LangChain-compatible Embeddings wrapper around OpenAI's own
Python client, used instead of the `langchain-openai` package.

Why: langchain-openai requires openai>=2.45,<4.0, but every openai version
in that range ships a broken bundled HTTP client (a genuine upstream bug —
every request fails with `Decompressor.decompress() got an unexpected
keyword argument 'output_buffer_limit'`, unrelated to the API key or
network — see the pin comment in requirements.txt). This app already
depends on openai==1.54.4 for chat completions (see
pages/2_Policy_Explainer.py), which works correctly, so embeddings just
reuse that same pinned client instead of pulling in the incompatible one.
"""
from langchain_core.embeddings import Embeddings
from openai import OpenAI


class OpenAIEmbeddingsCompat(Embeddings):
    def __init__(self, api_key: str, model: str = "text-embedding-3-small"):
        self._client = OpenAI(api_key=api_key)
        self._model = model

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        response = self._client.embeddings.create(model=self._model, input=texts)
        return [d.embedding for d in response.data]

    def embed_query(self, text: str) -> list[float]:
        return self.embed_documents([text])[0]
