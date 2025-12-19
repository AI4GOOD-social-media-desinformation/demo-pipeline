import os
import requests
from src.eventbus.InMemoryEventBus import InMemoryEventBus
from google import genai
from google.genai import types


class RelatedNewsFilter:
    """
    Filters and sends the top 2 most related news articles from the news list
    based on the analysis messages sent to the user.
    Triggered after `analysis_message_sender.completed`.
    """

    def __init__(self, eventbus: InMemoryEventBus | None = None):
        """
        Initialize the RelatedNewsFilter.
        
        Args:
            eventbus: InMemoryEventBus instance for publishing events
        """
        self.eventbus = eventbus
        self.client = genai.Client(api_key=os.getenv("GOOGLE_API_KEY"))
        self.model = "gemini-2.5-flash"

    def set_eventbus(self, eventbus: InMemoryEventBus):
        """Set the event bus for publishing events."""
        self.eventbus = eventbus

    def sanity_check_event_data(self, data: dict) -> None:
        """Ensure required fields are present in event data."""
        required_fields = ["data"]
        required_fields_data = ["userId", "news"]

        for field in required_fields:
            if field not in data:
                raise ValueError(f"Missing required field in event data: {field}")

        for field in required_fields_data:
            if field not in data["data"]:
                raise ValueError(f"Missing required field in event data['data']: {field}")

    def _chunk_message(self, message: str, limit: int = 1000) -> list[str]:
        """Split a message into chunks within the platform char limit."""
        if len(message) <= limit:
            return [message]
        return [message[i:i+limit] for i in range(0, len(message), limit)]

    def _find_related_news(self, messages: list[str], news_list: list[dict]) -> list[dict]:
        """
        Find the top 2 most related news articles using Gemini AI.
        
        Args:
            messages: List of analysis messages sent to the user
            news_list: List of news articles with title, description, and other metadata
            
        Returns:
            List of up to 2 most related news articles, or empty list if none are related
        """
        if not messages or not news_list:
            return []

        # Combine all messages into a single text
        combined_messages = " ".join(messages)

        # Build news list for the prompt
        news_items = []
        for i, news in enumerate(news_list, 1):
            title = news.get('title', 'Sem título')
            description = news.get('description', 'Sem descrição')
            news_items.append(f"Notícia {i}:\nTítulo: {title}\nDescrição: {description}")
        
        news_text = "\n\n".join(news_items)

        prompt = f"""
        Você é um assistente especializado em análise de relevância de notícias.
        
        Dada a seguinte análise enviada ao usuário:
        {combined_messages}
        
        E a seguinte lista de notícias:
        {news_text}
        
        Selecione as TOP 2 notícias mais relacionadas com o conteúdo da análise enviada.
        Se NENHUMA notícia for relevante ou relacionada, retorne apenas "NENHUMA".
        
        Retorne APENAS os números das notícias selecionadas separados por vírgula (ex: "1, 3" ou "2, 5").
        Se nenhuma for relevante, retorne apenas: "NENHUMA"
        
        Não inclua qualquer texto adicional, explicação ou formatação.
        """

        try:
            response = self.client.models.generate_content(
                model=self.model,
                contents=[prompt],
                config=types.GenerateContentConfig(
                    temperature=0.2
                )
            )

            if not response.text:
                return []

            result = response.text.strip()
            
            # Check if no news is related
            if result.upper() == "NENHUMA":
                return []

            # Parse the selected news indices
            selected_indices = []
            try:
                for num in result.replace(" ", "").split(","):
                    if num.strip().isdigit():
                        idx = int(num.strip()) - 1  # Convert to 0-based index
                        if 0 <= idx < len(news_list):
                            selected_indices.append(idx)
            except Exception as e:
                print(f"Error parsing Gemini response: {e}")
                return []

            # Return the selected news (max 2)
            return [news_list[i] for i in selected_indices[:2]]

        except Exception as e:
            print(f"Error using Gemini for news filtering: {e}")
            return []

    def _format_news_message(self, news_article: dict) -> str:
        """
        Format a news article into a message string.
        
        Args:
            news_article: News article dictionary with title, url, and source
            
        Returns:
            Formatted message string
        """
        title = news_article.get('title', 'Sem título')
        url = news_article.get('url', '')
        source = news_article.get('source', 'Fonte desconhecida')
        
        message = f"📰 {title}\n"
        message += f"Fonte: {source}\n"
        if url:
            message += f"Link: {url}"
        
        return message

    def run(self, event_data: dict) -> None:
        """
        Filter and send the top 2 most related news articles to the user.
        
        Args:
            event_data: Event data containing userId, messages, and news list
        """
        try:
            self.sanity_check_event_data(event_data)

            messages = event_data["data"].get("messages", [])
            news_list = event_data["data"].get("news", [])
            sender_id = event_data["data"]["userId"]

            # Find related news
            related_news = self._find_related_news(messages, news_list)

            # If no related news found, don't send anything
            if not related_news:
                print(f"No related news found for user {sender_id}")
                if self.eventbus:
                    self.eventbus.publish(
                        "related_news_filter.completed",
                        {"id": event_data.get("id"), "news_sent": 0}
                    )
                return

            # Send the related news via Instagram DM
            url = "https://graph.instagram.com/v21.0/me/messages"
            token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
            
            headers = {
                "Authorization": f"Bearer {token}",
                "Content-Type": "application/json",
            }

            # Send introductory message
            intro_message = "Segue notícias potencialmente relacionadas com o vídeo mandado:"
            intro_payload = {
                "message": {"text": intro_message},
                "recipient": {"id": sender_id},
            }
            try:
                response = requests.post(url, headers=headers, json=intro_payload)
                response.raise_for_status()
                print("Intro message sent for related news")
            except requests.exceptions.RequestException as e:
                print(f"Error sending intro message: {e}")

            news_sent = 0
            for news in related_news:
                formatted_message = self._format_news_message(news)
                
                for chunk in self._chunk_message(formatted_message):
                    payload = {
                        "message": {"text": chunk},
                        "recipient": {"id": sender_id},
                    }
                    response = requests.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    print(f"Related news sent: {news.get('title', 'N/A')[:50]}...")
                
                news_sent += 1

            if self.eventbus:
                self.eventbus.publish(
                    "related_news_filter.completed",
                    {"id": event_data.get("id"), "news_sent": news_sent}
                )

        except ValueError as e:
            print(f"Validation error in RelatedNewsFilter: {e}")
            if self.eventbus:
                self.eventbus.publish(
                    "related_news_filter.failed",
                    {"id": event_data.get("id", "unknown"), "error": str(e)}
                )
        except requests.exceptions.RequestException as e:
            print(f"Error sending related news: {e}")
            error_body = getattr(e.response, "text", "")
            print("Response Body:", error_body)
            if self.eventbus:
                self.eventbus.publish(
                    "related_news_filter.failed",
                    {"id": event_data.get("id", "unknown"), "error": str(e)}
                )
        except Exception as e:
            print(f"Unexpected error in RelatedNewsFilter: {e}")
            if self.eventbus:
                self.eventbus.publish(
                    "related_news_filter.failed",
                    {"id": event_data.get("id", "unknown"), "error": str(e)}
                )
