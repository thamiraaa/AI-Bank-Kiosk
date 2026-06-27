import cv2
import pytesseract
import re
from datetime import date

# -----------------------------
# Tesseract path
# -----------------------------
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# -----------------------------
# MENU
# -----------------------------
print("\n===== BANK OCR SYSTEM =====")
print("1. Aadhaar Scan")
print("2. Passbook Scan")

mode = input("Enter choice (1 or 2): ")

# -----------------------------
# IMAGE PATHS
# -----------------------------
aadhaar_path = r"C:\Users\Thamira\OneDrive\Desktop\ts Aadhar.jpeg"
passbook_path = r"C:\Users\Thamira\OneDrive\Desktop\bank passbook.jpeg"

img_path = aadhaar_path if mode == "1" else passbook_path

# -----------------------------
# LOAD IMAGE
# -----------------------------
img = cv2.imread(img_path)

if img is None:
    print("❌ Image not found. Check path")
    exit()

# -----------------------------
# PREPROCESSING (IMPROVED)
# -----------------------------
gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

# upscale (VERY IMPORTANT)
gray = cv2.resize(gray, None, fx=2.5, fy=2.5, interpolation=cv2.INTER_CUBIC)

# remove noise
gray = cv2.GaussianBlur(gray, (3, 3), 0)

# adaptive threshold (BEST for documents)
gray = cv2.adaptiveThreshold(
    gray, 255,
    cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
    cv2.THRESH_BINARY,
    31, 2
)

# -----------------------------
# OCR (IMPROVED MODE)
# -----------------------------
config = r'--oem 3 --psm 4'
text = pytesseract.image_to_string(gray, config=config)

print("\n===== OCR TEXT DEBUG =====\n")
print(text)

# -----------------------------
# OUTPUT STRUCTURE
# -----------------------------
data = {
    "name": "Not found",
    "dob": "Not found",
    "aadhaar": "Not found",
    "account_no": "Not found",
    "ifsc": "Not found",
    "branch": "Not found",
    "date": str(date.today())
}

# -----------------------------
# AADHAAR EXTRACTION
# -----------------------------
if mode == "1":

    aadhaar = re.findall(r'\d{4}\s\d{4}\s\d{4}', text)
    dob = re.findall(r'\d{2}/\d{2}/\d{4}', text)

    lines = text.split("\n")

    for line in lines:
        line = line.strip()

        if len(line) < 4:
            continue
        if any(char.isdigit() for char in line):
            continue
        if "government" in line.lower():
            continue
        if "aadhaar" in line.lower():
            continue
        if "india" in line.lower():
            continue
        if "male" in line.lower():
            continue
        if "female" in line.lower():
            continue

        if len(line.split()) >= 2:
            data["name"] = line
            break

    if aadhaar:
        data["aadhaar"] = aadhaar[0]

    if dob:
        data["dob"] = dob[0]

# -----------------------------
# PASSBOOK EXTRACTION
# -----------------------------
elif mode == "2":

    account = re.findall(r'\d{9,18}', text)
    ifsc = re.findall(r'[A-Z]{4}0[A-Z0-9]{6}', text)

    branch_match = re.search(r'Branch[:\s]*(.*)', text, re.IGNORECASE)

    if account:
        data["account_no"] = account[0]

    if ifsc:
        data["ifsc"] = ifsc[0]

    if branch_match:
        data["branch"] = branch_match.group(1).strip()

# -----------------------------
# FINAL OUTPUT
# -----------------------------
print("\n===== FILLED FORM DATA =====\n")

for k, v in data.items():
    print(f"{k.upper()}: {v}")