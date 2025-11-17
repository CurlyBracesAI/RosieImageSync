# ROSIE AGENT E - Image Intelligence & Sync API

## Overview
Flask-based microservice API for ROSIE AGENT E, part of the CurlyBraces.ai multi-agent system. This service centralizes image processing for real estate deals, integrating AWS Rekognition and OpenAI to generate alt text and tooltips for property images.

## Current Status (November 17, 2025)
**Phase**: Make.com Integration Complete & Production Ready
- Full processing pipeline operational: fetch → detect labels → generate descriptions
- Make.com integration successfully configured and tested (10+ successful requests)
- Endpoint accepts both JSON and form-urlencoded data formats
- Input validation: accepts deal_id, neighborhood, image_urls
- Returns structured JSON response with image_count and images array
- Each image object includes: url, status, bytes_fetched, labels, alt_text, tooltip_text
- AWS Rekognition and OpenAI client initialization (conditional on credentials)
- All helper functions integrated and operational
- Successfully processing real S3 URLs from Upper West Side neighborhood
- Awaiting AWS and OpenAI credentials for live label detection and text generation
- Raw image bytes not stored in response (memory efficient)

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
- `POST /rosie-images` - Main processing endpoint

### Blueprint Details
- **Name**: `bp_rosie_images`
- **Route**: `/rosie-images`
- **Method**: POST
- **Input Formats**: JSON or form-urlencoded
- **Public URL**: `https://262b6272-a512-43bd-b89f-dd45acce6b62-00-1ggs85wl8sclp.spock.replit.dev/rosie-images`

### Make.com Integration Configuration
**HTTP Module Settings:**
- **URL**: `https://262b6272-a512-43bd-b89f-dd45acce6b62-00-1ggs85wl8sclp.spock.replit.dev/rosie-images`
- **Method**: `POST`
- **Body Type**: `application/x-www-form-urlencoded`
- **Parse response**: `Yes`
- **Fields**:
  - `deal_id` → `{{72. image_id}}`
  - `neighborhood` → `{{20. File name}}`
  - `image_urls` → `{{30. image_url}}`

## Input/Output Schemas

### Input Schema
Accepts both JSON and form-urlencoded formats:
```json
{
  "deal_id": "string",
  "neighborhood": "string",
  "image_urls": "string or array"
}
```

### Output Schema
```json
{
  "status": "ok",
  "deal_id": "1234",
  "neighborhood": "Upper West Side",
  "image_count": 1,
  "images": [
    {
      "url": "https://...",
      "status": "processed",
      "bytes_fetched": true,
      "labels": ["Building", "Architecture", ...],
      "alt_text": "Modern apartment building...",
      "tooltip_text": "Luxury residence in..."
    }
  ]
}
```

### Environment Variables
Required for full functionality:
- `AWS_ACCESS_KEY_ID` - AWS credentials for Rekognition
- `AWS_SECRET_ACCESS_KEY` - AWS credentials for Rekognition  
- `AWS_REGION` - AWS region (e.g., us-east-2)
- `OPENAI_API_KEY` - OpenAI API key for text generation

Without credentials, the API still functions but returns empty arrays for labels and empty strings for alt_text/tooltip_text.

## User Preferences
- Incremental development approach
- Wait for explicit instructions before implementing business logic
- Follow exact naming conventions (bp_rosie_images, /rosie-images)
- Use existing app structure patterns

## Recent Changes
- **2025-11-17**: Make.com integration debugging and form data support
  - Added fallback to parse form-urlencoded data when JSON parsing fails
  - Handles both JSON and form data formats seamlessly
  - Auto-converts image_urls from string to array format
  - Successfully tested with 10+ real requests from Make.com
  - All requests returning HTTP 200 with proper data parsing
  - Make.com configuration documented: application/x-www-form-urlencoded with three fields
  - Removed debug logging after successful integration verification
  - API fully operational and processing real S3 URLs from Upper West Side deals

- **2025-11-16**: Description generation integration
  - Modified loop to call `_generate_descriptions(neighborhood, labels, url)` after detecting labels
  - Added `alt_text` and `tooltip_text` fields to each image object
  - Both fields return empty strings when OpenAI credentials not configured
  - All existing fields preserved: url, status, bytes_fetched, labels
  - Full processing pipeline now complete: fetch → detect labels → generate descriptions
  - Response structure: status, deal_id, neighborhood, image_count, images[{url, status, bytes_fetched, labels, alt_text, tooltip_text}]
  - Verified with multiple test scenarios (valid/invalid URLs, mixed cases)
  
- **2025-11-16**: Label detection integration
  - Modified loop to call `_detect_labels(image_bytes)` after fetching bytes
  - Added `labels` array field to each image object
  - Labels returned as array of detected label names (empty when AWS not configured)
  - All existing fields preserved: url, status, bytes_fetched
  - Helper function _generate_descriptions remains unused
  - Response structure: status, deal_id, neighborhood, image_count, images[{url, status, bytes_fetched, labels}]
  - Verified with multiple test scenarios (valid/invalid URLs, mixed cases)
  
- **2025-11-16**: Image fetching integration
  - Modified loop to call `_fetch_image_bytes(url)` for each image URL
  - Added `bytes_fetched` boolean field to each image object (true/false based on fetch success)
  - No raw bytes stored in JSON response (only boolean flag)
  - Verified with comprehensive testing: valid URLs return true, HTTP errors (403/404/500) and invalid domains return false
  - Helper functions _detect_labels and _generate_descriptions remain unused
  - Response structure: status, deal_id, neighborhood, image_count, images[{url, status, bytes_fetched}]
  
- **2025-11-16**: Output structure preparation
  - Modified `/rosie-images` route to build `processed` list after validation
  - Loop over `image_urls` and append {"url": url, "status": "pending"} for each
  - Updated response to include "images": processed array
  - Helper functions remain unused (structure-only step)
  - Response now returns: status, deal_id, neighborhood, image_count, images
  - Verified with test payloads (3 URLs and empty array)
  
- **2025-11-16**: OpenAI description generation helper added
  - Created `_generate_descriptions(neighborhood, labels, url)` helper function
  - Builds prompt using neighborhood, detected labels, and image URL
  - Calls OpenAI gpt-4o-mini with JSON response format
  - Returns dict with alt_text and tooltip_text keys
  - Includes comprehensive try/except error handling
  - Returns empty strings on any error (never raises exceptions)
  - Route behavior remains unchanged
  
- **2025-11-16**: Label detection helper added
  - Created `_detect_labels(image_bytes)` helper function
  - Uses AWS Rekognition to detect labels with MaxLabels=10, MinConfidence=75
  - Returns simple Python list of label names
  - Includes early None check and try/except error handling
  - Returns empty list on any error (never raises exceptions)
  - Route behavior remains unchanged
  
- **2025-11-16**: Image fetching helper added
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
