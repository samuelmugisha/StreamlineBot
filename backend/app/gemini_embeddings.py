import time
import logging
import requests
from langchain_core.embeddings import Embeddings

logger = logging.getLogger(__name__)

# Supabase vector column is vector(768); pin output to match.
_OUTPUT_DIMENSIONALITY = 768

# 0.7s between calls = ~85 req/min — 15% under the 100 RPM free-tier cap.
# Using direct REST calls (no SDK) so there are zero hidden internal retries
# that could burn extra quota.
_INTER_REQUEST_DELAY = 0.7

_BASE_URL = "https://generativelanguage.googleapis.com/v1beta/models"


class GeminiEmbeddings(Embeddings):
    def __init__(self, model: str, api_key: str):
        self._api_key = api_key
        self._model = model
        self._url = f"{_BASE_URL}/{model}:batchEmbedContents"

    def _embed_one(self, text: str, max_retries: int | None = None) -> list[float]:
        payload = {
            "requests": [
                {
                    "model": f"models/{self._model}",
                    "content": {"parts": [{"text": text}]},
                    "outputDimensionality": _OUTPUT_DIMENSIONALITY,
                }
            ]
        }
        headers = {
            "x-goog-api-key": self._api_key,
            "Content-Type": "application/json",
        }

        attempts = 0
        while True:
            resp = requests.post(self._url, json=payload, headers=headers, timeout=30)
            if resp.status_code == 429:
                attempts += 1
                if max_retries is not None and attempts > max_retries:
                    resp.raise_for_status()
                wait = 65
                try:
                    for detail in resp.json().get("error", {}).get("details", []):
                        if "retryDelay" in detail:
                            wait = int(detail["retryDelay"].rstrip("s")) + 5
                            break
                except Exception:
                    pass
                logger.warning("429 rate limit hit — sleeping %ds then retrying.", wait)
                time.sleep(wait)
                continue
            resp.raise_for_status()
            return resp.json()["embeddings"][0]["values"]

    def embed_documents(self, texts: list[str]) -> list[list[float]]:
        total = len(texts)
        logger.info("Embedding %d chunks at 0.7s/chunk (~8 min)...", total)
        embeddings = []
        for i, text in enumerate(texts):
            embeddings.append(self._embed_one(text))
            if (i + 1) % 50 == 0:
                logger.info("  Embedded %d/%d chunks.", i + 1, total)
            time.sleep(_INTER_REQUEST_DELAY)
        logger.info("Embedding complete: %d chunks.", total)
        return embeddings

    def embed_query(self, text: str) -> list[float]:
        return self._embed_one(text, max_retries=1)
