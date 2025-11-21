# ROSIE AGENT E - Image Intelligence & Sync API

## Overview
ROSIE AGENT E is a Flask-based microservice API designed for image processing within the CurlyBraces.ai multi-agent system. Its primary purpose is to centralize the generation of alt text and tooltips for real estate property images by integrating AWS Rekognition for label detection and OpenAI for descriptive text generation. The service automatically updates Pipedrive deal fields with the generated content, streamlining the image intelligence workflow for real estate deals. The project aims to enhance accessibility and data enrichment for property listings, initially focusing on Brooklyn and Queens markets, with ambitions for broader integration, including Wix.

## User Preferences
- Incremental development approach
- Wait for explicit instructions before implementing business logic
- Follow exact naming conventions (bp_rosie_images, /rosie-images)
- Use existing app structure patterns
- **Replit Secrets Location**: Use the **workspace search bar** (top of workspace) and search for "Secrets". This is the most reliable method. In the Secrets panel, use the "App Secrets" tab to link Account Secrets or add new secrets. Account Secrets must be explicitly linked to each project to be available as environment variables.

## System Architecture

### Project Structure
The application is structured as a Flask microservice with a clear separation of concerns.
- `main.py`: Entry point for the Flask application, responsible for blueprint registration.
- `routes/rosie_images.py`: Contains the core logic for image processing, exposed via the `bp_rosie_images` Blueprint.

### UI/UX Decisions
Descriptions are factual, varied in structure, and avoid promotional language. Alt text is concise (8-14 words) for screen readers, while tooltip text is more descriptive (20-30 words) but still lean and factual.

### Technical Implementations & Feature Specifications
- **API Endpoint**: A `POST /rosie-images` endpoint processes image URLs.
- **Input Handling**: Accepts both JSON and `form-urlencoded` data formats.
- **Image Processing Pipeline**:
    1. Fetches image bytes from provided URLs.
    2. Utilizes AWS Rekognition to detect labels from images.
    3. Leverages OpenAI (gpt-4o-mini) to generate alt text and tooltip text based on detected labels and neighborhood context.
    4. Automatically extracts picture numbers (1-10) from image filenames in URLs.
- **Pipedrive Integration**: Automatically updates "Deal - Alt Text Pic 1-10" and "Deal - Tooltip Pic 1-10" custom fields in Pipedrive.
- **Smart Caching & Idempotency**: Before processing, the system checks Pipedrive fields; if already populated, it skips processing to save costs and ensures idempotency for retries. A `force_refresh` parameter allows overriding this.
- **Neighborhood Parsing**: Extracts clean neighborhood names from image file paths for contextual description generation.
- **OpenAI Prompt Optimization**: Prompts are optimized for commercial professional office spaces, ensuring relevant and non-promotional descriptions.
- **S3 Folder Structure Standardization**: All S3 image folders are standardized to use numeric Pipedrive deal IDs for consistent processing.

## External Dependencies

- **AWS Rekognition**: Used for image label detection. Requires `AWS_ACCESS_KEY_ID`, `AWS_SECRET_ACCESS_KEY`, and `AWS_REGION`.
- **OpenAI API**: Used for generating alt text and tooltip descriptions. Requires `OPENAI_API_KEY`.
- **Pipedrive**: The CRM system where generated alt text and tooltips are updated. Integration relies on Pipedrive's API for updating deal custom fields.
- **Make.com**: An integration platform used to orchestrate the workflow, triggering the API with image data from Pipedrive.

## Recent Changes

- **2025-11-20**: West Village URL upload to Pipedrive
  - Successfully uploaded 68 image URLs across all 8 West Village deals
  - S3 folder: "UnSQ | Gren'Villl. AWS S3"
  - Deal 6301 required manual update (S3 folder had trailing space: "6301 " vs "6301")
  - All images numbered 1-10 with original filenames preserved
  - URL pattern: `https://neighborhood-listing-images.s3.amazonaws.com/Neighborhood%20Listing%20Images/UnSQ%20%7C%20Gren%27Villl.%20AWS%20S3/{deal_id}/{number}.jpg`
  - All URLs verified accessible (HTTP 200 response)
  - 100% success rate (8/8 deals)
  - Created verification documentation: WEST_VILLAGE_UPLOAD_VERIFICATION.md

- **2025-11-20**: Midtown East URL upload to Pipedrive
  - Successfully uploaded 96 image URLs across 13 Midtown East deals to Pipedrive
  - Used corrected S3 folder: "Midtown East | Gr Cent AWS S3"
  - All images numbered 1-10 with original filenames preserved
  - URL pattern: `https://neighborhood-listing-images.s3.amazonaws.com/Neighborhood%20Listing%20Images/Midtown%20East%20%7C%20Gr%20Cent%20AWS%20S3/{deal_id}/{number}.jpg`
  - All URLs verified accessible (HTTP 200 response)
  - Zero errors during upload, all 13 deals updated successfully
  - Created verification documentation: MIDTOWN_EAST_UPLOAD_VERIFICATION.md

- **2025-11-20**: Brooklyn | Queens ready for Make.com AI processing with force_refresh
  - Updated workflow guide to require force_refresh=true for Brooklyn | Queens
  - Existing descriptions are old profile content and need to be overwritten
  - All 97 images will get fresh AI-generated alt text and tooltip descriptions
  - Cost estimate: ~$0.30 for complete refresh of all Brooklyn | Queens images
  - Verified full AI pipeline: AWS Rekognition → OpenAI → Pipedrive update working correctly
  - Created comprehensive Make.com workflow guide: BROOKLYN_QUEENS_MAKE_WORKFLOW_GUIDE.md
  - Guide includes 3 scenario options with force_refresh=true configuration
  - Ready to process all 97 Brooklyn | Queens images through Make.com

- **2025-11-20**: Brooklyn | Queens URL upload to Pipedrive
  - Successfully uploaded 97 image URLs across 15 Brooklyn | Queens deals to Pipedrive
  - Created `update_pipedrive_urls.py` script to bulk update "Picture 1-10" fields
  - Fixed critical URL encoding bug with `quote(key, safe="/")` to preserve path separators
  - All images numbered 1-10 with original filenames preserved in S3 folder "Brooklyn | Queens AWS S3"
  - URL pattern: `https://neighborhood-listing-images.s3.amazonaws.com/Neighborhood%20Listing%20Images/Brooklyn%20%7C%20Queens%20AWS%20S3/{deal_id}/{number}.jpg`
  - All URLs verified accessible (HTTP 200 response)
  - Zero errors during upload, all 15 deals updated successfully
  - Created verification documentation: BROOKLYN_QUEENS_UPLOAD_VERIFICATION.md

- **2025-11-21**: Midtown East Make.com AI Processing - Complete (13/13 deals)
  - Successfully processed all 13 Midtown East deals with AI-generated alt text and tooltips
  - Processed deals: 1925, 2573, 2859, 2908, 3419, 4181, 4339, 4359, 4634, 4789, 4806, 5482, 6041
  - Total images processed: 112 across 13 deals
  - Run completed in 21.9 minutes (~11.7 seconds per image average)
  - All descriptions use address-based content (e.g., "Furnished office at 59 East 54th Street")
  - AWS S3 folder contained exactly 13 files - processing complete

- **2025-11-21**: Upper East Side Make.com AI Processing - IN PROGRESS
  - S3 folder: Upper_East_Side_AWS_S3/
  - Processing confirmed deals: 2639 (341 East 79th Street (2nd)), 3206 (1751 Second Ave (91st))+ 
  - Current status: Successfully updating Pipedrive with address-based alt text and tooltips
  - Processing speed: ~5 seconds per image (optimized performance)
  - All descriptions reference actual addresses from Pipedrive custom field
  - Monitoring: Processing continues smoothly, no errors detected