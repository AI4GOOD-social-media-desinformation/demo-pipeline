from typing import Any
from collections.abc import Generator, Iterable
from typing_extensions import TypedDict

from gnews import GNews
from newsapi import NewsApiClient
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
import unicodedata
import re

"""
Usage example:

if __name__ == "__main__":
    matcher = NewsMatcher(
        similarity_threshold=0.01,
        # recency_days=7
    )

    sentence = (
        "Lula aprova um novo decreto que reduz preço nos alimentos"
    )

    results = matcher.fetch_news(query)
    reuslts -> [ 
        {"title": "...", "url": "...", "source": "...", "score": 0.87},
    ]
"""

class NewsMatcher:
    """
    Robust sentence-level news matcher for Brazilian Portuguese.

    Features:
    - GNews + NewsAPI sources
    - Recency filtering
    - Input sentence refinement (fact extraction)
    - Sentence-level similarity
    """

    PT_STOPWORDS = [
        "a", "o", "os", "as", "um", "uma", "uns", "umas",
        "de", "do", "da", "dos", "das",
        "em", "no", "na", "nos", "nas",
        "por", "para", "com", "sem",
        "e", "ou", "mas", "que",
        "é", "foi", "são", "ser",
        "ao", "aos", "à", "às",
        "como", "mais", "menos",
        "isso", "esse", "essa", "este", "esta",
        "já", "também", "sobre", "entre"
    ]

    WEAK_WORDS = {
        "acha", "pensa", "acredita", "opina",
        "expressa", "demonstra", "critica",
        "adora", "odeia", "gosta",
        "sua", "seu", "dele", "dela",
        "muito", "pouco", "grande", "pequeno",
        "promete", "prometendo"
    }


    def __init__(
        self,
        newsapi_key="5a96668439fd4ad1b8136646d029a157",
        max_results=5,
        top_n=2,
        similarity_threshold=0.0001,
        recency_days=None,
        
    ):
        self.max_results = max_results
        self.top_n = top_n
        self.similarity_threshold = similarity_threshold
        self.recency_days = recency_days

        gnews_args = {
            "language": "pt",
            "country": "BR",
            "max_results": max_results
        }
        if recency_days:
            gnews_args["period"] = f"{recency_days}d"

        self.gnews = GNews(**gnews_args)

        self.newsapi = NewsApiClient(api_key=newsapi_key)

    def sanity_check_event_data(self, data: dict) -> None:
        required_fields = ["id", "data"]
        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field in event data: {field}")
        if "claim" not in data["data"]:
            raise ValueError("Missing required field in event data['data']: claim")
        # Ensure event bus is set before running
        if not getattr(self, "eventbus", None):
            raise ValueError("EventBus not set. Call set_eventbus() before run().")

    @staticmethod
    def _normalize(text):
        text = text.lower()
        text = unicodedata.normalize("NFKD", text)
        return "".join(c for c in text if not unicodedata.combining(c))

    @staticmethod
    def _split_sentences(text):
        sentences = re.split(r"[.!?]\s+", text.strip())
        return [s for s in sentences if len(s) > 10]

    def _extract_keywords(self, text):

        propmpt = f"Transforme o seguinte texto em uma lista de três palavras-chave separadas por ' ':\n\n {text}."
        response = self.client.models.generate_content(
            model=self.model,
            contents=[propmpt]
        )
        print(f"DEBUG: Keywords response: {response.text}")
        return response.text
        

    @classmethod
    def _split_user_sentence(cls, text):
        """
        Converts long narrative input into multiple factual sub-sentences.
        """
        text = cls._normalize(text)

        parts = re.split(r"[.!?]", text)

        final_parts = []
        for part in parts:
            subparts = re.split(
                r"\b(que|mas|onde|porque|pois|quando|enquanto)\b",
                part
            )
            final_parts.extend(subparts)

        refined = []
        for p in final_parts:
            words = [
                w for w in p.split()
                if w not in cls.PT_STOPWORDS
                and w not in cls.WEAK_WORDS
                and len(w) > 3
            ]

            if len(words) >= 3:
                refined.append(" ".join(words))

        return refined

    def _fetch_news(self, query: str) -> Generator[dict[str, Any], None, None]:
        """
        Fetch news articles from multiple sources.
        Yields articles as dictionaries with keys: title, description, url.
        """
        gnews_articles = self.gnews.get_news(query)

        if gnews_articles:
            for article in gnews_articles:
                yield {
                    "source": "GNews",
                    "publisher": article.get("publisher", {}).get("title", ""),
                    "date": article.get("published date", ""),
                    "title": article.get("title", ""),
                    "description": article.get("description", ""),
                    "url": article.get("url", "")
                }
        
        newsapi_response = self.newsapi.get_everything(
            q=query,
            language="pt",
            page_size=self.max_results,
            sort_by="relevancy"
        )

        for article in newsapi_response.get("articles", []):
            yield {
                "source": "NewsAPI",
                "title": article.get("title", ""),
                "description": article.get("description", ""),
                "url": article.get("url", "")
            }

    def _score_article(self, input_sentence: str, title: str, description: str) -> float:
        full_text = self._normalize(f"{title}. {description}")
        sentences = self._split_sentences(full_text)

        if not sentences:
            return 0.0

        documents = [input_sentence] + sentences

        tfidf = TfidfVectorizer(
            stop_words=self.PT_STOPWORDS,
            ngram_range=(1, 2)
        )

        tfidf_matrix = tfidf.fit_transform(documents)

        similarities = cosine_similarity(
            tfidf_matrix[0:1],
            tfidf_matrix[1:]
        ).flatten()

        return similarities.max()


    def run(self, queries: Iterable[str]) -> list[dict[str, Any]]:
        """
        Returns a list of similar news articles.
        Returns empty list if nothing is relevant enough.
        """
        
        results: list[dict[str, Any]] = []
        seen_urls: set[str] = set()

        for query in queries:
            for article in self._fetch_news(query):
                url = article["url"]

                if not url or url in seen_urls: continue
                    
                score = self._score_article(
                    query,
                    article.get("title", ""),
                    article.get("description", "")
                )

                if score >= self.similarity_threshold:
                    seen_urls.add(url)
                    results.append({
                        "source": article["source"],
                        "score": float(score),
                        "title": article["title"],
                        "url": url,
                        "query": query,
                        "description": article["description"]
                    })
            
        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:self.top_n]