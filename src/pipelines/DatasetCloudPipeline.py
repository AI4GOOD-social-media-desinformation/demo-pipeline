
from src.eventbus.InMemoryEventBus import InMemoryEventBus
from src.storage.LoaderDatasetFirestore import LocalDatasetFirestore
from src.modules.GeminiClaimExtraction import GeminiClaimExtraction
import asyncio


class DatasetCloudPipeline:
    """
    Pipeline to upload datasets to Firestore with event bus integration.
    """
    def __init__(self, data_dir: str):
        # Initialize Event Bus
        self.event_bus = InMemoryEventBus()
        self.storage_service = LocalDatasetFirestore(data_dir=data_dir)
        self.claim_extraction_module = GeminiClaimExtraction()
        self.add_storage_event_subscriptions()
        self.claim_extraction_module.set_eventbus(self.event_bus)

    
    def add_storage_event_subscriptions(self):
        """Subscribe event handlers to the event bus."""
        handlers = {
            "claim_extraction.completed": self.claim_extraction_module.on_claim_extraction_completed,
            "dataset.upload_completed": self.claim_extraction_module.run,
            "dataset.upload_failed": self.storage_service.on_upload_failed,
        }
        
        for topic, handler in handlers.items():
            self.event_bus.subscribe(topic, handler)

    def run(self, id: str):

        """
        For a certain ID of a local dutaset start the upload to Firestore.
        """

        print("\n" + "="*70)
        print("DATASET CLOUD PIPELINE: Upload Dataset to Firestore")
        print("="*70 + "\n")
        
        
        
        # Start upload process
        response =  self.storage_service.upload(id=id)
        if response["response"] is not None:
            print(f"Pipeline completed successfully for dataset ID: {id}")
            self.event_bus.publish("dataset.upload_completed", {"id": response["id"], "data": response["data"]})
            
        else:
            print(f"Pipeline failed for dataset ID: {id}")
            self.event_bus.publish("dataset.upload_failed", {"id": response["id"]})
        
        self.storage_service.close()



            