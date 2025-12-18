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

    results = matcher.fetch_news(sentence)
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
        max_results=20,
        top_n=3,
        similarity_threshold=0.001,
        recency_days=None
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

    @staticmethod
    def _normalize(text):
        text = text.lower()
        text = unicodedata.normalize("NFKD", text)
        return "".join(c for c in text if not unicodedata.combining(c))

    @staticmethod
    def _split_sentences(text):
        sentences = re.split(r"[.!?]\s+", text.strip())
        return [s for s in sentences if len(s) > 10]

    @classmethod
    def _extract_keywords(cls, text):
        words = cls._normalize(text).split()
        keywords = [
            w for w in words
            if w not in cls.PT_STOPWORDS and len(w) > 3
        ]
        return " ".join(keywords[:5])


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

    def _fetch_gnews(self, query):
        return self.gnews.get_news(query)

    def _fetch_newsapi(self, query):
        response = self.newsapi.get_everything(
            q=query,
            language="pt",
            page_size=self.max_results,
            sort_by="relevancy"
        )
        return response.get("articles", [])

    def _score_article(self, input_sentence, title, description):
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


    def fetch_news(self, input_sentence):
        """
        Returns a list of similar news articles.
        Returns empty list if nothing is relevant enough.
        """

        candidate_inputs = self._split_user_sentence(input_sentence)
        if not candidate_inputs:
            return []

        search_query = self._extract_keywords(input_sentence)
        if not search_query:
            return []

        results = []

        for article in self._fetch_gnews(search_query):
            best_score = 0.0
            for candidate in candidate_inputs:
                score = self._score_article(
                    candidate,
                    article.get("title", ""),
                    article.get("description", "")
                )
                best_score = max(best_score, score)

            if best_score >= self.similarity_threshold:
                results.append({
                    "source": "GNews",
                    "score": float(best_score),
                    "title": article["title"],
                    "url": article["url"]
                })

        for article in self._fetch_newsapi(search_query):
            best_score = 0.0
            for candidate in candidate_inputs:
                score = self._score_article(
                    candidate,
                    article.get("title", ""),
                    article.get("description", "")
                )
                best_score = max(best_score, score)

            if best_score >= self.similarity_threshold:
                results.append({
                    "source": "NewsAPI",
                    "score": float(best_score),
                    "title": article["title"],
                    "url": article["url"]
                })

        unique = {}
        for r in results:
            unique[r["url"]] = r

        final_results = list(unique.values())
        final_results.sort(key=lambda x: x["score"], reverse=True)

        return final_results[:self.top_n]
