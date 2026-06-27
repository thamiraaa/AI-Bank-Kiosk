"""
extractor.py — Regex-based field extraction from OCR text.

Handles three document types:
  • Aadhaar card  → name, dob, gender, aadhaar_number, address
  • Bank passbook → holder_name, account_no, ifsc, branch, bank_name, micr, mobile
  • PAN card      → name, dob, pan_number, father_name

All patterns are tuned for Indian document formats.
"""

import re
from datetime import date


# ─────────────────────────────────────────────────────────
# Noise / header lines to skip when hunting for the name
# ─────────────────────────────────────────────────────────
_AADHAAR_SKIP_KEYWORDS = {
    "government", "india", "aadhaar", "unique", "identification",
    "authority", "male", "female", "dob", "date", "birth", "year",
    "address", "enrol", "enrollment", "vid", "virtual", "help",
    "www", "http", "uidai", "resident"
}

_PAN_SKIP_KEYWORDS = {
    "income", "tax", "department", "government", "india",
    "permanent", "account", "number", "card", "permanent account number"
}


def _is_likely_name_line(line: str) -> bool:
    """Heuristic: a name line has 2+ words, no digits, no noise keywords."""
    line_stripped = line.strip()
    if len(line_stripped) < 4:
        return False
    if any(ch.isdigit() for ch in line_stripped):
        return False
    words = line_stripped.split()
    if len(words) < 2:
        return False
    lower = line_stripped.lower()
    if any(kw in lower for kw in _AADHAAR_SKIP_KEYWORDS):
        return False
    # Must be mostly alphabetic / spaces (relaxed to 70% to tolerate OCR errors)
    alpha_ratio = sum(c.isalpha() or c.isspace() for c in line_stripped) / len(line_stripped)
    return alpha_ratio > 0.70


# ─────────────────────────────────────────────────────────
# Aadhaar Extraction
# ─────────────────────────────────────────────────────────

def extract_aadhaar_data(text: str) -> dict:
    """
    Extract structured fields from Aadhaar card OCR text.

    Returns a dict with keys:
        name, dob, gender, aadhaar_number, address, doc_type, date
    """
    data = {
        "doc_type"      : "Aadhaar Card",
        "name"          : "Not found",
        "dob"           : "Not found",
        "gender"        : "Not found",
        "aadhaar_number": "Not found",
        "address"       : "Not found",
        "date"          : str(date.today()),
    }

    lines = [ln.strip() for ln in text.split("\n")]

    # ── Aadhaar number: XXXX XXXX XXXX ──────────────────
    # Ensure it's exactly 3 groups of 4 digits, not part of a 16-digit VID
    aadhaar_matches = re.findall(r'(?<!\d)(?<!\d\s)\b\d{4}\s\d{4}\s\d{4}\b(?!\s\d)', text)
    if not aadhaar_matches:
        # Fallback to 12 continuous digits if spaces are missing
        aadhaar_matches = re.findall(r'(?<!\d)\d{12}(?!\d)', text)
        
    if aadhaar_matches:
        data["aadhaar_number"] = aadhaar_matches[0]

    # ── Date of birth ────────────────────────────────────
    dob_patterns = [
        r'\b(\d{2}/\d{2}/\d{4})\b',       # 01/01/1990
        r'\b(\d{2}-\d{2}-\d{4})\b',       # 01-01-1990
        r'DOB[:\s]*(\d{2}[\/\-]\d{2}[\/\-]\d{4})',
        r'Year of Birth[:\s]*(\d{4})',
        r'Birth[:\s]*(\d{2}[\/\-]\d{2}[\/\-]\d{4})',
    ]
    for pat in dob_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            data["dob"] = m.group(1)
            break

    # ── Gender ───────────────────────────────────────────
    if re.search(r'\bMale\b', text, re.IGNORECASE):
        data["gender"] = "Male"
    elif re.search(r'\bFemale\b', text, re.IGNORECASE):
        data["gender"] = "Female"
    elif re.search(r'\bTransgender\b', text, re.IGNORECASE):
        data["gender"] = "Transgender"

    # ── Name: first clean multi-word alphabetic line ─────
    # Often the line immediately preceding DOB is the name on Aadhaar
    name_found = False
    for i, line in enumerate(lines):
        if _is_likely_name_line(line):
            data["name"] = line.strip()
            name_found = True
            break
            
    # Fallback name logic if heuristic failed but DOB is found
    if not name_found and data["dob"] != "Not found":
        for i, line in enumerate(lines):
            if data["dob"] in line and i > 0:
                # The line before DOB is often the name
                candidate = lines[i-1].strip()
                if len(candidate) > 4 and not any(ch.isdigit() for ch in candidate):
                    data["name"] = candidate
                    break

    # ── Address: lines after "Address" keyword ───────────
    addr_match = re.search(
        r'(?:Address|Addr)[:\s]*(.*?)(?:\n{2,}|\d{4}\s\d{4}\s\d{4}|$)',
        text, re.IGNORECASE | re.DOTALL
    )
    if addr_match:
        addr_raw = addr_match.group(1).replace("\n", ", ").strip(" ,")
        if addr_raw:
            data["address"] = addr_raw[:200]   # cap length

    return data


# ─────────────────────────────────────────────────────────
# PAN Card Extraction
# ─────────────────────────────────────────────────────────

def extract_pan_data(text: str) -> dict:
    """
    Extract structured fields from PAN card OCR text.

    Returns a dict with keys:
        doc_type, name, father_name, dob, pan_number, date
    """
    data = {
        "doc_type"    : "PAN Card",
        "name"        : "Not found",
        "father_name" : "Not found",
        "dob"         : "Not found",
        "pan_number"  : "Not found",
        "date"        : str(date.today()),
    }

    lines = [ln.strip() for ln in text.split("\n") if ln.strip()]

    # ── PAN Number: AAAAA9999A format ────────────────────
    pan_matches = re.findall(r'\b([A-Z]{5}[0-9]{4}[A-Z])\b', text)
    if pan_matches:
        data["pan_number"] = pan_matches[0]

    # ── Date of birth ────────────────────────────────────
    dob_patterns = [
        r'\b(\d{2}/\d{2}/\d{4})\b',
        r'\b(\d{2}-\d{2}-\d{4})\b',
        r'Date of Birth[:\s]*(\d{2}[\/\-]\d{2}[\/\-]\d{4})',
    ]
    for pat in dob_patterns:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            data["dob"] = m.group(1)
            break

    # ── Name & Father's Name ─────────────────────────────
    # PAN cards typically show: Name on one line, Father's name on next
    # Skip lines with PAN keywords
    name_candidates = []
    for line in lines:
        lower = line.lower()
        if any(kw in lower for kw in _PAN_SKIP_KEYWORDS):
            continue
        if _is_likely_name_line(line):
            name_candidates.append(line.strip())

    if len(name_candidates) >= 1:
        data["name"] = name_candidates[0]
    if len(name_candidates) >= 2:
        data["father_name"] = name_candidates[1]

    return data


# ─────────────────────────────────────────────────────────
# Passbook Extraction
# ─────────────────────────────────────────────────────────

def extract_passbook_data(text: str) -> dict:
    """
    Extract structured fields from bank passbook OCR text.

    Returns a dict with keys:
        doc_type, holder_name, account_no, ifsc, branch,
        bank_name, micr, mobile, date
    """
    data = {
        "doc_type"   : "Bank Passbook",
        "holder_name": "Not found",
        "account_no" : "Not found",
        "ifsc"       : "Not found",
        "branch"     : "Not found",
        "bank_name"  : "Not found",
        "micr"       : "Not found",
        "mobile"     : "Not found",
        "date"       : str(date.today()),
    }

    # ── Account number: 9–18 consecutive digits ──────────
    # Exclude years (4-digit) and short codes
    account_matches = re.findall(r'\b(\d{9,18})\b', text)
    if account_matches:
        # Pick the longest match (most likely to be acct no)
        data["account_no"] = max(account_matches, key=len)

    # ── IFSC code: ABCD0XXXXXX ───────────────────────────
    ifsc_matches = re.findall(r'\b([A-Z]{4}0[A-Z0-9]{6})\b', text)
    if ifsc_matches:
        data["ifsc"] = ifsc_matches[0]

    # ── Branch name ──────────────────────────────────────
    branch_match = re.search(
        r'Branch\s*[:\-]?\s*([A-Za-z\s,]+?)(?:\n|IFSC|$)',
        text, re.IGNORECASE
    )
    if branch_match:
        data["branch"] = branch_match.group(1).strip()

    # ── Bank name ────────────────────────────────────────
    known_banks = [
        "State Bank of India", "SBI",
        "HDFC Bank", "HDFC",
        "ICICI Bank", "ICICI",
        "Axis Bank", "Axis",
        "Canara Bank", "Punjab National Bank", "PNB",
        "Bank of Baroda", "BOB",
        "Union Bank", "Indian Bank",
        "Kotak Mahindra", "YES Bank",
        "Bank of India", "Central Bank",
        "UCO Bank", "Indian Overseas Bank",
    ]
    for bank in known_banks:
        if re.search(re.escape(bank), text, re.IGNORECASE):
            data["bank_name"] = bank
            break

    # ── MICR code: 9 consecutive digits ──────────────────
    micr_match = re.search(r'MICR[:\s]*(\d{9})', text, re.IGNORECASE)
    if not micr_match:
        micr_match = re.search(r'(?<!\d)(\d{9})(?!\d)', text)
    if micr_match:
        data["micr"] = micr_match.group(1)

    # ── Mobile number ────────────────────────────────────
    mobile_match = re.search(r'(?:Mobile|Ph|Phone|Mob)[:\s]*(\+?91[-\s]?\d{10}|\d{10})',
                              text, re.IGNORECASE)
    if mobile_match:
        data["mobile"] = mobile_match.group(1).strip()

    # ── Holder name ──────────────────────────────────────
    _PASSBOOK_SKIP = {
        "branch", "account", "ifsc", "micr", "bank", "mobile",
        "phone", "balance", "savings", "current", "statement",
        "deposit", "passbook", "ltd", "limited"
    }
    lines = [ln.strip() for ln in text.split("\n")]
    for line in lines:
        lower = line.lower()
        if any(kw in lower for kw in _PASSBOOK_SKIP):
            continue
        if _is_likely_name_line(line) and len(line) > 5:
            data["holder_name"] = line.strip()
            break

    return data


# ─────────────────────────────────────────────────────────
# Unified entry point
# ─────────────────────────────────────────────────────────

def extract(text: str, doc_type: str) -> dict:
    """
    Route to the correct extractor based on doc_type.

    Args:
        text     : raw OCR string
        doc_type : "aadhaar", "passbook", or "pan"

    Returns:
        structured dict of extracted fields
    """
    if doc_type == "aadhaar":
        return extract_aadhaar_data(text)
    elif doc_type == "passbook":
        return extract_passbook_data(text)
    elif doc_type == "pan":
        return extract_pan_data(text)
    else:
        raise ValueError(f"Unknown doc_type: {doc_type!r}")
