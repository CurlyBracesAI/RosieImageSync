# Midtown East Part 2 - Make.com Workflow Guide

## Overview
This guide handles the remaining **2 Midtown East deals** that hit the 40-minute Make.com timeout:
- **Deal 6148** (confirmed timeout)
- **Deal [15th ID]** (needs verification from Pipedrive)

## Issue Context
The first Make.com scenario processed 13/15 Midtown East deals successfully before timing out on deal 6148.

## Setup Steps

### 1. Identify Missing Deal ID
Check your Midtown East deals in Pipedrive to confirm:
- Processed: 1925, 2573, 2859, 2908, 3419, 4181, 4339, 4359, 4634, 4789, 4806, 5482, 6041
- Missing (confirm from Pipedrive): **6148** + **[one more deal ID]**

### 2. Create New Make.com Scenario (Part 2)
1. In Make.com, create a **new scenario** named: `ROSIE: Midtown East Part 2 (Final 2)`
2. **Trigger**: Manual or Pipedrive (your choice)
3. **HTTP POST Module** configuration:
   - **URL**: `https://262b6272-a512-43bd-b89f-dd45acce6b62-00-1ggs85wl8sclp.spock.replit.dev/rosie-images`
   - **Method**: POST
   - **Body type**: `application/x-www-form-urlencoded`

### 3. Request Body (Map these fields)
```
deal_id: [deal_id from trigger or static input]
neighborhood: Midtown East
image_urls: [urls from Pipedrive]
force_refresh: true
```

### 4. Test with Deal 6148
First, run **only deal 6148** to verify it processes without timeout.

### 5. Then Process the 15th Deal
Once 6148 succeeds, add the 15th deal to complete Midtown East.

## Expected Outcome
✅ All 15 Midtown East deals processed
✅ All picture slots 1-10 updated in Pipedrive with AI-generated descriptions
✅ All alt_text and tooltip_text populated with address-based content

## Troubleshooting
- If the scenario still times out at 40 minutes, consider processing just 1 deal per scenario to stay well under the limit
- The API processes ~3 images per second, so 9-10 images per scenario = ~30-40 seconds processing time + Pipedrive updates should stay under 40 min limit
