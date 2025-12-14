# Instagram Webhook Setup

This guide explains how to set up and run the Instagram webhook receiver.

## Overview

The Flask application receives webhooks from Instagram when new posts/reels are created, downloads the content, and processes it through your local pipeline.

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
- **Returns**: The challenge string if verification succeeds

### POST /webhook
- **Purpose**: Receives webhook events from Instagram
- **Payload**: JSON data containing post/reel information
- **Behavior**: 
  - Extracts permalink from payload
  - If only media_id is present, fetches permalink from Graph API
  - Starts pipeline processing in background thread
  - Returns immediate 200 response to Instagram

### GET /health
- **Purpose**: Health check endpoint
- **Returns**: JSON status indicating the service is running

## How It Works

1. **Webhook Received**: Instagram sends POST request to `/webhook`
2. **Extract Permalink**: App extracts the permalink URL or fetches it using media_id
3. **Async Processing**: Pipeline runs in background thread to avoid timeout
4. **Immediate Response**: App returns 200 OK to Instagram immediately
5. **Pipeline Execution**: 
   - Downloads the Instagram content
   - Processes it through your custom pipeline
   - Can extract claims, analyze video, store results, etc.

## Webhook Payload Structure

Instagram webhooks typically send data in this format:

```json
{
  "object": "instagram",
  "entry": [
    {
      "id": "instagram-account-id",
      "time": 1234567890,
      "changes": [
        {
          "field": "mentions",
          "value": {
            "media_id": "123456789",
            "permalink": "https://www.instagram.com/p/ABC123/"
          }
        }
      ]
    }
  ]
}
```

**Note**: Some webhook fields only provide `media_id`, requiring a Graph API call to get the permalink.

## Customizing the Pipeline

Edit [`src/pipelines/InstagramWebhookPipeline.py`](src/pipelines/InstagramWebhookPipeline.py) to customize processing:

```python
def process_content(self, video_path: str):
    # Add your custom logic here:
    # - Extract claims using GeminiClaimExtraction
    # - Analyze video metadata
    # - Store in Firestore
    # - Send notifications
    # etc.
```

## Troubleshooting

### Webhook Verification Fails
- Ensure `INSTAGRAM_VERIFY_TOKEN` in `.env` matches the token in Meta Developer Portal
- Check Flask app is running and accessible via tunnel
- Verify tunnel URL is correct and includes `/webhook` path

### No Permalink in Payload
- Ensure `INSTAGRAM_ACCESS_TOKEN` is set in `.env`
- Check the token has appropriate permissions
- Verify the webhook subscription field you selected provides the data you need

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

Test the webhook verification:
```bash
curl "http://localhost:5000/webhook?hub.mode=subscribe&hub.verify_token=my_secure_verify_token&hub.challenge=test_challenge"
```

Expected response: `test_challenge`

Test health endpoint:
```bash
curl http://localhost:5000/health
```

Expected response: `{"status": "healthy", "service": "Instagram Webhook Receiver"}`
