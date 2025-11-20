# Brooklyn | Queens - Make.com AI Processing Workflow Guide
**Date**: November 20, 2025

## Overview
Process all 97 Brooklyn | Queens images through the ROSIE AGENT E API to generate AI-powered alt text and tooltip descriptions, then automatically update Pipedrive.

**IMPORTANT**: Brooklyn | Queens requires `force_refresh=true` to overwrite existing old profile descriptions with fresh AI-generated content.

## API Endpoint
**URL**: `https://262b6272-a512-43bd-b89f-dd45acce6b62-00-1ggs85wl8sclp.spock.replit.dev/rosie-images`
**Method**: POST
**Status**: ✅ Running and tested

## Processing Pipeline
```
S3 Image → AWS Rekognition (labels) → OpenAI (descriptions) → Pipedrive Update
```

### What Gets Generated:
- **Alt Text**: 8-14 words, screen reader optimized
- **Tooltip Text**: 20-30 words, descriptive and factual
- **Auto-updates**: Pipedrive "Deal - Alt Text Pic 1-10" and "Deal - Tooltip Pic 1-10" fields

## Make.com Module Configuration

### HTTP Request Settings:
```
URL: https://262b6272-a512-43bd-b89f-dd45acce6b62-00-1ggs85wl8sclp.spock.replit.dev/rosie-images
Method: POST
Body Type: application/json (recommended) or application/x-www-form-urlencoded
Parse Response: Yes
```

### Required Fields (JSON format):
```json
{
  "deal_id": "{{pipedrive_deal_id}}",
  "neighborhood": "Brooklyn | Queens",
  "image_urls": ["{{picture_url}}"],
  "force_refresh": true
}
```

**IMPORTANT**: `force_refresh: true` is **required** for Brooklyn | Queens to overwrite existing old descriptions with fresh AI-generated content.

### Field Mapping Example:
```
deal_id → {{pipedrive.deal_id}}
neighborhood → "Brooklyn | Queens" (hardcoded)
image_urls → [{{pipedrive.picture_1}}] (or picture_2, picture_3, etc.)
force_refresh → true (hardcoded - overwrites existing descriptions)
```

### Force Refresh Parameter:
- `force_refresh: true` - **REQUIRED for Brooklyn | Queens** to replace old profile descriptions
  - Regenerates descriptions even if already populated
  - Ensures all 97 images get fresh AI-generated alt text and tooltips
  - Cost: ~$0.30 for all images (minimal investment for quality improvement)

## Smart Caching Behavior

### Automatic Skip Logic:
- API checks Pipedrive before processing each image
- If alt_text AND tooltip_text are already populated → returns cached data (< 1 sec)
- If either field is empty → processes image (~3-5 sec)
- Result: Idempotent and cost-efficient (saves ~$0.001 per cached image)

### Example Response (Cached):
```json
{
  "status": "ok",
  "cached": true,
  "deal_id": 2561,
  "picture_number": 1,
  "pipedrive_updated": false,
  "images": [{
    "status": "cached",
    "alt_text": "Office space with chair, plant, and lamp",
    "tooltip_text": "Interior of a professional office...",
    "labels": []
  }]
}
```

### Example Response (Fresh Processing):
```json
{
  "status": "ok",
  "deal_id": 3246,
  "picture_number": 1,
  "pipedrive_updated": true,
  "images": [{
    "status": "processed",
    "alt_text": "Office space with chair, plant, and lamp",
    "tooltip_text": "Interior of a professional office...",
    "labels": ["Furniture", "Chair", "Plant", "Lamp", ...]
  }]
}
```

## Make.com Scenario Design Options

### Option 1: Single Loop (Recommended for Testing)
```
1. List Deals (Pipedrive filter: Brooklyn | Queens neighborhood)
2. Iterator: Loop through Picture 1-10 fields
3. Filter: Only process if picture_url exists
4. HTTP Request: Call /rosie-images
5. Router: Log success/failure
```

**Pros**: Simple, easy to debug  
**Cons**: Slower (sequential processing)

### Option 2: Parallel Processing (Production)
```
1. List Deals (Pipedrive filter: Brooklyn | Queens neighborhood)
2. Array Aggregator: Collect all picture URLs with deal_ids
3. Flow Control: Split into batches of 10
4. HTTP Request: Call /rosie-images (parallel)
5. Data Store: Track completion status
```

**Pros**: Much faster (parallel API calls)  
**Cons**: More complex setup

### Option 3: Single Deal Test (Start Here)
```
1. Get Deal (hardcoded deal_id: 3246)
2. Set Variables:
   - deal_id: 3246
   - neighborhood: "Brooklyn | Queens"
   - image_urls: [{{picture_1}}]
   - force_refresh: true
3. HTTP Request: Call /rosie-images
4. Logger: Output response
```

**Pros**: Perfect for initial testing  
**Cons**: Manual - one deal at a time

## Processing Checklist

### Before Running:
- [ ] Verify API is accessible (test with curl/Postman)
- [ ] Confirm all 15 Brooklyn | Queens deals have Picture 1-10 URLs populated
- [ ] Test with 1-2 deals first to verify Make.com configuration
- [ ] Check AWS/OpenAI credits are sufficient

### During Processing:
- [ ] Monitor Make.com execution logs for errors
- [ ] Check API logs in Replit for any failures
- [ ] Spot-check Pipedrive to verify alt text/tooltip updates
- [ ] Track processing time and costs

### After Completion:
- [ ] Verify all 97 images have alt text + tooltip in Pipedrive
- [ ] Review quality of generated descriptions
- [ ] Document any images that need `force_refresh=true`
- [ ] Update project documentation with completion status

## Expected Results
- **Total Images**: 97 across 15 deals
- **Processing Time**: ~5-10 minutes (with caching)
- **Cost Estimate**: 
  - Rekognition: ~$0.001/image × 97 = $0.097
  - OpenAI: ~$0.002/image × 97 = $0.194
  - Total: ~$0.30 (first run, less with caching)

## Troubleshooting

### Error: "Missing required field: deal_id"
→ Check Make.com field mapping, ensure deal_id is passed as string

### Error: "Invalid image URL"
→ Verify Picture URLs in Pipedrive are properly formatted S3 URLs

### Response: "cached": true but need fresh descriptions
→ Add `"force_refresh": true` to request body

### API returns 500 error
→ Check Replit logs for Python errors, verify AWS/OpenAI credentials

### Pipedrive not updating
→ Verify Pipedrive API token is valid, check field names match exactly

## Next Neighborhoods
After Brooklyn | Queens success:
1. Greenwich Village (West Village) - ~15 deals
2. Upper West Side - already processed
3. Upper East Side - already processed
4. Other neighborhoods as needed

## Support
- API Logs: Replit console (flask-app workflow)
- Pipedrive Fields: "Deal - Alt Text Pic 1-10", "Deal - Tooltip Pic 1-10"
- Smart caching reduces cost on retries/restarts
