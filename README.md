# demo-pipeline
The goal of this repo is to quickly create and evaluate modules in different pipeline setups

## Setup

```bash
pip install -e .
gcloud auth application-default login

```

**Add your GOOGLE_API_KEY to .env file for using google services**

**Add INSTAGRAM_ACCESS_TOKEN to .env file to enable sending Instagram Direct Messages**

This will install the required dependencies and the package in editable mode.

## Folder Structure
- `src/`: Main source code directory
  - `dataloaders/`: Data loading utilities and validation loaders
  - `eventbus/`: Event bus implementation for event-driven architecture
  - `modules/`: Core pipeline modules (e.g., GeminiClaimExtraction)
  - `pipelines/`: Pipeline implementations (e.g., DatasetCloudPipeline)
  - `storage/`: Storage services for local and cloud data management
  - `utils/`: Utility functions and helpers
- `data/`: Contains datasets and data processing
  - `socialdf/`: Social media deepfake dataset
    - `socialdf_script_vids/`: Scripts and processed videos with descriptions
    - `socialdf_vids/`: Processed social media videos
    - `val_socialdf/`: Validation dataset
  - `*.csv`: Dataset metadata files
- `examples/`: Example scripts demonstrating pipeline usage
- `experiments/`: Experimental notebooks and scripts for testing and validating hypotheses
- `config.py`: Configuration settings
- `pyproject.toml`: Project metadata and dependencies

## API Endpoints

The Flask application provides the following endpoints:

### `GET /`
- **Purpose**: Home/health check endpoint
- **Returns**: Simple "Hello, World!" message

### `GET /privacy-policy`
- **Purpose**: Renders privacy policy page
- **Returns**: HTML content from `templates/privacy_policy.html`

### `GET /webhook`
- **Purpose**: Instagram webhook verification
- **Query Parameters**:
  - `hub.mode`: Should be `subscribe`
  - `hub.verify_token`: Must match `INSTAGRAM_VERIFY_TOKEN` environment variable
  - `hub.challenge`: Challenge string to echo back
- **Returns**: Challenge string if token matches, otherwise "Forbidden"
- **Used by**: Instagram to verify webhook subscription during setup

### `POST /webhook`
- **Purpose**: Receives Instagram Direct Message webhook events
- **Behavior**:
  - Validates event is from Instagram
  - Extracts messaging events with video attachments
  - Skips echo messages and messages without attachments
  - Extracts sender ID, video URL, reel ID, and video title
  - Prevents duplicate processing using message ID (idempotency)
  - Saves event to Firestore database
  - Runs DirectMessagePipeline asynchronously in background thread
  - Returns immediate 200 response to Instagram
- **See**: [WEBHOOK_SETUP.md](WEBHOOK_SETUP.md) for detailed webhook configuration and payload structure

### `POST /test`
- **Purpose**: Debug endpoint for testing webhook payloads
- **Behavior**: Echoes received JSON to console, returns success response
- **Returns**: `{"analysisMessage": "Test received successfully", "data": <received_data>}`
- **Useful for**: Testing webhook payload structure without triggering full pipeline

### `POST /testPipeline`
- **Purpose**: Manual pipeline testing endpoint
- **Behavior**: Runs DatasetCloudPipeline on hardcoded video ID `C5tBt-0IEEy`
- **Returns**: `{"analysisMessage": "Pipeline request received successfully"}`
- **Note**: For testing only; modify the code to test different videos

## Running the Flask Server

Start the Flask application:

```bash
python app.py
```

The server runs on `http://localhost:5000`

To expose it publicly for Instagram webhooks, use Cloudflare Tunnel:

```bash
cloudflared tunnel run --token $CLOUDFARE_TUNNELING_TOKEN```
```
This will provide a public HTTPS URL to configure in the Instagram Developer Console.


### Prerequisites

Before running any examples, ensure you have:
1. Installed the package: `pip install -e .`
2. Set up Google Cloud authentication: `gcloud auth application-default login`
3. Added your `GOOGLE_API_KEY` to a `.env` file for Google services
4. Added your `INSTAGRAM_ACCESS_TOKEN` to the `.env` file to enable sending Instagram Direct Messages
5. Added your `INSTAGRAM_VERIFY_TOKEN` to the `.env` file for webhook verification
6. Added your `CLOUDFARE_TUNNELING_TOKEN` to the `.env` file for Cloudflare Tunnel

### Direct Message Pipeline


**What it does**:
- Downloads Instagram reels from the provided video URL
- Extracts claims from the video content using Gemini API
- Runs deepfake detection on the video
- Performs disinformation analysis on detected claims
- Sends processing status messages to the user via Instagram DM
- Sends final analysis results back to the user via Instagram DM
- Filters and provides related news articles
- Uses event-driven architecture to coordinate all modules

**Event Flow**:
1. `reels_download.completed` → triggers claim extraction
2. `claim_extraction.completed` → triggers deepfake detection
3. `deepfake_detection.completed` → triggers disinformation analysis
4. `disinformation_analysis.completed` → triggers analysis message sender
5. `analysis_message_sender.completed` → triggers related news filtering

**Required Environment Variables**:
- `GOOGLE_API_KEY`: For Gemini claim extraction
- `INSTAGRAM_ACCESS_TOKEN`: For sending direct messages back to users

**Expected Output**:
```
======================================================================
DATASET CLOUD PIPELINE: Upload Dataset to Firestore
======================================================================

[Processing] Sending processing message to user...
[Download] Downloading reel from URL...
[Claim Extraction] Processing video...
[Deepfake Detection] Analyzing video for deepfake indicators...
[Disinformation Analysis] Analyzing claims...
[Messaging] Sending analysis results to user via Instagram DM...
[News Filter] Finding related news articles...
Pipeline completed successfully
```

### Troubleshooting

- **Google API Key Error**: Ensure `GOOGLE_API_KEY` is set in your `.env` file
- **Firebase Credentials Error**: Run `gcloud auth application-default login` and ensure your GCP project is configured
- **Video Not Found**: Verify that video files exist in the correct directory structure
- **Firestore Connection Error**: Check that your GCP project has Firestore enabled

## Cloudflared tunneling

Expose the local service through Cloudflare Tunnel to the public endpoint https://ehfake.caiorhoden-apps.work/.

1. Install the Cloudflare CLI (Linux example): `sudo apt-get update && sudo apt-get install cloudflared`
2. Set the tunnel token environment variable (store securely, e.g., in your shell profile or secret manager): `export CLOUDFARE_TUNNELING_TOKEN=<tunnel_token>`
3. Start the tunnel (runs until interrupted): `cloudflared tunnel run --token $CLOUDFARE_TUNNELING_TOKEN`
4. Keep your app running locally (e.g., `flask run`) so the tunnel can forward traffic to it.

Notes:
- The token is provided by Cloudflare when you create the tunnel; rotate it if compromised.
- The command above uses the token-based mode (no local config file required).