# Wix Integration Guide for ROSIE AGENT E

## Overview
Once all neighborhoods have been processed with AI-generated alt text and tooltips in Pipedrive, we'll sync these descriptions to the Wix website.

## Integration Approach

### Option 1: Wix REST API (Recommended)
- Use Wix's `/contacts`, `/items`, or `/products` API endpoints
- Sync generated alt_text and tooltip_text from Pipedrive → Wix
- Requires: Wix API key + Site ID

### Option 2: Make.com Workflow
- Create scenario: "Sync Pipedrive → Wix"
- Trigger after each Pipedrive update
- Wix HTTP module posts data to Wix API

## Setup Requirements

1. **Wix API Credentials**
   - API Key (from Wix Dev Console)
   - Site ID (from Wix account)
   - Authorization: Bearer token in headers

2. **Pipedrive Data to Sync**
   - Deal ID
   - Property address
   - Alt Text Pic 1-10
   - Tooltip Pic 1-10

3. **Wix Data Target**
   - Wix CMS Collections / Database Items
   - Or: Wix Stores Products
   - Custom fields for alt_text and tooltip_text

## Neighborhoods to Sync

Once processing is complete, sync all neighborhoods to Wix:
1. **Brooklyn | Queens** (15 deals, 97 images) ✅ Complete
2. **Midtown East** (13 deals, 112 images) ✅ Complete  
3. **West Village** (8 deals, 68 images) ✅ Complete
4. **Upper East Side** (TBD deals, TBD images) 🔄 In Progress
5. **Upper West Side** (TBD deals, TBD images) ⏳ Pending Upload & Processing

## Next Steps

**Phase 1 - Wait for Upper East Side completion**
1. Confirm Upper East Side finishes in Pipedrive
2. Upload Upper West Side image URLs to Pipedrive (if not done)
3. Process Upper West Side through Make.com

**Phase 2 - Wix Sync**
1. Get Wix API credentials (Site ID + API Key)
2. Identify Wix data structure (which collection/products to update)
3. Implement sync logic via Make.com or Flask endpoint
4. Test sync on one neighborhood first, then batch sync all neighborhoods
