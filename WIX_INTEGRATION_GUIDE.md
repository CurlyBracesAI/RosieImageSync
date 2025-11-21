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

## Next Steps

When Upper East Side finishes:
1. Confirm all neighborhoods complete in Pipedrive
2. Get Wix API credentials
3. Identify Wix data structure (which Wix collection/products to update)
4. Implement sync logic via Make.com or Flask endpoint
