from flask import Blueprint, jsonify, request
import os
from openai import OpenAI

bp_match = Blueprint("match", __name__)

def _get_openai_client():
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        return None
    return OpenAI(api_key=api_key)

@bp_match.route("/match", methods=["POST"])
def match():
    """
    Match endpoint for Make.com integration.
    Accepts client and partners data, returns matching results.
    
    Expected payload from Make.com:
    {
        "client": { ... Pipedrive deal data for the client ... },
        "partners": [ ... array of Pipedrive deal data for potential matches ... ]
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
        
        client_data = data.get("client")
        partners_data = data.get("partners", [])
        
        if not client_data:
            return jsonify({
                "error": "Missing 'client' data in payload",
                "received_keys": list(data.keys()) if data else []
            }), 400
        
        if not partners_data:
            return jsonify({
                "error": "Missing 'partners' data in payload",
                "received_keys": list(data.keys()) if data else []
            }), 400
        
        print(f"[MATCH DEBUG] Client: {client_data.get('title', 'Unknown')}")
        print(f"[MATCH DEBUG] Partners count: {len(partners_data)}")
        
        # Debug: Print first partner's keys and title
        if partners_data:
            first_partner = partners_data[0] if isinstance(partners_data, list) else partners_data
            if isinstance(first_partner, dict):
                print(f"[MATCH DEBUG] First partner keys: {list(first_partner.keys())[:10]}")
                print(f"[MATCH DEBUG] First partner title: {first_partner.get('title', 'No title')}")
            else:
                print(f"[MATCH DEBUG] Partner data type: {type(first_partner)}")
        
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
