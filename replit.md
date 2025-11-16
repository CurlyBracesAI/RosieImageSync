# ROSIE AGENT E - Image Intelligence & Sync API

## Overview
Flask-based microservice API for ROSIE AGENT E, part of the CurlyBraces.ai multi-agent system. This service centralizes image processing for real estate deals, integrating AWS Rekognition and OpenAI to generate alt text and tooltips for property images.

## Current Status (November 16, 2025)
**Phase**: Helper Functions Ready
- Basic Flask application structure created
- Blueprint skeleton in place for `/rosie-images` endpoint
- Input validation complete: accepts deal_id, neighborhood, image_urls
- Returns structured response with image_count
- Client initialization for AWS Rekognition and OpenAI (conditional)
- Helper function `_fetch_image_bytes(url)` added for downloading images
- No image processing logic implemented yet

## Project Architecture

### Structure
```
/
├── main.py                    # Flask app entry point with Blueprint registration
├── routes/
│   └── rosie_images.py       # Blueprint: bp_rosie_images with /rosie-images POST route
└── replit.md                 # This file
```

### Current Endpoints
- `GET /` - Returns API welcome message
- `POST /rosie-images` - Accepts deal_id, neighborhood, and image_urls; validates input and returns status with image count

### Blueprint Details
- **Name**: `bp_rosie_images`
- **Route**: `/rosie-images`
- **Method**: POST
- **Current Response**: `{"status": "ready"}`

## Next Phase Implementation (Not Yet Built)
The following features are planned but not yet implemented:

### Input Schema (Planned)
```json
{
  "deal_id": "string",
  "neighborhood": "string",
  "image_urls": ["s3://url1", "s3://url2"]
}
```

### Output Schema (Planned)
```json
{
  "status": "ok",
  "deal_id": "1234",
  "images": [
    {
      "url": "...",
      "rekognition_labels": [...],
      "alt_text": "...",
      "tooltip_text": "..."
    }
  ]
}
```

### Planned Components
1. AWS Rekognition integration via boto3
2. OpenAI integration for text generation
3. S3 image fetching
4. Error handling and validation
5. Environment variables: AWS_ACCESS_KEY_ID, AWS_SECRET_ACCESS_KEY, AWS_REGION, OPENAI_API_KEY

## Integration with Make.com
This API will replace parts of the existing Make.com scenario that currently handles:
- S3 image retrieval
- AWS Rekognition label detection
- OpenAI text generation
- JSON formatting

The endpoint will be called from Make.com, which will then update Pipedrive and push to Wix.

## User Preferences
- Incremental development approach
- Wait for explicit instructions before implementing business logic
- Follow exact naming conventions (bp_rosie_images, /rosie-images)
- Use existing app structure patterns

## Recent Changes
- **2025-11-16**: Helper function added
  - Created `_fetch_image_bytes(url)` helper function
  - Uses requests library to download images from URLs
  - Returns raw bytes on success, None on failure
  - Includes 30-second timeout and basic error handling
  - Route behavior remains unchanged
  
- **2025-11-16**: Input validation implementation
  - Added JSON input parsing with request.get_json(silent=True)
  - Implemented validation for required fields: deal_id, neighborhood, image_urls
  - Return error response for missing/invalid fields
  - Return success response with deal_id, neighborhood, and image_count
  - Conditional client initialization for OpenAI and AWS Rekognition
  - Handles empty image_urls arrays (returns count: 0)
  - All test cases pass: valid payloads, missing fields, invalid JSON
  
- **2025-11-15**: Initial project setup
  - Created Flask application skeleton
  - Added bp_rosie_images Blueprint with stub endpoint
  - Configured workflow to run on port 5000
  - Verified endpoint accessibility
