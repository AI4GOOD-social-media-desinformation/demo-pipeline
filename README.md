# demo-pipeline
The goal of this repo is to quickly create and evaluate modules in different pipeline setups

## Setup

```bash
pip install -e .
gcloud auth application-default login

```

**Add yout  GOOGLE_API_KEY to .env file for using google services**

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
- **Returns**: `{"message": "Test received successfully", "data": <received_data>}`
- **Useful for**: Testing webhook payload structure without triggering full pipeline

### `POST /testPipeline`
- **Purpose**: Manual pipeline testing endpoint
- **Behavior**: Runs DatasetCloudPipeline on hardcoded video ID `C5tBt-0IEEy`
- **Returns**: `{"message": "Pipeline request received successfully"}`
- **Note**: For testing only; modify the code to test different videos

## Running the Flask Server

Start the Flask application:

```bash
python app.py
```

The server runs on `http://localhost:5000`

To expose it publicly for Instagram webhooks, use Cloudflare Tunnel:

```bash
cloudflared tunnel --url http://localhost:5000
```

This will provide a public HTTPS URL to configure in the Instagram Developer Console.

## Running Examples

This project includes example scripts demonstrating how to use the pipeline modules. All examples are located in the `examples/` directory.

### Prerequisites

Before running any examples, ensure you have:
1. Installed the package: `pip install -e .`
2. Set up Google Cloud authentication: `gcloud auth application-default login`
3. Added your `GOOGLE_API_KEY` to a `.env` file for Google services

### Example 1: Claim Extraction Pipeline

**File**: `examples/test_claim_extraction_pipeline.py`

**Description**: Tests the claim extraction module by processing videos and extracting claims using Google Gemini AI. This example demonstrates how to use the GeminiClaimExtraction module to analyze video content and extract factual claims.

**Usage**:
```bash
cd examples
python test_claim_extraction_pipeline.py
```

**What it does**:
- Loads video files from the `data/socialdf/socialdf_vids` directory
- Processes videos with specified IDs (default: `DELIpWZN3tU`)
- Extracts claims from video content using the Gemini API
- Saves results to Firestore database
- Displays processing progress and status updates

**Expected Output**:
```
================================================================================
Testing ClaimExtraction Pipeline
================================================================================

[Processing] Video ID: DELIpWZN3tU
--------------------------------------------------------------------------------
[Claim Extraction] Processing video...
[Result] Claims extracted and saved to Firestore
Video ID: DELIpWZN3tU - Status: Success

================================================================================
Pipeline Test Complete
================================================================================
```

### Example 2: Dataset Cloud Pipeline

**File**: `examples/pipeline_saving_dataset_cloud.py`

**Description**: Demonstrates how to run the full pipeline that processes videos and saves the dataset to cloud storage (Firestore). This is the main production pipeline for processing multiple videos in batch.

**Usage**:
```bash
cd examples
python pipeline_saving_dataset_cloud.py
```

**What it does**:
- Loads video data from the `data/socialdf/socialdf_vids` directory
- Processes multiple videos in sequence (default IDs: `C5tBt-0IEEy`, `C96nZIGIb_v`)
- Saves processed data and claims to Firestore
- Handles event-driven architecture through the InMemoryEventBus
- Logs all processing stages

**Expected Output**:
```
Dataset Cloud Pipeline Processing:
Processing video ID: C5tBt-0IEEy
  - Video loaded successfully
  - Claims extracted: [list of claims]
  - Data saved to Firestore
Processing video ID: C96nZIGIb_v
  - Video loaded successfully
  - Claims extracted: [list of claims]
  - Data saved to Firestore
Pipeline completed successfully
```

### Running Custom Examples

To run examples with your own video data:

1. Place your videos in `data/socialdf/socialdf_vids/vids/<video_id>/` directory
2. Modify the `ids` list in the example script with your video IDs
3. Run the example script as shown above

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