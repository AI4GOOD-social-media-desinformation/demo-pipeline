import os
import threading
from flask import Flask, request, jsonify, render_template
from dotenv import load_dotenv
from src.utils.dataclasses import FirestoreObject
import firebase_admin
from firebase_admin import firestore
import uuid

# Import the DM  Pipeline
from src.pipelines.DirectMessagePipeline import DirectMessagePipeline
# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_VERIFY_TOKEN")
INSTAGRAM_VERIFY_TOKEN = os.getenv("INSTAGRAM_VERIFY_TOKEN")

firebase_admin.initialize_app()
pipeline = DirectMessagePipeline(saving_dir="data/requests")


def save_event_to_firestore(sender_id, url, reel_video_id, text, doc_id=None):
    """
    Saves the Instagram webhook event data to Firestore.
    
    Args:
        sender_id: The Instagram user ID who sent the message
        url: The URL of the shared video
        reel_video_id: The Instagram reel video ID
        text: The title/text of the video
    
    Returns:
        request_id: The UUID of the created Firestore document
    """
    event_data = FirestoreObject(
        userId=sender_id,
        videoUrl=url,
        videoId=reel_video_id,
        videoPath="",
        videoText=text,
        claim="",
        context="",
        message=""
    )

    db = firestore.Client(project="gen-lang-client-0915299548", database="ai4good")
    request_id = doc_id or str(uuid.uuid4())
    doc_ref = db.collection("requests").document(request_id)

    # Idempotency: skip if this request was already processed.
    if doc_ref.get().exists:
        print(f"Request {request_id} already exists; skipping pipeline run.")
        db.close()
        return None

    doc_ref.set(event_data.__dict__)
    event_data = {"id": request_id, "data": event_data.__dict__}
    db.close()
    
    return event_data


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.route('/privacy-policy')
def privacy_policy():
    """Renders the privacy policy page."""
    return render_template('privacy_policy.html')

@app.route('/webhook', methods=['POST', 'GET'])
def receive_webhook():
    """
    Receives the webhook payload.
    Extracts the permalink and triggers the local pipeline.
    """

    # 1. Verification Logic (GET)
    if request.method == 'GET':
        mode = request.args.get('hub.mode')
        token = request.args.get('hub.verify_token')
        challenge = request.args.get('hub.challenge')

        if mode == 'subscribe' and token == INSTAGRAM_VERIFY_TOKEN:
            return challenge, 200
        return 'Forbidden', 403
    
    else:  # 2. Event Handling Logic (POST)
        print("Received POST webhook event")
        data = request.json
        # Verify it is an Instagram event
        if data.get('object') == 'instagram':
            
            for entry in data.get('entry', []):
                # Handle messaging events (DMs)
                for message_event in entry.get('messaging', []):
                    if 'message' not in message_event:
                        continue

                    message = message_event.get('message', {})
                    if message.get('is_echo'):
                        continue  # Skip echoes sent by Instagram

                    sender_id = message_event.get('sender', {}).get('id')
                    attachments = message.get('attachments') or []
                    if not attachments:
                        print("No attachments found in the message; skipping.")
                        continue

                    url = None
                    reel_video_id = None
                    text = ''
                    for attachment in attachments:
                        payload = attachment.get('payload', {})
                        url = payload.get('url')
                        reel_video_id = payload.get('reel_video_id')
                        text = payload.get('title', '')
                        break  # Only process the first attachment

                    if not url:
                        print("Attachment payload missing url; skipping event.")
                        continue

                    # Use stable IDs to prevent duplicate processing for the same reel/message.
                    request_id = message.get('mid') or reel_video_id or str(uuid.uuid4())
                    event_data = save_event_to_firestore(sender_id, url, reel_video_id, text, doc_id=request_id)
                    print(event_data)
                    if not event_data:
                        continue

                    # Run heavy pipeline work off the request thread so webhook responds fast.
                    threading.Thread(target=pipeline.run, args=(event_data,), daemon=True).start()

            return 'EVENT_RECEIVED', 200
        
        return 'Not Found', 404
    
  

@app.route("/testPipeline", methods=['POST'])
def test_pipeline():
    id = "C5tBt-0IEEy"
    pipeline = DatasetCloudPipeline(data_dir="data/socialdf/socialdf_vids")
    pipeline.run(id)
    return jsonify({'message': 'Pipeline request received successfully'}), 200



@app.route('/test', methods=['POST'])
def test_endpoint():
    """
    Simple test endpoint that prints received data to terminal.
    """
    data = request.json
    print("\n" + "="*70)
    print("TEST ENDPOINT - POST Request Received!")
    print("="*70)
    print(f"Received data: {data}")
    print("="*70 + "\n")
    
    return jsonify({'message': 'Test received successfully', 'data': data}), 200


if __name__ == '__main__':
    print("="*70)
    print("Instagram Webhook Receiver")
    print("="*70)
    print("Starting Flask server on port 5000...")
    print("="*70)
    
    # Run specifically on port 5000 (default for many tunnels)
    app.run(host='0.0.0.0', port=5000, debug=True)
