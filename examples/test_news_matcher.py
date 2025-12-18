

import firebase_admin
import uuid
from firebase_admin import firestore
import os

from src.modules.NewsMatcher import NewsMatcher
from src.eventbus.InMemoryEventBus import InMemoryEventBus
from src.utils.dataclasses import FirestoreObject

GOOGLE_API_KEY = os.getenv("GOOGLE_API_KEY")



def main():
    """Test ClaimExtraction with multiple videos."""

    matcher = NewsMatcher(
        similarity_threshold=0,
        top_n=2,
        max_results=10,
        recency_days=180
    )

    query = "Lula aprova um novo decreto que reduz preço nos alimentos"
    # Run claim extraction
    results = matcher.run(query)
    print(results)

        
        
    
    print("\n" + "=" * 80)
    print("Pipeline Test Complete")
    print("=" * 80)


if __name__ == "__main__":
    main()