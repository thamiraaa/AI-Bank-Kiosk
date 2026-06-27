"""
form_generator.py — PDF bank form generation using ReportLab.

Generates professional, printable bank forms pre-filled with
extracted data. Supports form-type specific layouts:
  • Cash Deposit / Withdrawal Slip
  • Cheque Deposit Slip
  • Account Opening Form
  • Passbook Update Request
  • KYC Update Form
  • Generic / Other
"""

import os
from datetime import date

from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import cm
from reportlab.lib import colors
from reportlab.platypus import (
    SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle,
    HRFlowable
)
from reportlab.lib.enums import TA_CENTER, TA_LEFT, TA_RIGHT

import config


# ─────────────────────────────────────────────────────────
# Colour definitions
# ─────────────────────────────────────────────────────────
NAVY   = colors.HexColor("#0D1B2A")
BLUE   = colors.HexColor("#0077B6")
CYAN   = colors.HexColor("#00B4D8")
WHITE  = colors.white
SILVER = colors.HexColor("#E0E9F4")
LIGHT  = colors.HexColor("#F4F9FF")
GREEN  = colors.HexColor("#06D6A0")
AMBER  = colors.HexColor("#FFD166")


# ─────────────────────────────────────────────────────────
# Style helpers
# ─────────────────────────────────────────────────────────

def _styles():
    styles = {
        "title": ParagraphStyle(
            "title",
            fontSize=18, fontName="Helvetica-Bold",
            textColor=WHITE, alignment=TA_CENTER,
            spaceAfter=4
        ),
        "subtitle": ParagraphStyle(
            "subtitle",
            fontSize=10, fontName="Helvetica",
            textColor=SILVER, alignment=TA_CENTER,
            spaceAfter=12
        ),
        "form_title": ParagraphStyle(
            "form_title",
            fontSize=14, fontName="Helvetica-Bold",
            textColor=BLUE, alignment=TA_CENTER,
            spaceBefore=6, spaceAfter=8
        ),
        "section_header": ParagraphStyle(
            "section_header",
            fontSize=11, fontName="Helvetica-Bold",
            textColor=BLUE, spaceBefore=14, spaceAfter=6
        ),
        "field_label": ParagraphStyle(
            "field_label",
            fontSize=9, fontName="Helvetica-Bold",
            textColor=NAVY
        ),
        "field_value": ParagraphStyle(
            "field_value",
            fontSize=10, fontName="Helvetica",
            textColor=NAVY
        ),
        "box_label": ParagraphStyle(
            "box_label",
            fontSize=8, fontName="Helvetica",
            textColor=colors.grey
        ),
        "footer": ParagraphStyle(
            "footer",
            fontSize=8, fontName="Helvetica-Oblique",
            textColor=colors.grey, alignment=TA_CENTER
        ),
        "decl": ParagraphStyle(
            "decl",
            fontSize=9, fontName="Helvetica-Oblique",
            textColor=colors.HexColor("#4A6E8A"), leading=14
        ),
        "amount_box": ParagraphStyle(
            "amount_box",
            fontSize=20, fontName="Helvetica-Bold",
            textColor=NAVY, alignment=TA_CENTER
        ),
    }
    return styles


def _field_row(label: str, value: str, s: dict):
    """Create a two-cell table row for a form field."""
    label_p = Paragraph(label, s["field_label"])
    value_p = Paragraph(str(value) if value else "—", s["field_value"])
    return [label_p, value_p]


def _section_table(rows: list, col_widths=None):
    """Wrap rows in a styled Table."""
    if col_widths is None:
        col_widths = [5 * cm, 11 * cm]
    t = Table(rows, colWidths=col_widths, repeatRows=0)
    t.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (0, -1), LIGHT),
        ("BACKGROUND", (1, 0), (1, -1), WHITE),
        ("GRID",       (0, 0), (-1, -1), 0.4, colors.HexColor("#C0D6E8")),
        ("VALIGN",     (0, 0), (-1, -1), "MIDDLE"),
        ("TOPPADDING", (0, 0), (-1, -1), 6),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
        ("LEFTPADDING", (0, 0), (-1, -1), 8),
    ]))
    return t


def _header_banner(s: dict, form_label: str, doc_type: str):
    """Shared header banner used by all form types."""
    elements = []
    header_data = [[Paragraph("🏦  AI Bank Form Kiosk", s["title"])]]
    header_table = Table(header_data, colWidths=[17 * cm])
    header_table.setStyle(TableStyle([
        ("BACKGROUND", (0, 0), (-1, -1), NAVY),
        ("TOPPADDING", (0, 0), (-1, -1), 14),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
    ]))
    elements.append(header_table)
    elements.append(Paragraph(
        f"Automatically filled on {date.today().strftime('%d %B %Y')} • Source: {doc_type}",
        s["subtitle"]
    ))
    elements.append(HRFlowable(width="100%", thickness=2, color=CYAN, spaceAfter=6))
    elements.append(Paragraph(form_label, s["form_title"]))
    elements.append(HRFlowable(width="100%", thickness=1, color=CYAN, spaceAfter=10))
    return elements


def _signature_block(s: dict):
    """Standard signature / declaration block."""
    elements = []
    elements.append(Spacer(1, 0.5 * cm))
    elements.append(HRFlowable(width="100%", thickness=1, color=CYAN, spaceAfter=8))
    elements.append(Paragraph(
        "I hereby declare that the information provided above is true and correct "
        "to the best of my knowledge. This form was auto-filled by an AI-powered "
        "OCR system and must be verified before submission.",
        s["decl"]
    ))
    elements.append(Spacer(1, 1.2 * cm))
    sig_rows = [[
        Paragraph("_______________________", s["field_label"]),
        Paragraph("_______________________", s["field_label"]),
        Paragraph("_______________________", s["field_label"]),
    ]]
    sig_labels = [[
        Paragraph("Applicant Signature", s["footer"]),
        Paragraph("Date", s["footer"]),
        Paragraph("Bank Official", s["footer"]),
    ]]
    sig_table = Table(sig_rows + sig_labels, colWidths=[5.5 * cm, 5.5 * cm, 5.5 * cm])
    sig_table.setStyle(TableStyle([
        ("ALIGN", (0, 0), (-1, -1), "CENTER"),
        ("TOPPADDING", (0, 0), (-1, -1), 4),
    ]))
    elements.append(sig_table)
    return elements


def _footer_line(s: dict, data: dict):
    """Final footer line."""
    ai_note = "✅ AI-Enhanced" if data.get("ai_enhanced") else "📋 Regex Extracted"
    return [
        Spacer(1, 0.8 * cm),
        HRFlowable(width="100%", thickness=1, color=SILVER),
        Paragraph(
            f"Generated by AI Bank Kiosk System  •  {ai_note}  •  {date.today()}",
            s["footer"]
        ),
    ]


# ─────────────────────────────────────────────────────────
# Form-Type Specific Builders
# ─────────────────────────────────────────────────────────

def _build_deposit_slip(data: dict, s: dict, form_type: str) -> list:
    """Cash Deposit or Cash Withdrawal slip."""
    label = "CASH DEPOSIT SLIP" if form_type == "cash_deposit" else "CASH WITHDRAWAL SLIP"
    story = _header_banner(s, label, data.get("doc_type", "Document"))

    # Amount highlight box
    amount = data.get("amount", "____________")
    amount_box = Table(
        [[Paragraph(f"₹  {amount}", s["amount_box"])]],
        colWidths=[17 * cm]
    )
    amount_box.setStyle(TableStyle([
        ("BACKGROUND",    (0, 0), (-1, -1), LIGHT),
        ("GRID",          (0, 0), (-1, -1), 1.5, CYAN),
        ("TOPPADDING",    (0, 0), (-1, -1), 12),
        ("BOTTOMPADDING", (0, 0), (-1, -1), 12),
    ]))
    story.append(Paragraph("Amount (₹)", s["section_header"]))
    story.append(amount_box)
    story.append(Spacer(1, 0.4 * cm))

    # Account details
    story.append(Paragraph("Account Details", s["section_header"]))
    name = data.get("name") or data.get("holder_name", "—")
    rows = [
        _field_row("Account Holder Name", name, s),
        _field_row("Account Number",      data.get("account_no", "—"), s),
        _field_row("Bank Name",           data.get("bank_name", "—"), s),
        _field_row("Branch",              data.get("branch", "—"), s),
        _field_row("IFSC Code",           data.get("ifsc", "—"), s),
        _field_row("Mobile Number",       data.get("mobile", "—"), s),
        _field_row("Date",                str(date.today()), s),
    ]
    story.append(_section_table(rows))
    story += _signature_block(s)
    story += _footer_line(s, data)
    return story


def _build_cheque_deposit(data: dict, s: dict) -> list:
    """Cheque Deposit slip."""
    story = _header_banner(s, "CHEQUE DEPOSIT SLIP", data.get("doc_type", "Document"))

    story.append(Paragraph("Cheque Details", s["section_header"]))
    rows = [
        _field_row("Cheque Number",       data.get("cheque_no", "____________"), s),
        _field_row("Cheque Date",         data.get("cheque_date", "____________"), s),
        _field_row("Drawn on Bank",       data.get("bank_name", "—"), s),
        _field_row("Amount (₹)",          data.get("amount", "____________"), s),
    ]
    story.append(_section_table(rows))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Depositor Account Details", s["section_header"]))
    name = data.get("name") or data.get("holder_name", "—")
    rows2 = [
        _field_row("Account Holder Name", name, s),
        _field_row("Account Number",      data.get("account_no", "—"), s),
        _field_row("Branch",              data.get("branch", "—"), s),
        _field_row("IFSC Code",           data.get("ifsc", "—"), s),
        _field_row("Date",                str(date.today()), s),
    ]
    story.append(_section_table(rows2))
    story += _signature_block(s)
    story += _footer_line(s, data)
    return story


def _build_account_opening(data: dict, s: dict) -> list:
    """Account Opening form."""
    story = _header_banner(s, "ACCOUNT OPENING FORM", data.get("doc_type", "Document"))

    story.append(Paragraph("Personal Details", s["section_header"]))
    rows = [
        _field_row("Full Name",          data.get("name", "—"), s),
        _field_row("Date of Birth",      data.get("dob", "—"), s),
        _field_row("Gender",             data.get("gender", "—"), s),
        _field_row("Father's Name",      data.get("father_name", "—"), s),
        _field_row("Mobile Number",      data.get("mobile", "—"), s),
        _field_row("Address",            data.get("address", "—"), s),
    ]
    story.append(_section_table(rows))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Identity Documents", s["section_header"]))
    rows2 = [
        _field_row("Aadhaar Number",     data.get("aadhaar_number", "—"), s),
        _field_row("PAN Number",         data.get("pan_number", "—"), s),
    ]
    story.append(_section_table(rows2))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Account Preferences", s["section_header"]))
    rows3 = [
        _field_row("Account Type",       "Savings Account", s),
        _field_row("Nominee Name",       "____________", s),
        _field_row("Nominee Relation",   "____________", s),
    ]
    story.append(_section_table(rows3))
    story += _signature_block(s)
    story += _footer_line(s, data)
    return story


def _build_kyc_update(data: dict, s: dict) -> list:
    """KYC Update form."""
    story = _header_banner(s, "KYC UPDATE FORM", data.get("doc_type", "Document"))

    story.append(Paragraph("Customer Details", s["section_header"]))
    rows = [
        _field_row("Full Name",          data.get("name", "—"), s),
        _field_row("Date of Birth",      data.get("dob", "—"), s),
        _field_row("Gender",             data.get("gender", "—"), s),
        _field_row("Mobile Number",      data.get("mobile", "—"), s),
        _field_row("Address",            data.get("address", "—"), s),
    ]
    story.append(_section_table(rows))
    story.append(Spacer(1, 0.3 * cm))

    story.append(Paragraph("Identity Verification", s["section_header"]))
    rows2 = [
        _field_row("Aadhaar Number",     data.get("aadhaar_number", "—"), s),
        _field_row("PAN Number",         data.get("pan_number", "—"), s),
        _field_row("Account Number",     data.get("account_no", "—"), s),
    ]
    story.append(_section_table(rows2))
    story += _signature_block(s)
    story += _footer_line(s, data)
    return story


def _build_passbook_update(data: dict, s: dict) -> list:
    """Passbook Update request form."""
    story = _header_banner(s, "PASSBOOK UPDATE REQUEST", data.get("doc_type", "Document"))

    story.append(Paragraph("Account Details", s["section_header"]))
    name = data.get("holder_name") or data.get("name", "—")
    rows = [
        _field_row("Account Holder Name", name, s),
        _field_row("Account Number",      data.get("account_no", "—"), s),
        _field_row("Branch",              data.get("branch", "—"), s),
        _field_row("Bank Name",           data.get("bank_name", "—"), s),
        _field_row("Mobile Number",       data.get("mobile", "—"), s),
        _field_row("Date",                str(date.today()), s),
    ]
    story.append(_section_table(rows))
    story += _signature_block(s)
    story += _footer_line(s, data)
    return story


def _build_generic(data: dict, s: dict) -> list:
    """Generic / Other form."""
    story = _header_banner(s, "BANK SERVICE REQUEST FORM", data.get("doc_type", "Document"))

    skip = {"doc_type", "date", "_raw_text", "_confidence", "ai_enhanced", "ai_error"}
    labels_map = {
        "name": "Full Name", "dob": "Date of Birth", "gender": "Gender",
        "aadhaar_number": "Aadhaar Number", "address": "Address",
        "holder_name": "Account Holder", "account_no": "Account Number",
        "ifsc": "IFSC Code", "branch": "Branch", "bank_name": "Bank Name",
        "micr": "MICR Code", "mobile": "Mobile Number",
        "pan_number": "PAN Number", "father_name": "Father Name",
    }

    story.append(Paragraph("Extracted Data", s["section_header"]))
    rows = [
        _field_row(labels_map.get(k, k.replace("_", " ").title()), v, s)
        for k, v in data.items()
        if k not in skip
    ]
    if rows:
        story.append(_section_table(rows))
    story += _signature_block(s)
    story += _footer_line(s, data)
    return story


# ─────────────────────────────────────────────────────────
# Public API
# ─────────────────────────────────────────────────────────

def generate_form_by_type(data: dict, form_type: str,
                          output_path: str = None) -> str:
    """
    Generate a filled bank form PDF for the given *form_type*.

    Args:
        data        : dict returned by extractor + ai_helper + user edits
        form_type   : key from config.FORM_TYPES
                      e.g. 'cash_deposit', 'account_opening', etc.
        output_path : optional full file path for the PDF

    Returns:
        The absolute path to the generated PDF.
    """
    if output_path is None:
        output_path = os.path.join(config.PDF_OUTPUT_DIR, config.PDF_FILENAME)

    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=2 * cm, leftMargin=2 * cm,
        topMargin=2 * cm, bottomMargin=2 * cm,
    )
    s = _styles()

    if form_type == "cash_deposit":
        story = _build_deposit_slip(data, s, "cash_deposit")
    elif form_type == "cash_withdrawal":
        story = _build_deposit_slip(data, s, "cash_withdrawal")
    elif form_type == "cheque_deposit":
        story = _build_cheque_deposit(data, s)
    elif form_type == "account_opening":
        story = _build_account_opening(data, s)
    elif form_type == "kyc_update":
        story = _build_kyc_update(data, s)
    elif form_type == "passbook_update":
        story = _build_passbook_update(data, s)
    else:
        story = _build_generic(data, s)

    doc.build(story)
    return output_path


# ─────────────────────────────────────────────────────────
# Backward-compatible wrapper (used by old main.py code)
# ─────────────────────────────────────────────────────────

def generate_bank_form(data: dict, output_path: str = None) -> str:
    """
    Backward-compatible API — calls generate_form_by_type with 'other'.
    """
    return generate_form_by_type(data, "other", output_path)
