from src.modules.ProcessingMessageSender import ProcessingMessageSender
from src.eventbus.InMemoryEventBus import InMemoryEventBus


def main():
    """Test ClaimExtraction with multiple videos."""

    sender = ProcessingMessageSender()
    sender.set_eventbus(InMemoryEventBus())


    # Find video file

    # Create event data
    event_data = {
        "id": f"testing-send-confirmation",
        "data": {
            "userId": "1909996093229343",
        }
    }
    
    # Run claim extraction
    sender.run(event_data)

        
        
    
    print("\n" + "=" * 80)
    print("Pipeline Test Complete")
    print("=" * 80)


if __name__ == "__main__":
    main()
