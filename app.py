import os
import threading
from flask import Flask, request, jsonify
from dotenv import load_dotenv
from src.pipelines.DatasetCloudPipeline import DatasetCloudPipeline

# Import the Instagram pipeline
from src.pipelines.InstagramWebhookPipeline import InstagramWebhookPipeline

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
VERIFY_TOKEN = os.getenv("INSTAGRAM_VERIFY_TOKEN", "my_secure_verify_token")
INSTAGRAM_ACCESS_TOKEN = os.getenv("INSTAGRAM_ACCESS_TOKEN")


def run_pipeline_task(permalink):
    """
    Wrapper to run the pipeline in a separate thread to avoid 
    blocking the webhook response.
    """
    try:
        print(f"Starting pipeline for: {permalink}")
        # Initialize and run the Instagram pipeline
        pipeline = InstagramWebhookPipeline(permalink)
        pipeline.run()
        print(f"Pipeline finished for: {permalink}")
    except Exception as e:
        print(f"Pipeline error: {e}")


def get_permalink_from_id(media_id, access_token):
    """
    Fetch the permalink from Instagram Graph API using media_id.
    """
    import requests
    
    url = f"https://graph.facebook.com/v18.0/{media_id}?fields=permalink&access_token={access_token}"
    try:
        response = requests.get(url)
        if response.status_code == 200:
            return response.json().get('permalink')
        else:
            print(f"Error fetching permalink: {response.status_code} - {response.text}")
    except Exception as e:
        print(f"Exception fetching permalink: {e}")
    return None


@app.route("/")
def hello_world():
    return "<p>Hello, World!</p>"


@app.route('/webhook', methods=['GET'])
def verify_webhook():
    """
    Verifies the webhook subscription.
    Instagram sends a GET request with a challenge string.
    """
    mode = request.args.get('hub.mode')
    token = request.args.get('hub.verify_token')
    challenge = request.args.get('hub.challenge')

    if mode == 'subscribe' and token == VERIFY_TOKEN:
        print("Webhook verified successfully!")
        return challenge, 200
    
    print("Webhook verification failed!")
    return 'Forbidden', 403


@app.route('/webhook', methods=['POST'])
def receive_webhook():
    """
    Receives the webhook payload.
    Extracts the permalink and triggers the local pipeline.
    """
    data = request.json
    print(f"Received webhook payload: {data}")
    return jsonify({'message': 'Webhook received successfully'}), 200
    
    # Check if this is an object from Instagram
    # if data.get('object') == 'instagram':
    #     for entry in data.get('entry', []):
    #         for change in entry.get('changes', []):
    #             # The payload structure depends on the subscription field
    #             value = change.get('value', {})
                
    #             # Try to get permalink directly
    #             permalink = value.get('permalink_url') or value.get('permalink')
                
    #             # If no permalink, try to get media_id and fetch it
    #             if not permalink:
    #                 media_id = value.get('media_id') or value.get('id')
    #                 if media_id and INSTAGRAM_ACCESS_TOKEN:
    #                     permalink = get_permalink_from_id(media_id, INSTAGRAM_ACCESS_TOKEN)
                
    #             if permalink:
    #                 print(f"Processing permalink: {permalink}")
    #                 # Run processing asynchronously so we can return 200 OK immediately
    #                 thread = threading.Thread(target=run_pipeline_task, args=(permalink,))
    #                 thread.start()
    #             else:
    #                 print("No permalink found in webhook payload")

    #     return 'EVENT_RECEIVED', 200
    
    # return 'Not Found', 404

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
    print(f"Verify Token: {VERIFY_TOKEN}")
    print(f"Access Token Configured: {'Yes' if INSTAGRAM_ACCESS_TOKEN else 'No'}")
    print("Starting Flask server on port 5000...")
    print("="*70)
    
    # Run specifically on port 5000 (default for many tunnels)
    app.run(host='0.0.0.0', port=5000, debug=True)
