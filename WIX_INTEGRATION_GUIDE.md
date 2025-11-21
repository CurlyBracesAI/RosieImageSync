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

## Neighborhoods Ready for Wix Sync

All neighborhoods uploaded & processing:
1. **Brooklyn | Queens** (15 deals, 97 images) ✅ Complete
2. **Midtown East** (13 deals, 112 images) ✅ Complete  
3. **West Village** (8 deals, 68 images) ✅ Complete
4. **Upper East Side** 🔄 In Progress
5. **Upper West Side** ✅ URLs in Pipedrive (ready to process)

## Implementation Steps

**Once Upper East Side completes:**
1. Confirm all neighborhoods have alt_text and tooltip_text in Pipedrive
2. Get Wix API credentials (Site ID + API Key)
3. Identify Wix data structure (collection/products to update)
4. Implement Wix sync via Make.com or Flask endpoint
5. Test sync on one neighborhood, then batch sync all 5 neighborhoods
