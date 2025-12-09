from typing import Callable

# Define the Abstract Interface for clarity (Optional, but good practice)
# class EventBus:
#     def publish(self, topic: str, event_data: dict): ...
#     def subscribe(self, topic: str, handler: Callable[[dict], None]): ...

class InMemoryEventBus:
    """
    Implements a simple, synchronous, in-memory Event Bus.
    Events are immediately delivered to all subscribed handlers within the same process.
    """
    def __init__(self):
        # Topic -> list of handler functions
        self._subscriptions: dict[str, list[Callable[[dict], None]]] = {}
        print("Local Event Bus initialized (In-Memory).")

    def publish(self, topic: str, event_data: dict):
        """Publishes an event to a topic, triggering all handlers."""
        print(f"--- Event Published: TOPIC='{topic}' ---")
        
        
        if topic in self._subscriptions:
            for handler in self._subscriptions[topic]:
                try:
                    print(f"  -> Delivering to handler: {handler.__name__}")
                    handler(event_data)
                except Exception as e:
                   print(f"  !! Handler '{handler.__name__}' failed with error: {e}")
        else:
            print(f"  -> No subscribers for topic: {topic}")

    def subscribe(self, topic: str, handler: Callable[[dict], None]):
        """Registers a handler function to receive events for a specific topic."""
        if topic not in self._subscriptions:
            self._subscriptions[topic] = []
        self._subscriptions[topic].append(handler)
        print(f"Subscription added: TOPIC='{topic}', HANDLER='{handler.__name__}'")