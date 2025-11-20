# ROSIE AGENT E - Image Intelligence & Sync API

## Overview
Flask-based microservice API for ROSIE AGENT E, part of the CurlyBraces.ai multi-agent system. This service centralizes image processing for real estate deals, integrating AWS Rekognition and OpenAI to generate alt text and tooltips for property images.

## Current Status (November 20, 2025)
**Phase**: Production Ready with Pipedrive Auto-Update & Smart Caching
- Full AI processing pipeline operational: fetch → AWS Rekognition labels → OpenAI descriptions → Pipedrive update
- All AWS, OpenAI, and Pipedrive credentials configured and active
- OpenAI prompt optimized for commercial professional office spaces
- Alt text: 8-14 words, short and functional for screen readers
- Tooltip text: 20-30 words, descriptive but lean and factual
- Descriptions are factual, varied structure, no promotional language
- Neighborhood parsing: extracts clean name from full file paths
- Make.com integration successfully configured and tested (100+ successful requests)
- Endpoint accepts both JSON and form-urlencoded data formats
- **Pipedrive Integration**: Automatically updates "Deal - Alt Text Pic 1-10" and "Deal - Tooltip Pic 1-10" fields
- **Smart Caching**: Checks Pipedrive before processing - skips already-populated slots to save costs
- **Auto-Detection**: Extracts picture number (1-10) from URL filename automatically
- **Idempotent**: Safe to retry/restart Make.com scenarios without reprocessing completed images
- **Brooklyn | Queens Images**: All 15 deals with 97 total images uploaded to "Brooklyn | Queens AWS S3" folder in S3 and synced to Pipedrive Picture 1-10 fields
- Processing all neighborhoods: Upper West Side, Upper East Side, West Village, Midtown East, Brooklyn, Queens
- Ready for Wix integration (next phase)

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
  "image_urls": "string or array",
  "picture_number": "integer (1-10, optional)",
  "force_refresh": "boolean (optional, default: false)"
}
```

**Parameters:**
- `deal_id` - Pipedrive deal ID (numeric, required). Example: "2560"
- `neighborhood` - Neighborhood name or full path (required)
- `image_urls` - Single URL or array of URLs (required)
- `picture_number` - Specific picture slot (1-10) to update. Auto-detected from filename if not provided (optional)
- `force_refresh` - Set to `true` to bypass cache and regenerate descriptions even if slot is populated. Use this to replace poor quality existing text or when images are updated (optional)

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
- **Replit Secrets Location**: Use the **workspace search bar** (top of workspace) and search for "Secrets". This is the most reliable method. In the Secrets panel, use the "App Secrets" tab to link Account Secrets or add new secrets. Account Secrets must be explicitly linked to each project to be available as environment variables.

## Recent Changes
- **2025-11-20**: Brooklyn | Queens URL upload to Pipedrive
  - Successfully uploaded 97 image URLs across 15 Brooklyn | Queens deals to Pipedrive
  - Created `update_pipedrive_urls.py` script to bulk update "Picture 1-10" fields
  - Script dynamically fetches Pipedrive field keys and maps S3 images to correct slots
  - All images numbered 1-10 with original filenames preserved in S3 folder "Brooklyn | Queens AWS S3"
  - URLs use proper encoding with `quote(key, safe="/")` to preserve path separators
  - URL pattern: `https://neighborhood-listing-images.s3.amazonaws.com/Neighborhood%20Listing%20Images/Brooklyn%20%7C%20Queens%20AWS%20S3/{deal_id}/{number}.jpg`
  - Zero errors during upload, all 15 deals updated successfully with accessible URLs
  - Greenwich Village (West Village) folder upload next on roadmap
  - Fixed LSP warnings in routes/rosie_images.py with type ignore comments and variable initialization

- **2025-11-18**: S3 image file renaming for auto-detection
  - Renamed ALL image files in West Village and Brooklyn | Queens to sequential numbers
  - West Village: 15 deals, 200+ images renamed (1.jpg, 2.jpeg, 3.pdf, etc.)
  - Brooklyn | Queens: 11 deals, 100+ images renamed
  - Files now follow pattern: 1.jpeg, 2.pdf, 3.jpg, 4.webp (preserves extensions)
  - API auto-detects picture_number from filename for smart caching
  - Smart caching now works: checks Pipedrive slots before processing
  - No Make.com counter needed - filenames already sequential

- **2025-11-18**: S3 folder structure standardization completed
  - Successfully restructured ALL S3 neighborhoods to use numeric deal IDs (matching UWS/UES format)
  - Brooklyn | Queens: Renamed 11 address-based folders to numeric deal IDs, deleted 4 dead folders
  - West Village (UnSQ:Gren'Villl.): Renamed 15 address-based folders to numeric deal IDs
  - Used Pipedrive CSV export as master data source for address → deal_id mapping
  - Created restructure_s3_with_csv.py script with fuzzy matching algorithm (0.7+ confidence threshold)
  - Manual overrides applied for edge cases (172 Crown Heights, 80 5th Ave, 150 W 25th)
  - Removed temporary address lookup logic from API (no longer needed)
  - ALL neighborhoods now follow same folder naming convention: Pipedrive deal ID only
  - Ready for consistent Make.com automation across all neighborhoods

- **2025-11-18**: Pipedrive integration with smart caching
  - Implemented automatic Pipedrive updates: API now updates "Deal - Alt Text Pic 1-10" and "Deal - Tooltip Pic 1-10" fields directly
  - Added smart caching: checks Pipedrive before processing each image to skip already-populated slots
  - Automatic picture number detection from URL filenames (e.g., ".../2560/1.jpeg" → Picture 1)
  - Makes API idempotent: safe to restart Make.com scenarios without wasting costs on reprocessing
  - Each retry skips completed images (returns cached data in <1 second, saves ~$0.001 per skip)
  - Tested with multiple deals across neighborhoods (Upper West Side, Upper East Side, etc.)
  - Successfully processed 60+ images with automatic Pipedrive field population

- **2025-11-18**: OpenAI prompt optimization and neighborhood parsing
  - Updated OpenAI prompt to focus on commercial professional office spaces (not residential)
  - Optimized description lengths: alt_text 8-14 words, tooltip_text 20-30 words
  - Added structural variation examples to avoid repetitive descriptions
  - Enforced factual, descriptive tone with no promotional/flowery language
  - Added neighborhood path parsing to extract clean names from "Neighborhood Listing Images/Upper West Side/2560/1.jpg" → "Upper West Side"
  - Instructions emphasize using detected Rekognition labels as primary driver for descriptions
  - All credentials (AWS Rekognition, OpenAI) now active and operational
  - Tested with real Make.com data and confirmed accurate, varied descriptions
  
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
