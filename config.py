"""
config.py — Central configuration for the Bank Kiosk system.
Edit the paths and API key here before running the application.
"""

import os

# ─────────────────────────────────────────────────────────
# Tesseract OCR
# ─────────────────────────────────────────────────────────
TESSERACT_PATH = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# ─────────────────────────────────────────────────────────
# Gemini AI (optional – leave empty string to disable)
# Set via environment variable for security, or paste key here.
# ─────────────────────────────────────────────────────────
GEMINI_API_KEY = "AIzaSyBmIMlkeshkXh2oUgmp07SrzC1M-J833Uo"

# ─────────────────────────────────────────────────────────
# Default Test Image Paths (used when no image is chosen)
# ─────────────────────────────────────────────────────────
DEFAULT_AADHAAR_PATH  = r"C:\Users\Thamira\OneDrive\Desktop\bank hardware\hh aadhar.jpeg"
DEFAULT_PASSBOOK_PATH = r"C:\Users\Thamira\OneDrive\Desktop\bank hardware\bank passbook.jpeg"
DEFAULT_PAN_PATH      = r"C:\Users\Thamira\OneDrive\Desktop\pan_card.jpeg"

# ─────────────────────────────────────────────────────────
# PDF Output
# ─────────────────────────────────────────────────────────
PDF_OUTPUT_DIR = r"C:\Users\Thamira\OneDrive\Desktop"
PDF_FILENAME   = "bank_form_filled.pdf"

# ─────────────────────────────────────────────────────────
# SQLite Database
# ─────────────────────────────────────────────────────────
DB_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "kiosk_transactions.db"
)

# ─────────────────────────────────────────────────────────
# UI / Kiosk Settings
# ─────────────────────────────────────────────────────────
APP_TITLE      = "AI Bank Form Kiosk"
WINDOW_WIDTH   = 1100
WINDOW_HEIGHT  = 800
FULLSCREEN     = False          # Set True for real kiosk deployment

# ── Professional Corporate Banking palette ─────────────
COLOR_BG           = "#FFFFFF"     # Pure clean white
COLOR_SURFACE      = "#F2F6FC"     # Subtle cool-white surface
COLOR_PRIMARY      = "#1A56DB"     # Deep professional blue (SBI/HDFC style)
COLOR_SECONDARY    = "#0E3A8C"     # Dark corporate navy
COLOR_SUCCESS      = "#0E9F6E"     # Professional green
COLOR_WARNING      = "#E3A008"     # Warm amber
COLOR_ERROR        = "#E02424"     # Alert red
COLOR_TEXT         = "#111928"     # Near-black for crisp readability
COLOR_SUBTEXT      = "#6B7280"     # Professional gray subtext
COLOR_GLASS        = "#EBF3FF"     # Light blue-white card background
COLOR_GLASS_BORDER = "#C3DDFF"     # Subtle blue card border

FONT_FAMILY     = "Segoe UI"

# ─────────────────────────────────────────────────────────
# Multi-Language Support
# ─────────────────────────────────────────────────────────
LANGUAGES = {
    "en": {"name": "English",   "native": "English",    "flag": "🇬🇧"},
    "ta": {"name": "Tamil",     "native": "தமிழ்",       "flag": "🇮🇳"},
    "hi": {"name": "Hindi",     "native": "हिंदी",        "flag": "🇮🇳"},
    "te": {"name": "Telugu",    "native": "తెలుగు",       "flag": "🇮🇳"},
    "kn": {"name": "Kannada",   "native": "ಕನ್ನಡ",        "flag": "🇮🇳"},
    "ml": {"name": "Malayalam", "native": "മലയാളം",       "flag": "🇮🇳"},
}

# ─────────────────────────────────────────────────────────
# Banking Service Types
# ─────────────────────────────────────────────────────────
FORM_TYPES = {
    "cash_deposit": {
        "label":    "Cash Deposit",
        "icon":     "💵",
        "image":    "assets/cash_icon.png",
        "desc":     "Deposit cash into account",
        "requires": ["account_no", "amount", "name"],
    },
    "cash_withdrawal": {
        "label":    "Cash Withdrawal",
        "icon":     "🏧",
        "image":    "assets/cash_icon.png",
        "desc":     "Withdraw cash from account",
        "requires": ["account_no", "amount", "name"],
    },
    "cheque_deposit": {
        "label":    "Cheque Deposit",
        "icon":     "📋",
        "image":    "assets/cheque_icon.png",
        "desc":     "Deposit a cheque",
        "requires": ["account_no", "cheque_no", "name", "bank_name"],
    },
    "account_opening": {
        "label":    "Account Opening",
        "icon":     "🏦",
        "image":    "assets/bank_icon.png",
        "desc":     "Open a new bank account",
        "requires": ["name", "dob", "address", "mobile", "aadhaar_number"],
    },
    "passbook_update": {
        "label":    "Passbook Update",
        "icon":     "📔",
        "image":    "assets/bank_icon.png",
        "desc":     "Update your passbook",
        "requires": ["account_no", "name"],
    },
    "kyc_update": {
        "label":    "KYC Update",
        "icon":     "🪪",
        "image":    "assets/bank_icon.png", # Using bank icon as fallback for KYC since it failed to generate
        "desc":     "Update KYC information",
        "requires": ["name", "dob", "address", "aadhaar_number", "mobile"],
    },
    "other": {
        "label":    "Other Forms",
        "icon":     "📄",
        "image":    "assets/bank_icon.png",
        "desc":     "Miscellaneous banking forms",
        "requires": [],
    },
}
