# ROSIE AGENT E - Image Intelligence & Sync API

## Overview
ROSIE AGENT E is a Flask-based microservice API for image processing within the CurlyBraces.ai multi-agent system. Its core function is to generate alt text and tooltips for real estate property images using AWS Rekognition for label detection and OpenAI for descriptive text. The service automatically updates Pipedrive deal fields with this generated content, streamlining image intelligence for real estate transactions. The project aims to enhance accessibility and data enrichment for property listings, with initial focus on Brooklyn and Queens, and future plans for broader integrations like Wix.

## User Preferences
- Incremental development approach
- Wait for explicit instructions before implementing business logic
- Follow exact naming conventions (bp_rosie_images, /rosie-images)
- Use existing app structure patterns
- **Replit Secrets Location**: Use the **workspace search bar** (top of workspace) and search for "Secrets". This is the most reliable method. In the Secrets panel, use the "App Secrets" tab to link Account Secrets or add new secrets. Account Secrets must be explicitly linked to each project to be available as environment variables.

## System Architecture

### Project Structure
The application is a Flask microservice with a clear separation of concerns:
- `main.py`: Application entry point and blueprint registration.
- `routes/rosie_images.py`: Contains core image processing logic via `bp_rosie_images` Blueprint.

### UI/UX Decisions
Alt text is concise (8-14 words) for screen readers, while tooltip text is more descriptive (20-30 words). Descriptions are factual, varied, and non-promotional.

### Technical Implementations & Feature Specifications
- **API Endpoint**: `POST /rosie-images` for processing image URLs.
- **Input Handling**: Supports JSON and `form-urlencoded` data.
- **Image Processing Pipeline**:
    1. Fetches image bytes from URLs.
    2. Uses AWS Rekognition for label detection.
    3. Employs OpenAI (gpt-4o-mini) to generate alt text and tooltips based on labels and neighborhood context.
    4. Extracts picture numbers (1-10) from image filenames in URLs.
- **Pipedrive Integration**: Updates "Deal - Alt Text Pic 1-10" and "Deal - Tooltip Pic 1-10" custom fields.
- **Smart Caching & Idempotency**: Checks Pipedrive for existing content before processing; `force_refresh` parameter allows override.
- **Neighborhood Parsing**: Extracts clean neighborhood names from image paths for contextual descriptions.
- **OpenAI Prompt Optimization**: Prompts are tailored for commercial professional office spaces.
- **S3 Folder Structure Standardization**: S3 image folders use numeric Pipedrive deal IDs.

## External Dependencies

- **AWS Rekognition**: Used for image label detection.
- **OpenAI API**: Used for generating alt text and tooltip descriptions.
- **Pipedrive**: CRM system for updating deal custom fields.
- **Make.com**: Integration platform for orchestrating workflow and triggering the API.

## Recent Updates & Fixes

### 2025-11-24: Root Cause Fixed - Missing Picture URLs Issue Resolved ✅

**Problem:** Deals 3365, 3371, 3460, 3977 were in Wix but missing picture URLs.

**Root Cause:** Pipedrive's filter API endpoint doesn't return custom fields (Picture 1-10, Alt Text, Tooltips) in the response.

**Solution Implemented:**
- Modified `_fetch_pipedrive_deals_filtered()` to:
  1. Use filter to get deal IDs
  2. Fetch each deal individually (includes ALL custom fields)
  3. Return complete deals with pictures, alt text, tooltips
- Modified `_fetch_pipedrive_deals_by_neighborhood()` with same logic
- Tested: All 15 UES deals synced successfully with custom fields included

**Result:** This issue will NOT happen again. All future syncs automatically include custom fields by fetching deals individually.