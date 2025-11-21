# Remediation Plan for Deals 3367 & 4188

## Step 1: Verify Deal IDs Have URLs Uploaded

Confirm in Pipedrive that deals 3367 & 4188 have all 10 image URLs in "Picture 1-10" fields.
If missing, run your URL upload script first.

## Step 2: Create Separate Make.com Scenarios

### Option A (Recommended - Zero Risk)
**Create 2 new Make.com scenarios:**

**Scenario: "ROSIE: Deal 3367 Only"**
- Target just deal 3367
- Estimated runtime: 2-3 minutes
- Safety margin: Completes in <5 minutes

**Scenario: "ROSIE: Deal 4188 Only"**
- Target just deal 4188  
- Estimated runtime: 2-3 minutes
- Safety margin: Completes in <5 minutes

### Option B (If Dealing with Large Batches Going Forward)
Modify your Make.com workflow to:
1. Limit images per batch to 12 max
2. Include a pause/delay between batches (Make.com throttling)
3. Add run-time monitoring in your Flask API

## Step 3: Monitor Processing

For each scenario, watch for:
- API response times (target: <15 seconds per image)
- Pipedrive update confirmations
- No "ModuleTimeoutError" in Make.com logs

## Step 4: Future Prevention

Going forward, when adding new neighborhoods:
1. **Calculate batch size**: `batch_images = 40000 / avg_seconds_per_image`
2. **Set Make.com timeout**: 30 minutes per scenario (10 min safety margin from 40 min limit)
3. **Split if needed**: If total images > batch_images, split into multiple scenarios

## Test Calculation

- Average per image: 11.7 seconds
- Make.com limit: 40 minutes (2400 seconds)
- Max safe images per scenario: 2400 / 11.7 = **~205 images**
- BUT: To stay under 30-minute comfort zone, limit to **~150 images per scenario**

This gives you flexibility for deals with 8-10 images each = **15-19 deals per scenario comfortably**.

Since you're only processing 2 more deals, splitting them is overkill - process together = ~25 minutes max, safe!
