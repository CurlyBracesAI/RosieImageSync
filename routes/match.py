from flask import Blueprint, jsonify, request
import os
import re
import json
from openai import OpenAI

bp_match = Blueprint("match", __name__)

def _get_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)


def _parse_aggregated_partners(partners_raw):
    """
    Parse partners data from Make.com aggregator.
    Can handle:
    - JSON array of partner objects
    - Text string with partner data (aggregated format)
    - Single partner object
    - Dict with 'text' key containing aggregated text
    """
    # If it's a dict with 'text' key, extract the text and parse it
    if isinstance(partners_raw, dict) and 'text' in partners_raw:
        print(f"[MATCH DEBUG] Found 'text' key in partners, extracting...")
        text_content = partners_raw['text']
        print(f"[MATCH DEBUG] Text content length: {len(text_content) if text_content else 0}")
        print(f"[MATCH DEBUG] Text preview: {str(text_content)[:500]}")
        return _parse_aggregated_partners(text_content)
    
    # If it's already a list of dicts, return as-is
    if isinstance(partners_raw, list):
        if all(isinstance(p, dict) for p in partners_raw):
            return partners_raw
        # List of strings - try to parse each
        parsed = []
        for item in partners_raw:
            if isinstance(item, dict):
                parsed.append(item)
            elif isinstance(item, str):
                try:
                    parsed.append(json.loads(item))
                except:
                    # Try to extract deal info from text
                    partner = _parse_partner_text(item)
                    if partner:
                        parsed.append(partner)
        return parsed
    
    # If it's a single dict (but not with 'text' key), wrap in list
    if isinstance(partners_raw, dict):
        return [partners_raw]
    
    # If it's a string, try to parse it
    if isinstance(partners_raw, str):
        # Try JSON first
        try:
            parsed = json.loads(partners_raw)
            if isinstance(parsed, list):
                return parsed
            elif isinstance(parsed, dict):
                return [parsed]
        except:
            pass
        
        # Try to parse as aggregated text format
        partners = []
        
        # Check if the format uses { } braces to separate partners
        # Pattern: { "Deal ID": 1234 ... } { "Deal ID": 5678 ... }
        if '{' in partners_raw and '"Deal ID"' in partners_raw:
            # Split by closing brace followed by opening brace
            # or find all blocks between { and }
            brace_pattern = re.compile(r'\{([^{}]+)\}', re.DOTALL)
            matches = brace_pattern.findall(partners_raw)
            print(f"[MATCH DEBUG] Found {len(matches)} brace-delimited blocks")
            
            for block in matches:
                block = block.strip()
                if not block:
                    continue
                partner = _parse_partner_text(block)
                if partner:
                    partners.append(partner)
            
            if partners:
                print(f"[MATCH DEBUG] Successfully parsed {len(partners)} partners from brace format")
                return partners
        
        # Try splitting by common delimiters
        chunks = re.split(r'(?:---+|\n\n\n+|={3,})', partners_raw)
        
        for chunk in chunks:
            chunk = chunk.strip()
            if not chunk:
                continue
            partner = _parse_partner_text(chunk)
            if partner:
                partners.append(partner)
        
        # If no chunks found, try the whole thing as one partner
        if not partners and partners_raw.strip():
            partner = _parse_partner_text(partners_raw)
            if partner:
                partners.append(partner)
        
        return partners
    
    return []


def _parse_partner_text(text):
    """Extract partner info from text format"""
    if not text or not isinstance(text, str):
        return None
    
    partner = {}
    
    # Try to extract Deal ID - handles "Deal ID": 1234 or Deal ID: 1234
    deal_id_match = re.search(r'"?Deal\s*ID"?\s*[:\s]+(\d+)', text, re.IGNORECASE)
    if deal_id_match:
        partner['id'] = int(deal_id_match.group(1))
    
    # Try to extract Title - handles "Title": value or Title: value
    title_match = re.search(r'"?Title"?\s*[:\s]+([^\n]+)', text, re.IGNORECASE)
    if title_match:
        partner['title'] = title_match.group(1).strip().strip('"')
    
    # Try to extract Name
    name_match = re.search(r'"?Name"?\s*[:\s]+([^\n]+)', text, re.IGNORECASE)
    if name_match:
        partner['name'] = name_match.group(1).strip().strip('"')
    
    # Try to extract Neighborhood (primary)
    neighborhood_match = re.search(r'"?Neighborhood"?\s*\(?primary\)?\s*[:\s]+([^\n]+)', text, re.IGNORECASE)
    if neighborhood_match:
        partner['neighborhood'] = neighborhood_match.group(1).strip().strip('"')
    
    # Try to extract Price ranges
    ft_price_match = re.search(r'"?Price Range:\s*FT\s*(?:Windowed)?"?\s*[:\s]+([^\n]+)', text, re.IGNORECASE)
    if ft_price_match:
        partner['price_ft'] = ft_price_match.group(1).strip().strip('"')
    
    pt_price_match = re.search(r'"?Price Range:\s*PT\s*(?:Windowed)?"?\s*[:\s]+([^\n]+)', text, re.IGNORECASE)
    if pt_price_match:
        partner['price_pt'] = pt_price_match.group(1).strip().strip('"')
    
    # Try to extract Availability
    avail_match = re.search(r'"?FT/PT Availability requirement"?\s*[:\s]+([^\n]+)', text, re.IGNORECASE)
    if avail_match:
        avail_text = avail_match.group(1).strip()
        label_match = re.search(r'"label"\s*:\s*"([^"]+)"', avail_text)
        if label_match:
            partner['availability'] = label_match.group(1)
        else:
            partner['availability'] = avail_text.strip('"')
    
    # Try to extract Office Notes
    notes_match = re.search(r'"?Office Notes"?\s*[:\s]+([^\n]+)', text, re.IGNORECASE)
    if notes_match:
        partner['office_notes'] = notes_match.group(1).strip().strip('"')
    
    # Try to extract Profession
    profession_match = re.search(r'"?Profession Use"?\s*[:\s]+([^\n]+)', text, re.IGNORECASE)
    if profession_match:
        partner['profession'] = profession_match.group(1).strip().strip('"')
    
    # Try to extract Link
    link_match = re.search(r'"?Link"?\s*[:\s]+(https?://[^\s\n]+)', text, re.IGNORECASE)
    if link_match:
        partner['link'] = link_match.group(1).strip()
    
    # Store raw text for OpenAI to parse
    partner['raw_text'] = text[:1500]  # Limit to first 1500 chars
    
    return partner if partner.get('id') or partner.get('title') else None


@bp_match.route("/match", methods=["POST"])
def match():
    """
    Match endpoint for Make.com integration.
    Accepts client and partners data, returns matching results.
    
    Expected payload from Make.com:
    {
        "client": { ... Pipedrive deal data for the client ... },
        "partners": [ ... array or aggregated text of partner data ... ]
    }
    
    Returns:
    {
        "email_html": "...",
        "internal_notes": "...",
        "selected_deal_ids": [...]
    }
    """
    try:
        data = request.get_json(force=True) if request.data else {}
        
        print(f"[MATCH DEBUG] Received payload keys: {list(data.keys()) if data else 'None'}")
        
        # Debug: show raw data types
        for key in (data.keys() if data else []):
            val = data[key]
            print(f"[MATCH DEBUG] Key '{key}' type: {type(val).__name__}, len: {len(val) if hasattr(val, '__len__') else 'N/A'}")
        
        client_data = data.get("client")
        partners_raw = data.get("partners", [])
        
        if not client_data:
            return jsonify({
                "error": "Missing 'client' data in payload",
                "received_keys": list(data.keys()) if data else []
            }), 400
        
        # Parse partners from various formats
        partners_data = _parse_aggregated_partners(partners_raw)
        
        print(f"[MATCH DEBUG] Client: {client_data.get('title', 'Unknown') if isinstance(client_data, dict) else 'Unknown'}")
        print(f"[MATCH DEBUG] Raw partners type: {type(partners_raw).__name__}")
        print(f"[MATCH DEBUG] Parsed partners count: {len(partners_data)}")
        
        if not partners_data:
            return jsonify({
                "error": "No partners data could be parsed",
                "partners_raw_type": type(partners_raw).__name__,
                "partners_raw_preview": str(partners_raw)[:500] if partners_raw else "empty"
            }), 400
        
        # Debug: Print first partner info
        if partners_data:
            first_partner = partners_data[0]
            if isinstance(first_partner, dict):
                print(f"[MATCH DEBUG] First partner keys: {list(first_partner.keys())[:10]}")
                print(f"[MATCH DEBUG] First partner title: {first_partner.get('title', 'No title')}")
        
        client_name = _extract_client_name(client_data)
        client_requirements = _extract_client_requirements(client_data)
        partner_summaries = [_summarize_partner(p) for p in partners_data]
        
        email_html, internal_notes, selected_deal_ids = _generate_match_response(
            client_name,
            client_requirements,
            partner_summaries,
            partners_data
        )
        
        return jsonify({
            "email_html": email_html,
            "internal_notes": internal_notes,
            "selected_deal_ids": selected_deal_ids
        })
        
    except Exception as e:
        print(f"[MATCH ERROR] {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({"error": str(e)}), 500


def _extract_client_name(client_data):
    """Extract client name from Pipedrive deal data"""
    if isinstance(client_data, dict):
        return client_data.get("person_name") or client_data.get("title", "Client")
    return "Client"


def _extract_client_requirements(client_data):
    """Extract client requirements from Pipedrive deal data"""
    requirements = {}
    
    if not isinstance(client_data, dict):
        return requirements
    
    requirements["title"] = client_data.get("title", "")
    requirements["neighborhood"] = _get_field_value(client_data, "neighborhood")
    requirements["profession"] = _get_field_value(client_data, "profession")
    requirements["availability"] = _get_field_value(client_data, "availability")
    requirements["budget"] = _get_field_value(client_data, "budget")
    requirements["office_type"] = _get_field_value(client_data, "office_type")
    requirements["start_date"] = _get_field_value(client_data, "start_date")
    
    return {k: v for k, v in requirements.items() if v}


def _get_field_value(data, field_hint):
    """Try to extract a field value by searching for matching keys"""
    if not isinstance(data, dict):
        return None
    
    for key, value in data.items():
        key_lower = key.lower()
        if field_hint.lower() in key_lower:
            if isinstance(value, dict) and "label" in value:
                return value["label"]
            elif isinstance(value, str):
                return value
    return None


def _summarize_partner(partner_data):
    """Create a summary of a partner listing for matching"""
    if not isinstance(partner_data, dict):
        return {}
    
    return {
        "deal_id": partner_data.get("id"),
        "title": partner_data.get("title", ""),
        "neighborhood": _get_field_value(partner_data, "neighborhood"),
        "availability": _get_field_value(partner_data, "availability"),
        "price": _get_field_value(partner_data, "price") or _get_field_value(partner_data, "budget"),
        "office_notes": _get_field_value(partner_data, "notes"),
        "profession": _get_field_value(partner_data, "profession"),
    }


def _generate_match_response(client_name, client_requirements, partner_summaries, partners_data):
    """Use OpenAI to generate matching response"""
    
    client = _get_openai_client()
    
    if not client:
        selected_ids = [p.get("deal_id") for p in partner_summaries if p.get("deal_id")][:5]
        return (
            f"<p>Dear {client_name},</p><p>We have found {len(selected_ids)} potential matches for you.</p>",
            "OpenAI not configured - returning first 5 partners",
            selected_ids
        )
    
    prompt = f"""You are a real estate matching assistant for therapist office rentals.

CLIENT REQUIREMENTS:
{client_requirements}

AVAILABLE PARTNER LISTINGS:
{partner_summaries}

Based on the client's requirements, select the best matching partner listings.
Consider neighborhood preferences, availability (full-time vs part-time), budget, and profession compatibility.

Respond in JSON format:
{{
    "selected_deal_ids": [list of deal IDs that are good matches],
    "email_html": "Professional HTML email to send to the client introducing the matches",
    "internal_notes": "Brief internal notes about why these matches were selected"
}}

The email should:
- Be professional and warm
- Mention specific properties and why they might be a good fit
- Include relevant details like pricing and availability
- Be formatted in clean HTML

Keep internal_notes concise - just key matching criteria and any concerns."""

    try:
        response = client.chat.completions.create(
            model="gpt-4o",
            messages=[{"role": "user", "content": prompt}],
            response_format={"type": "json_object"},
            temperature=0.7
        )
        
        result = response.choices[0].message.content
        import json
        parsed = json.loads(result)
        
        return (
            parsed.get("email_html", ""),
            parsed.get("internal_notes", ""),
            parsed.get("selected_deal_ids", [])
        )
        
    except Exception as e:
        print(f"[MATCH] OpenAI error: {e}")
        selected_ids = [p.get("deal_id") for p in partner_summaries if p.get("deal_id")][:5]
        return (
            f"<p>Dear {client_name},</p><p>We have found potential office matches for you.</p>",
            f"OpenAI error: {str(e)}",
            selected_ids
        )
