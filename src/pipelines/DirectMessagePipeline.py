
from src.eventbus.InMemoryEventBus import InMemoryEventBus
from src.modules.ReelsDonwloader import ReelsDownloader
from src.modules.GeminiClaimExtraction import GeminiClaimExtraction


class DirectMessagePipeline:
    """
    Pipeline to upload datasets to Firestore with event bus integration.
    """
    def __init__(self, saving_dir: str = "data/requests"):
        # Initialize Event Bus
        self.event_bus = InMemoryEventBus()
        self.storage_service = ReelsDownloader(saving_dir=saving_dir)
        self.claim_extraction_module = GeminiClaimExtraction()
        self.add_event_subscriptions()
        self.claim_extraction_module.set_eventbus(self.event_bus)
        self.storage_service.set_eventbus(self.event_bus)
    
    def add_event_subscriptions(self):
        """Subscribe event handlers to the event bus."""
        handlers = {
            "reels_download.completed": self.claim_extraction_module.run,
            "claim_extraction.completed": self.on_success,
            "claim_extraction.failed": self.on_error,
            "storage_service.failed": self.on_error,        }
        
        for topic, handler in handlers.items():
            self.event_bus.subscribe(topic, handler)

    def on_error(self, event_data: dict):
        """
        Handle errors during pipeline execution.
        
        Args:
            event_data: Dictionary containing error details.
        """
        print(f"{event_data.get('erro', '')} - Error occurred  last logged event data: {event_data}")

    def on_success(self, event_data: dict):
        """
        Handle successful completion of the pipeline.
        
        Args:
            event_data: Dictionary containing success details.
        """
        print(f"Pipeline completed successfully. Details: {event_data}")

    def run(self, data: dict):

        """
        For a certain ID of a local dutaset start the upload to Firestore.
        """

        print("\n" + "="*70)
        print("DATASET CLOUD PIPELINE: Upload Dataset to Firestore")
        print("="*70 + "\n")

        

        videoUrl = data.get("data", {}).get("videoUrl")
        request_id = data.get("id")
        self.storage_service.run({
            "data": {
                "videoUrl": videoUrl,
            },
            "id": request_id
        })




            