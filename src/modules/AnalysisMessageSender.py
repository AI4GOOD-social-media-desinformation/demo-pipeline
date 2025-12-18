import os
import requests
from src.eventbus.InMemoryEventBus import InMemoryEventBus


class AnalysisMessageSender:
    """
    Sends the disinformation analysis result back to the Instagram user via DM.
    Triggered after `disinformation_analysis.completed` with the analysis message and userId.
    """

    def __init__(self, eventbus: InMemoryEventBus | None = None):
        self.eventbus = eventbus

    def set_eventbus(self, eventbus: InMemoryEventBus):
        """Set the event bus for publishing events."""
        self.eventbus = eventbus

    def sanity_check_event_data(self, data: dict) -> None:
        """Ensure required fields are present in event data."""
        required_fields = ["data"]
        required_fields_data = ["userId"]

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

    def run(self, event_data: dict) -> None:
        """Send the analysis messages to the Instagram user, respecting char limits."""
        self.sanity_check_event_data(event_data)

        url = "https://graph.instagram.com/v21.0/me/messages"
        token = os.getenv("INSTAGRAM_ACCESS_TOKEN")
        sender_id = event_data["data"]["userId"]

        messages = event_data["data"].get("messages")
        if not messages:
            fallback = event_data["data"].get(
                "analysisMessage",
                "A análise foi concluída, mas não foi possível recuperar o resultado.",
            )
            messages = [fallback]

        headers = {
            "Authorization": f"Bearer {token}",
            "Content-Type": "application/json",
        }

        try:
            for msg in messages:
                for chunk in self._chunk_message(msg):
                    payload = {
                        "message": {"text": chunk},
                        "recipient": {"id": sender_id},
                    }
                    response = requests.post(url, headers=headers, json=payload)
                    response.raise_for_status()
                    print("Message chunk sent:", response.json())

            if self.eventbus:
                self.eventbus.publish(
                    "analysis_message.completed", {"id": event_data.get("id")}
                )
        except requests.exceptions.RequestException as e:
            print("Error sending final message:", e)
            error_body = getattr(e.response, "text", "")
            print("Response Body:", error_body)
            if self.eventbus:
                self.eventbus.publish(
                    "analysis_message.failed",
                    {"id": event_data.get("id", "unknown"), "error": str(e)},
                )
