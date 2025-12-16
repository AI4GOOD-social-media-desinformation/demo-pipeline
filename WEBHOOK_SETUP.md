# Instagram Webhook Setup

This guide explains how to set up and run the Instagram webhook receiver.

## Overview

The Flask application receives webhooks from Instagram when users send Direct Messages containing Instagram reel/video attachments. It extracts the video information, saves it to Firestore, and processes it through your local pipeline asynchronously.

## Prerequisites

1. **Instagram Business Account** connected to a Facebook App
2. **Meta Developer Account** with an app configured
3. **Cloudflare Tunnel** (or similar tunneling service like ngrok)
4. **Python 3.8+** installed

## Setup Instructions

### 1. Install Dependencies

```bash
pip install -e .
```

### 2. Configure Environment Variables

Create or update your `.env` file with the following:

```bash
# Required: Token to verify Instagram webhook subscription
INSTAGRAM_VERIFY_TOKEN=my_secure_verify_token

# Required: Instagram Graph API access token (for fetching permalinks from media IDs)
INSTAGRAM_ACCESS_TOKEN=your_instagram_access_token_here

# Optional: Other API keys you may need
GOOGLE_API_KEY=your_google_api_key_here
```

**How to get the Instagram Access Token:**
1. Go to [Meta for Developers](https://developers.facebook.com/)
2. Select your app
3. Go to Instagram > Basic Display or Instagram Graph API
4. Generate a User Access Token with appropriate permissions
5. Copy the token to your `.env` file

### 3. Start the Flask Application

```bash
python app.py
```

The server will start on `http://localhost:5000`

### 4. Set Up Cloudflare Tunnel

In a separate terminal, start the Cloudflare tunnel:

```bash
cloudflared tunnel --url http://localhost:5000
```

This will output a public URL like: `https://xyz.trycloudflare.com`

**Alternative:** Use ngrok if you prefer:
```bash
ngrok http 5000
```

### 5. Configure Instagram Webhooks in Meta Developer Portal

1. Go to your App Dashboard at [developers.facebook.com](https://developers.facebook.com/)
2. Navigate to **Instagram** > **Webhooks**
3. Click **Edit Subscription**
4. Configure the following:
   - **Callback URL**: Your tunnel URL + `/webhook` (e.g., `https://xyz.trycloudflare.com/webhook`)
   - **Verify Token**: The same token you set in `INSTAGRAM_VERIFY_TOKEN` (e.g., `my_secure_verify_token`)
5. Click **Verify and Save**
6. Subscribe to the fields you want to receive:
   - `comments` - For new comments on your posts
   - `mentions` - For mentions in stories/posts
   - `live_comments` - For live video comments
   - etc.

## Endpoints

### GET /webhook
- **Purpose**: Webhook verification endpoint
- **Used by**: Instagram to verify your webhook subscription
- **Query Parameters**:
  - `hub.mode`: Should be `subscribe`
  - `hub.verify_token`: Must match `INSTAGRAM_VERIFY_TOKEN` environment variable
  - `hub.challenge`: Challenge string to echo back
- **Returns**: The challenge string if verification succeeds, otherwise "Forbidden"
- **Example**: `GET /webhook?hub.mode=subscribe&hub.verify_token=my_secure_verify_token&hub.challenge=test_challenge`

### POST /webhook
- **Purpose**: Receives webhook events from Instagram Direct Messages
- **Payload**: JSON webhook data from Instagram with messaging events
- **Behavior**: 
  - Validates the event is from Instagram (`object == 'instagram'`)
  - Extracts Direct Message events from the payload
  - Skips echo messages and messages without attachments
  - Processes the first attachment from each message
  - Extracts: sender ID, attachment URL, reel video ID, and video title
  - Uses message ID (`mid`) or reel video ID for idempotency (prevents duplicate processing)
  - Saves event data to Firestore database
  - Runs the DirectMessagePipeline asynchronously in a background thread
  - Returns immediate 200 "EVENT_RECEIVED" response to Instagram
- **Expected Attachment Payload**:
  ```json
  {
    "url": "https://www.instagram.com/reel/ABC123/",
    "reel_video_id": "video_id_here",
    "title": "Video title/description"
  }
  ```

### POST /test
- **Purpose**: Simple test endpoint for debugging webhook payloads
- **Behavior**: Echoes received JSON data to console and returns success response
- **Used for**: Testing webhook structure without triggering full pipeline
- **Returns**: `{"message": "Test received successfully", "data": <received_data>}`

### POST /testPipeline
- **Purpose**: Manual pipeline testing endpoint
- **Behavior**: Runs the DatasetCloudPipeline on a hardcoded video ID
- **Note**: Currently hardcoded to process video ID `C5tBt-0IEEy` from `data/socialdf/socialdf_vids`
- **Returns**: `{"message": "Pipeline request received successfully"}`

### GET /
- **Purpose**: Home/health check endpoint
- **Returns**: Simple "Hello, World!" message

### GET /privacy-policy
- **Purpose**: Renders privacy policy page
- **Returns**: HTML privacy policy from `templates/privacy_policy.html`

## How It Works

1. **DM Webhook Received**: Instagram sends POST request to `/webhook` with Direct Message event
2. **Validate Event**: App confirms event is from Instagram and contains messaging data
3. **Extract Attachment**: App extracts the first attachment from the DM (video URL, reel ID, title)
4. **Idempotency Check**: Uses message ID to prevent duplicate processing of same message
5. **Save to Firestore**: Creates a FirestoreObject document with the extracted data
6. **Async Processing**: Runs DirectMessagePipeline in background thread to avoid timeout
7. **Immediate Response**: App returns 200 "EVENT_RECEIVED" to Instagram immediately
8. **Pipeline Execution**: 
   - Processes the video data
   - Can extract claims, analyze content, store results, etc.

## Webhook Payload Structure

Instagram Direct Message webhooks send data in this format:

```json
{
  "object": "instagram",
  "entry": [
    {
      "id": "instagram-account-id",
      "messaging": [
        {
          "sender": {
            "id": "sender_user_id"
          },
          "message": {
            "mid": "message_id",
            "is_echo": false,
            "attachments": [
              {
                "type": "share",
                "payload": {
                  "url": "https://www.instagram.com/reel/ABC123/",
                  "reel_video_id": "video_id_here",
                  "title": "Video title"
                }
              }
            ]
          }
        }
      ]
    }
  ]
}
```

**Key Fields**:
- `sender.id`: Instagram user ID of the person who sent the DM
- `message.mid`: Unique message ID used for idempotency
- `message.attachments[].payload.url`: Full Instagram URL of the shared video
- `message.attachments[].payload.reel_video_id`: Instagram reel/video ID
- `message.attachments[].payload.title`: Caption/title of the shared video
- `message.is_echo`: Set to `true` for messages echoed back by Instagram (skipped by the webhook handler)

## Customizing the Pipeline

Edit [`src/pipelines/DirectMessagePipeline.py`](src/pipelines/DirectMessagePipeline.py) to customize processing:

The DirectMessagePipeline receives event data containing:
- `userId`: Instagram user ID who sent the DM
- `videoUrl`: Full Instagram URL of the shared reel
- `videoId`: Instagram reel video ID
- `videoText`: Video title/caption

You can customize the pipeline to:
- Download and process the video content
- Extract claims using GeminiClaimExtraction
- Analyze video metadata
- Store additional results in Firestore
- Send notifications
- etc.

## Troubleshooting

### Webhook Verification Fails
- Ensure `INSTAGRAM_VERIFY_TOKEN` in `.env` matches the token in Meta Developer Portal
- Check Flask app is running and accessible via tunnel
- Verify tunnel URL is correct and includes `/webhook` path

### No Attachments in Payload
- Ensure users are sharing video reels/posts with attachments
- Check that the webhook subscription includes messaging events
- Plain text DMs without attachments are skipped by the handler

### Pipeline Errors
- Check Flask console for error messages
- Verify download utility works with Instagram URLs
- Ensure all required environment variables are set

## Security Considerations

1. **Verify Token**: Keep your verify token secure and don't commit it to version control
2. **HTTPS**: Always use HTTPS tunnels for production
3. **Signature Validation**: Consider adding Instagram's signature validation for production
4. **Rate Limiting**: Implement rate limiting to prevent abuse
5. **Error Handling**: Add robust error handling and logging

## Testing

### Test Webhook Verification
```bash
curl "http://localhost:5000/webhook?hub.mode=subscribe&hub.verify_token=my_secure_verify_token&hub.challenge=test_challenge"
```
Expected response: `test_challenge`

### Test Webhook with Sample Payload
```bash
curl -X POST http://localhost:5000/webhook \
  -H "Content-Type: application/json" \
  -d '{
    "object": "instagram",
    "entry": [{"messaging": [{"sender": {"id": "12345"}, "message": {"mid": "msg_id_123", "attachments": [{"payload": {"url": "https://www.instagram.com/reel/ABC123/", "reel_video_id": "reel_123", "title": "Test Video"}}]}}]}]
  }'
```
Expected response: `EVENT_RECEIVED` with 200 status

### Test Plain POST Endpoint
For debugging webhook structure without triggering the full pipeline:
```bash
curl -X POST http://localhost:5000/test \
  -H "Content-Type: application/json" \
  -d '{"test": "data"}'
```
Expected response: `{"message": "Test received successfully", "data": {"test": "data"}}`

### Home/Status Check
```bash
curl http://localhost:5000/
```
Expected response: `<p>Hello, World!</p>`
