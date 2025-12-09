
from src.eventbus.InMemoryEventBus import InMemoryEventBus
from src.storage.LoadDatasetFirestore import LocalDatasetFirestore
import asyncio


class DatasetCloudPipeline:
    """
    Pipeline to upload datasets to GCP Cloud SQL with event bus integration.
    """
    def __init__(self, data_dir: str):
        # Initialize Event Bus
        self.event_bus = InMemoryEventBus()
        self.storage_service = LocalDatasetFirestore(data_dir=data_dir)
        self.add_storage_event_subscriptions()

    
    def add_storage_event_subscriptions(self):
        """Subscribe event handlers to the event bus."""
        handlers = {
            "dataset.upload_completed": self.storage_service.on_upload_completed,
            "dataset.upload_failed": self.storage_service.on_upload_failed,
        }
        
        for topic, handler in handlers.items():
            self.event_bus.subscribe(topic, handler)

    def run(self, id: str):

        """
        For a certain ID of a local dutaset start the upload to GCP Cloud SQL.
        """

        print("\n" + "="*70)
        print("DATASET CLOUD PIPELINE: Upload Dataset to GCP Cloud SQL")
        print("="*70 + "\n")
        
        
        
        # Start upload process
        response =  self.storage_service.upload(id=id)
        if response["response"] is not None:
            print(f"Pipeline completed successfully for dataset ID: {id}")
        else:
            print(f"Pipeline failed for dataset ID: {id}")
            self.event_bus.publish("dataset.upload_failed", {"id": response["id"]})