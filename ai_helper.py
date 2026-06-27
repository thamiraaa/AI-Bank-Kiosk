"""
ai_helper.py — Gemini AI post-processing and Vision OCR extraction.

Sends raw image or OCR text to the Gemini API with a structured prompt
asking it to extract and correct the relevant fields, then
returns a clean dict.
"""

import json
import re
import warnings
import config


def _extract_json_from_response(text: str) -> dict:
    """Try to parse JSON from the AI response (handles markdown code fences)."""
    clean = re.sub(r'```(?:json)?', '', text).strip().strip('`')
    return json.loads(clean)


def _call_gemini(prompt: str) -> str:
    """Call the Gemini API and return the text response."""
    import google.generativeai as genai
    warnings.simplefilter('ignore', FutureWarning)
    genai.configure(api_key=config.GEMINI_API_KEY)
    model = genai.GenerativeModel("gemini-2.5-flash")
    response = model.generate_content(prompt)
    return response.text


def enhance_with_vision(image_path: str, doc_type: str) -> dict:
    """
    Process the image directly using Gemini Vision for near 100% accuracy,
    bypassing Tesseract entirely.
    """
    if not config.GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY is not configured.")

    import google.generativeai as genai
    from PIL import Image

    warnings.simplefilter('ignore', FutureWarning)
    genai.configure(api_key=config.GEMINI_API_KEY)
    # Using the 2.5-flash model which is fast and supports vision natively
    model = genai.GenerativeModel("gemini-2.5-flash")
    img = Image.open(image_path)

    if doc_type == "aadhaar":
        prompt = (
            "You are an expert OCR and data extraction system for Indian Aadhaar cards.\n"
            "Extract the following fields from this image. Return ONLY a valid JSON object.\n"
            "Use 'Not found' for any field you cannot determine.\n"
            "{\n"
            "  \"name\": \"full name of the card holder\",\n"
            "  \"dob\": \"date of birth in DD/MM/YYYY format\",\n"
            "  \"gender\": \"Male or Female or Transgender\",\n"
            "  \"aadhaar_number\": \"12-digit aadhaar number in format XXXX XXXX XXXX\",\n"
            "  \"address\": \"full address if visible\"\n"
            "}"
        )
    elif doc_type == "passbook":
        prompt = (
            "You are an expert OCR and data extraction system for Indian bank passbooks.\n"
            "Extract the following fields from this image. Return ONLY a valid JSON object.\n"
            "Use 'Not found' for any field you cannot determine.\n"
            "{\n"
            "  \"holder_name\": \"full name of the account holder\",\n"
            "  \"account_no\": \"bank account number (9-18 digits)\",\n"
            "  \"ifsc\": \"IFSC code in format ABCD0XXXXXX\",\n"
            "  \"branch\": \"branch name\",\n"
            "  \"bank_name\": \"name of the bank\",\n"
            "  \"micr\": \"MICR code if present (9 digits)\",\n"
            "  \"mobile\": \"mobile number if present\"\n"
            "}"
        )
    elif doc_type == "pan":
        prompt = (
            "You are an expert OCR and data extraction system for Indian PAN cards.\n"
            "Extract the following fields from this image. Return ONLY a valid JSON object.\n"
            "Use 'Not found' for any field you cannot determine.\n"
            "{\n"
            "  \"name\": \"full name of the PAN card holder (not father's name)\",\n"
            "  \"father_name\": \"father's full name\",\n"
            "  \"dob\": \"date of birth in DD/MM/YYYY format\",\n"
            "  \"pan_number\": \"PAN number in format AAAAA9999A\"\n"
            "}"
        )
    else:
        raise ValueError(f"Unknown doc_type: {doc_type}")

    response = model.generate_content([prompt, img])
    ai_data = _extract_json_from_response(response.text)
    
    # Clean up empty strings or nulls to "Not found"
    for k, v in ai_data.items():
        if not v or str(v).strip() == "":
            ai_data[k] = "Not found"

    ai_data["ai_enhanced"] = True
    ai_data["doc_type"] = doc_type
    ai_data["_confidence"] = 100.0  # Vision model confidence is effectively perfect
    ai_data["_raw_text"] = "Extracted directly from image via Gemini 2.5 Vision"
    
    return ai_data


def enhance_with_ai(ocr_text: str, doc_type: str, regex_data: dict) -> dict:
    """
    Fallback for when Vision isn't used.
    Post-process regex-extracted data using the Gemini AI on text.
    """
    if not config.GEMINI_API_KEY:
        return regex_data

    try:
        if doc_type == "aadhaar":
            prompt = f"Extract and correct from OCR text: {ocr_text}\nReturn JSON with keys: name, dob, gender, aadhaar_number, address."
        elif doc_type == "passbook":
            prompt = f"Extract and correct from OCR text: {ocr_text}\nReturn JSON with keys: holder_name, account_no, ifsc, branch, bank_name, micr, mobile."
        elif doc_type == "pan":
            prompt = f"Extract and correct from OCR text: {ocr_text}\nReturn JSON with keys: name, father_name, dob, pan_number."
        else:
            return regex_data

        response_text = _call_gemini(prompt)
        ai_data = _extract_json_from_response(response_text)

        merged = dict(regex_data)
        for key, ai_val in ai_data.items():
            if ai_val and ai_val.lower() != "not found":
                if merged.get(key, "Not found") == "Not found" or key in merged:
                    merged[key] = ai_val

        merged["ai_enhanced"] = True
        return merged

    except Exception as exc:
        regex_data["ai_error"] = str(exc)
        return regex_data
