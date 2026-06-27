"""
main.py — AI-Powered Bank Form Filling Kiosk
Full kiosk UI with 5 screens, rebuilt with CustomTkinter for a modern UI.

  Screen 0: LanguageScreen  — Select language (6 Indian languages)
  Screen 1: ServiceScreen   — Select banking service / form type
  Screen 2: DocumentScreen  — Select document (Aadhaar / PAN / Passbook)
  Screen 3: ScanScreen      — Load / capture image, run OCR
  Screen 4: ReviewScreen    — Review fields, enter missing data, generate PDF
"""

import os
import threading
import tkinter as tk
from tkinter import filedialog, messagebox
import customtkinter as ctk
from PIL import Image

import config
import ocr_engine
import extractor
import ai_helper
import form_generator
import tts_engine
import db_logger
import security
from keypad_widget import NumericKeypad, AlphaKeypad

# Set CustomTkinter appearance to Light mode for professional banking look
ctk.set_appearance_mode("Light")
ctk.set_default_color_theme("blue")


# ═══════════════════════════════════════════════════════════
# KioskApp
# ═══════════════════════════════════════════════════════════

class KioskApp(ctk.CTk):

    def __init__(self):
        super().__init__()
        self.title(config.APP_TITLE)
        self.geometry(f"{config.WINDOW_WIDTH}x{config.WINDOW_HEIGHT}")
        self.configure(fg_color=config.COLOR_BG)

        if config.FULLSCREEN:
            self.attributes("-fullscreen", True)

        # ── Kiosk-wide state ─────────────────────────────
        self.language    = tk.StringVar(value="en")
        self.form_type   = tk.StringVar(value="other")
        self.doc_type    = tk.StringVar(value="aadhaar")
        self.image_path  = tk.StringVar(value="")
        
        # We accumulate OCR results here so multiple scans merge together!
        self.ocr_result  = {}
        self.temp_files  = []

        # ── Container ────────────────────────────────────
        self.container = ctk.CTkFrame(self, fg_color="transparent")
        self.container.pack(fill="both", expand=True)
        self.container.grid_rowconfigure(0, weight=1)
        self.container.grid_columnconfigure(0, weight=1)

        # ── Build all screens ────────────────────────────
        self.screens = {}
        for ScreenClass in (
            LanguageScreen,
            ServiceScreen,
            DocumentScreen,
            ScanScreen,
            ReviewScreen,
        ):
            screen = ScreenClass(self.container, self)
            self.screens[ScreenClass.__name__] = screen
            screen.grid(row=0, column=0, sticky="nsew")

        self.show_screen("LanguageScreen")

    # ── Navigation ───────────────────────────────────────

    def show_screen(self, name: str):
        screen = self.screens[name]
        screen.on_show()
        screen.tkraise()

    def get_lang(self) -> str:
        return self.language.get()

    # ── Session reset ────────────────────────────────────

    def reset_session(self):
        """Secure wipe of all session data and return to language screen."""
        security.cleanup_session(self.temp_files)
        security.clear_app_state(self)
        self.ocr_result = {}  # Reset accumulated data
        self.show_screen("LanguageScreen")


# ═══════════════════════════════════════════════════════════
# Base screen
# ═══════════════════════════════════════════════════════════

class BaseScreen(ctk.CTkFrame):

    def __init__(self, parent, app: KioskApp):
        super().__init__(parent, fg_color=config.COLOR_BG)
        self.app = app
        self._image_cache = {}  # Keep references to CTkImages

    def on_show(self):
        pass

    def load_icon_image(self, path: str, size=(100, 100)):
        if path in self._image_cache:
            return self._image_cache[path]
        try:
            full_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), path)
            img = Image.open(full_path)
            ctk_img = ctk.CTkImage(light_image=img, dark_image=img, size=size)
            self._image_cache[path] = ctk_img
            return ctk_img
        except Exception as e:
            print(f"Failed to load image {path}: {e}")
            return None

    # ── Helpers ─────────────────────────────────────────

    def _topbar(self, text, bg=None, fg=None, size=24):
        bg = bg or config.COLOR_SECONDARY
        fg = fg or "#FFFFFF"
        bar = ctk.CTkFrame(self, fg_color=bg, corner_radius=0)
        bar.pack(fill="x", ipady=14)
        # Blue accent line at bottom of topbar
        ctk.CTkLabel(bar, text=text,
                     font=ctk.CTkFont(family=config.FONT_FAMILY, size=size, weight="bold"),
                     text_color=fg).pack(pady=(4,4))
        # Thin accent line
        ctk.CTkFrame(self, fg_color=config.COLOR_PRIMARY, height=3, corner_radius=0).pack(fill="x")
        return bar

    def _footer_bar(self, back_screen=None, back_label="← Back"):
        # Thin blue top accent line
        ctk.CTkFrame(self, fg_color=config.COLOR_PRIMARY, height=2, corner_radius=0).pack(fill="x", side="bottom")
        bar = ctk.CTkFrame(self, fg_color=config.COLOR_SURFACE, corner_radius=0, height=75)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        # Home button
        ctk.CTkButton(
            bar, text="🏠  Start Over",
            command=self.app.reset_session,
            font=ctk.CTkFont(family=config.FONT_FAMILY, size=14, weight="bold"),
            fg_color=config.COLOR_ERROR, hover_color="#C01C1C", text_color="#FFFFFF",
            width=150, height=42, corner_radius=8
        ).pack(side="right", padx=20, pady=16)

        if back_screen:
            ctk.CTkButton(
                bar, text=back_label,
                command=lambda: self.app.show_screen(back_screen),
                font=ctk.CTkFont(family=config.FONT_FAMILY, size=14, weight="bold"),
                fg_color=config.COLOR_BG, hover_color=config.COLOR_GLASS,
                text_color=config.COLOR_PRIMARY,
                width=150, height=42, corner_radius=8,
                border_width=2, border_color=config.COLOR_PRIMARY
            ).pack(side="left", padx=20, pady=16)

        return bar

    def speak(self, key: str):
        tts_engine.speak_script(key, self.app.get_lang())


# ═══════════════════════════════════════════════════════════
# Screen 0 — Language Selection
# ═══════════════════════════════════════════════════════════

class LanguageScreen(BaseScreen):

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._build()

    def _build(self):
        # Header
        hdr = ctk.CTkFrame(self, fg_color=config.COLOR_SECONDARY, corner_radius=0)
        hdr.pack(fill="x", ipady=20)
        ctk.CTkLabel(hdr, text="🏦  AI Bank Form Filling Kiosk",
                     font=ctk.CTkFont(family=config.FONT_FAMILY, size=32, weight="bold"),
                     text_color="#FFFFFF").pack()
        ctk.CTkLabel(hdr, text="AI வங்கி படிவ கியோஸ்க்  •  AI बैंक कियोस्क  •  AI బ్యాంక్ కియోస్క్",
                     font=ctk.CTkFont(family=config.FONT_FAMILY, size=16),
                     text_color="#E0E9F4").pack(pady=(4, 0))

        # Content
        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=60, pady=40)

        ctk.CTkLabel(content, text="Please select your language  /  மொழியை தேர்ந்தெடுக்கவும்",
                     font=ctk.CTkFont(family=config.FONT_FAMILY, size=22, weight="bold"),
                     text_color=config.COLOR_PRIMARY).pack(pady=(0, 40))

        # Language grid 3x2
        grid = ctk.CTkFrame(content, fg_color="transparent")
        grid.pack()

        langs = list(config.LANGUAGES.items())
        for idx, (code, info) in enumerate(langs):
            row, col = divmod(idx, 3)
            self._lang_button(grid, code, info).grid(
                row=row, column=col, padx=20, pady=15
            )

        # Footer
        ctk.CTkFrame(self, fg_color=config.COLOR_SECONDARY, height=4, corner_radius=0).pack(fill="x", side="bottom")
        ctk.CTkLabel(self,
                     text="Powered by OpenCV  •  Tesseract OCR  •  Gemini AI",
                     font=ctk.CTkFont(family=config.FONT_FAMILY, size=12),
                     text_color=config.COLOR_SUBTEXT
                     ).pack(side="bottom", pady=10)

    def _lang_button(self, parent, code: str, info: dict):
        frame = ctk.CTkFrame(parent, fg_color=config.COLOR_GLASS,
                             border_width=2, border_color=config.COLOR_GLASS_BORDER,
                             corner_radius=15, width=240, height=160, cursor="hand2")
        frame.grid_propagate(False)

        ctk.CTkLabel(frame, text=info["flag"],
                     font=ctk.CTkFont(size=48)).pack(pady=(15, 0))
        ctk.CTkLabel(frame, text=info["native"],
                     font=ctk.CTkFont(family=config.FONT_FAMILY, size=24, weight="bold"),
                     text_color=config.COLOR_TEXT).pack(pady=(5, 0))
        ctk.CTkLabel(frame, text=info["name"],
                     font=ctk.CTkFont(family=config.FONT_FAMILY, size=14),
                     text_color=config.COLOR_SUBTEXT).pack()

        def _select(c=code, f=frame):
            self.app.language.set(c)
            self._highlight(f)
            tts_engine.speak_script("language_selected", c)
            self.after(1200, lambda: self.app.show_screen("ServiceScreen"))

        for w in [frame] + list(frame.winfo_children()):
            w.bind("<Button-1>", lambda e, fn=_select: fn())

        frame._code = code
        if not hasattr(self, "_lang_frames"):
            self._lang_frames = []
        self._lang_frames.append(frame)
        return frame

    def _highlight(self, selected_frame):
        for f in getattr(self, "_lang_frames", []):
            if f is selected_frame:
                f.configure(border_color=config.COLOR_PRIMARY, border_width=4)
            else:
                f.configure(border_color=config.COLOR_SUBTEXT, border_width=2)

    def on_show(self):
        for f in getattr(self, "_lang_frames", []):
            f.configure(border_color=config.COLOR_SUBTEXT, border_width=2)
        tts_engine.speak_script("welcome", "en")


# ═══════════════════════════════════════════════════════════
# Screen 1 — Service Selection
# ═══════════════════════════════════════════════════════════

class ServiceScreen(BaseScreen):

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._build()

    def _build(self):
        self._topbar("🏦  Select Banking Service")

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=30, pady=20)

        ctk.CTkLabel(content,
                     text="Which service do you need today?",
                     font=ctk.CTkFont(family=config.FONT_FAMILY, size=22, weight="bold"),
                     text_color=config.COLOR_PRIMARY).pack(pady=(0, 20))

        grid = ctk.CTkFrame(content, fg_color="transparent")
        grid.pack()

        self._service_cards = []
        items = list(config.FORM_TYPES.items())
        for idx, (key, info) in enumerate(items):
            row, col = divmod(idx, 4)
            card = self._service_card(grid, key, info)
            card.grid(row=row, column=col, padx=12, pady=12)

        self._footer_bar(back_screen="LanguageScreen")

    def _service_card(self, parent, key: str, info: dict):
        frame = ctk.CTkFrame(parent, fg_color=config.COLOR_GLASS,
                             border_width=2, border_color=config.COLOR_GLASS_BORDER,
                             corner_radius=12, width=220, height=210, cursor="hand2")
        frame.grid_propagate(False)

        # Try load actual image, fallback to icon if missing
        img = self.load_icon_image(info.get("image", ""), size=(90, 70))
        if img:
            ctk.CTkLabel(frame, image=img, text="").pack(pady=(15, 5))
        else:
            ctk.CTkLabel(frame, text=info["icon"], font=ctk.CTkFont(size=42)).pack(pady=(15, 5))

        ctk.CTkLabel(frame, text=info["label"],
                     font=ctk.CTkFont(family=config.FONT_FAMILY, size=16, weight="bold"),
                     text_color=config.COLOR_TEXT, wraplength=200).pack()
        ctk.CTkLabel(frame, text=info["desc"],
                     font=ctk.CTkFont(family=config.FONT_FAMILY, size=12),
                     text_color=config.COLOR_SUBTEXT, wraplength=200).pack(pady=(5, 0))

        def _select(k=key, f=frame):
            self.app.form_type.set(k)
            self._highlight(f)
            self.after(300, lambda: self.app.show_screen("DocumentScreen"))

        for w in [frame] + list(frame.winfo_children()):
            w.bind("<Button-1>", lambda e, fn=_select: fn())

        frame._key = key
        self._service_cards.append(frame)
        return frame

    def _highlight(self, selected):
        for card in self._service_cards:
            if card is selected:
                card.configure(border_color=config.COLOR_PRIMARY, border_width=4)
            else:
                card.configure(border_color=config.COLOR_SUBTEXT, border_width=2)

    def on_show(self):
        for card in self._service_cards:
            card.configure(border_color=config.COLOR_SUBTEXT, border_width=2)
        self.speak("select_service")


# ═══════════════════════════════════════════════════════════
# Screen 2 — Document Type Selection
# ═══════════════════════════════════════════════════════════

class DocumentScreen(BaseScreen):

    _DOCS = [
        ("aadhaar", "assets/aadhaar_icon.png", "Aadhaar Card",  "Name · DOB · Gender · Address"),
        ("pan",     "assets/pan_icon.png", "PAN Card",      "Name · DOB · PAN Number"),
        ("passbook","assets/passbook_icon.png", "Bank Passbook", "Account No · IFSC · Branch"),
    ]

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._cards = []
        self._build()

    def _build(self):
        self._topbar("📄  Select Document Type")

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=60, pady=40)

        ctk.CTkLabel(content,
                     text="Place your document on the scanner and select its type below.",
                     font=ctk.CTkFont(family=config.FONT_FAMILY, size=20, weight="bold"),
                     text_color=config.COLOR_PRIMARY).pack(pady=(0, 40))

        row_frame = ctk.CTkFrame(content, fg_color="transparent")
        row_frame.pack()

        for idx, (value, img_path, title, subtitle) in enumerate(self._DOCS):
            card = self._doc_card(row_frame, value, img_path, title, subtitle)
            card.grid(row=0, column=idx, padx=30, pady=10)

        ctk.CTkButton(
            content, text="▶  Continue to Scan",
            command=lambda: self.app.show_screen("ScanScreen"),
            font=ctk.CTkFont(family=config.FONT_FAMILY, size=18, weight="bold"),
            fg_color=config.COLOR_PRIMARY, hover_color=config.COLOR_SECONDARY,
            text_color="#FFFFFF", width=260, height=55, corner_radius=10
        ).pack(pady=50)

        self._footer_bar(back_screen="ServiceScreen")

    def _doc_card(self, parent, value, img_path, title, subtitle):
        card = ctk.CTkFrame(parent, fg_color=config.COLOR_GLASS,
                            border_width=2, border_color=config.COLOR_GLASS_BORDER,
                            corner_radius=15, width=280, height=220, cursor="hand2")
        card.grid_propagate(False)

        img = self.load_icon_image(img_path, size=(120, 80))
        if img:
            ctk.CTkLabel(card, image=img, text="").pack(pady=(25, 10))
        else:
            ctk.CTkLabel(card, text="📄", font=ctk.CTkFont(size=56)).pack(pady=(25, 10))
            
        ctk.CTkLabel(card, text=title,
                     font=ctk.CTkFont(family=config.FONT_FAMILY, size=20, weight="bold"),
                     text_color=config.COLOR_TEXT).pack()
        ctk.CTkLabel(card, text=subtitle,
                     font=ctk.CTkFont(family=config.FONT_FAMILY, size=13),
                     text_color=config.COLOR_SUBTEXT).pack(pady=(5, 0))

        def _select(v=value, c=card):
            self.app.doc_type.set(v)
            self._refresh_cards()

        for w in [card] + list(card.winfo_children()):
            w.bind("<Button-1>", lambda e, fn=_select: fn())

        card._value = value
        self._cards.append(card)
        return card

    def _refresh_cards(self):
        selected = self.app.doc_type.get()
        for card in self._cards:
            if card._value == selected:
                card.configure(border_color=config.COLOR_PRIMARY, border_width=4)
            else:
                card.configure(border_color=config.COLOR_SUBTEXT, border_width=2)

    def on_show(self):
        self._refresh_cards()
        self.speak("select_document")


# ═══════════════════════════════════════════════════════════
# Screen 3 — Scan / Load Image
# ═══════════════════════════════════════════════════════════

class ScanScreen(BaseScreen):

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._build()

    def _build(self):
        self._topbar("📷  Load & Process Document")

        content = ctk.CTkFrame(self, fg_color="transparent")
        content.pack(fill="both", expand=True, padx=50, pady=30)
        content.grid_columnconfigure(0, weight=5)
        content.grid_columnconfigure(1, weight=4)
        content.grid_rowconfigure(0, weight=1)

        # ── Left: image preview ──────────────────────────
        left = ctk.CTkFrame(content, fg_color=config.COLOR_SURFACE,
                            border_width=2, border_color=config.COLOR_PRIMARY,
                            corner_radius=10)
        left.grid(row=0, column=0, sticky="nsew", padx=(0, 20))
        left.pack_propagate(False)

        ctk.CTkLabel(left, text="Document Preview",
                     font=ctk.CTkFont(family=config.FONT_FAMILY, size=16, weight="bold"),
                     text_color=config.COLOR_SUBTEXT).pack(pady=(15, 10))

        self.preview_label = ctk.CTkLabel(
            left, text="No image loaded\n\nBrowse or capture\nto see preview here",
            font=ctk.CTkFont(family=config.FONT_FAMILY, size=16),
            text_color=config.COLOR_SUBTEXT,
            fg_color=config.COLOR_BG, corner_radius=8
        )
        self.preview_label.pack(fill="both", expand=True, padx=20, pady=(0, 20))

        # ── Right: action panel ──────────────────────────
        right = ctk.CTkFrame(content, fg_color="transparent")
        right.grid(row=0, column=1, sticky="nsew")

        ctk.CTkLabel(right, text="Document Source",
                     font=ctk.CTkFont(family=config.FONT_FAMILY, size=20, weight="bold"),
                     text_color=config.COLOR_TEXT).pack(pady=(0, 10))

        self._doc_type_label = ctk.CTkLabel(right, text="",
                                            font=ctk.CTkFont(family=config.FONT_FAMILY, size=14, weight="bold"),
                                            text_color=config.COLOR_PRIMARY)
        self._doc_type_label.pack(pady=(0, 20))

        btn_font = ctk.CTkFont(family=config.FONT_FAMILY, size=15, weight="bold")
        
        ctk.CTkButton(right, text="📂  Browse for Image File",
                      command=self._browse_file, font=btn_font,
                      fg_color=config.COLOR_PRIMARY, hover_color=config.COLOR_SECONDARY,
                      text_color="#FFFFFF", height=45).pack(fill="x", pady=8)

        ctk.CTkButton(right, text="🗂  Use Default Test Image",
                      command=self._use_default, font=btn_font,
                      fg_color=config.COLOR_SECONDARY, hover_color=config.COLOR_PRIMARY,
                      text_color="#FFFFFF", height=45).pack(fill="x", pady=8)

        ctk.CTkButton(right, text="📸  Capture from Camera",
                      command=self._capture_camera, font=btn_font,
                      fg_color=config.COLOR_SUCCESS, hover_color="#04A87E",
                      text_color="#FFFFFF", height=45).pack(fill="x", pady=8)

        # Status
        self.status_var = tk.StringVar(value="")
        self.status_label = ctk.CTkLabel(
            right, textvariable=self.status_var,
            font=ctk.CTkFont(family=config.FONT_FAMILY, size=14),
            text_color=config.COLOR_WARNING, wraplength=350, justify="left"
        )
        self.status_label.pack(pady=10)

        # Progress bar
        self.progress = ctk.CTkProgressBar(right, mode="indeterminate", width=350)
        self.progress.pack(pady=(0, 10))
        self.progress.set(0)

        # Scan button
        self.scan_btn = ctk.CTkButton(
            right, text="🔍  Run OCR & Extract",
            command=self._run_scan,
            font=ctk.CTkFont(family=config.FONT_FAMILY, size=18, weight="bold"),
            fg_color=config.COLOR_PRIMARY, hover_color=config.COLOR_SECONDARY, text_color="#FFFFFF",
            height=55, corner_radius=10
        )
        self.scan_btn.pack(fill="x", pady=(5, 0))

        # Bottom Bar: Multi-document support
        bar = ctk.CTkFrame(self, fg_color=config.COLOR_SURFACE, corner_radius=0, height=80)
        bar.pack(fill="x", side="bottom")
        bar.pack_propagate(False)

        ctk.CTkButton(
            bar, text="🏠  Start Over", command=self.app.reset_session,
            font=ctk.CTkFont(family=config.FONT_FAMILY, size=15, weight="bold"),
            fg_color="#1A2530", hover_color=config.COLOR_ERROR, text_color="#FFFFFF",
            width=160, height=45
        ).pack(side="left", padx=20, pady=17)

        # Add "Scan Another Proof" button
        self.scan_another_btn = ctk.CTkButton(
            bar, text="➕  Scan Another Proof", command=lambda: self.app.show_screen("DocumentScreen"),
            font=ctk.CTkFont(family=config.FONT_FAMILY, size=15, weight="bold"),
            fg_color=config.COLOR_BG, hover_color="#E0E9F4", text_color=config.COLOR_TEXT,
            width=200, height=45, border_width=1, border_color=config.COLOR_SUBTEXT, state="disabled"
        )
        self.scan_another_btn.pack(side="right", padx=10, pady=17)

        self.review_btn = ctk.CTkButton(
            bar, text="▶  Review Scanned Data", command=lambda: self.app.show_screen("ReviewScreen"),
            font=ctk.CTkFont(family=config.FONT_FAMILY, size=15, weight="bold"),
            fg_color=config.COLOR_SUCCESS, hover_color="#04A87E", text_color="#FFFFFF",
            width=200, height=45, state="disabled"
        )
        self.review_btn.pack(side="right", padx=20, pady=17)

    def on_show(self):
        dt_map = {"aadhaar": "Aadhaar Card", "pan": "PAN Card", "passbook": "Bank Passbook"}
        dt = dt_map.get(self.app.doc_type.get(), "Document")
        
        doc_count = len(self.app.ocr_result) if self.app.ocr_result else 0
        if doc_count > 0:
            self._doc_type_label.configure(text=f"Selected: {dt} (Adding to {doc_count} field(s))")
        else:
            self._doc_type_label.configure(text=f"Selected: {dt}")
            
        self.status_var.set("")
        self.progress.stop()
        self.scan_btn.configure(state="normal")
        self.scan_another_btn.configure(state="disabled" if not self.app.ocr_result else "normal")
        self.review_btn.configure(state="disabled" if not self.app.ocr_result else "normal")
        self.speak("scanning")

    def _set_status(self, msg, color=None):
        color = color or config.COLOR_WARNING
        self.status_var.set(msg)
        self.status_label.configure(text_color=color)
        self.update_idletasks()

    def _show_image(self, path):
        try:
            img = Image.open(path)
            img.thumbnail((450, 350))
            photo = ctk.CTkImage(light_image=img, dark_image=img, size=img.size)
            self.preview_label.configure(image=photo, text="")
        except Exception:
            self.preview_label.configure(text="Preview unavailable", image=None)

    def _browse_file(self):
        path = filedialog.askopenfilename(
            title="Select Document Image",
            filetypes=[("Image files", "*.jpg *.jpeg *.png *.bmp *.tiff *.tif"), ("All files", "*.*")]
        )
        if path:
            self.app.image_path.set(path)
            self._show_image(path)
            self._set_status(f"Loaded: {os.path.basename(path)}", config.COLOR_SUCCESS)

    def _use_default(self):
        dt = self.app.doc_type.get()
        if dt == "aadhaar":
            path = config.DEFAULT_AADHAAR_PATH
        elif dt == "pan":
            path = config.DEFAULT_PAN_PATH
        else:
            path = config.DEFAULT_PASSBOOK_PATH

        if not os.path.exists(path):
            messagebox.showwarning("File Not Found", f"Default image not found:\n{path}")
            return
        self.app.image_path.set(path)
        self._show_image(path)
        self._set_status(f"Loaded: {os.path.basename(path)}", config.COLOR_SUCCESS)

    def _capture_camera(self):
        self._set_status("Capturing from camera…")
        self.progress.start()
        try:
            frame = ocr_engine.capture_from_camera()
            import tempfile, cv2
            tmp = tempfile.NamedTemporaryFile(suffix=".png", delete=False)
            cv2.imwrite(tmp.name, frame)
            self.app.temp_files.append(tmp.name)
            self.app.image_path.set(tmp.name)
            self._show_image(tmp.name)
            self._set_status("Camera capture successful!", config.COLOR_SUCCESS)
        except RuntimeError as e:
            self._set_status(f"Camera error: {e}", config.COLOR_ERROR)
        finally:
            self.progress.stop()

    def _run_scan(self):
        path = self.app.image_path.get()
        if not path or not os.path.exists(path):
            messagebox.showwarning("No Image", "Please load an image first.")
            return

        self.scan_btn.configure(state="disabled")
        self.progress.start()
        self._set_status("Preprocessing image…")

        def _worker():
            try:
                self.after(0, lambda: self._set_status("Extracting with Gemini Vision..."))
                doc_type = self.app.doc_type.get()
                
                # Attempt to use Gemini Vision directly for 100% accuracy
                try:
                    final = ai_helper.enhance_with_vision(path, doc_type)
                    raw_text = final.pop("_raw_text", "Extracted via Gemini Vision")
                    confidence = final.pop("_confidence", 99.9)
                except Exception as vision_exc:
                    # Fallback to local Tesseract + Regex if Vision fails (e.g. no internet)
                    print(f"Vision API failed, falling back to Tesseract: {vision_exc}")
                    self.after(0, lambda: self._set_status("Enhancing image for local OCR…"))
                    processed = ocr_engine.preprocess_image(path)
                    
                    self.after(0, lambda: self._set_status("Running local OCR…"))
                    ocr_result = ocr_engine.run_ocr(processed)
                    raw_text   = ocr_result["text"]
                    confidence = ocr_result["confidence"]

                    self.after(0, lambda: self._set_status("Extracting fields…"))
                    extracted = extractor.extract(raw_text, doc_type)
                    
                    # Try local AI enhancement of raw text
                    final = ai_helper.enhance_with_ai(raw_text, doc_type, extracted)

                # Merge extracted fields into session
                for key, val in final.items():
                    if val and val != "Not found" and key not in ("doc_type", "ai_enhanced", "ai_error"):
                        self.app.ocr_result[key] = val
                        
                self.app.ocr_result["_raw_text"] = raw_text
                self.app.ocr_result["_confidence"] = confidence
                # Append doc type for the final form label
                old_doc = self.app.ocr_result.get("doc_type", "")
                if old_doc and doc_type not in old_doc:
                    self.app.ocr_result["doc_type"] = old_doc + " + " + doc_type
                elif not old_doc:
                    self.app.ocr_result["doc_type"] = doc_type

                self.after(0, self._on_scan_done)

            except Exception as exc:
                self.after(0, lambda: self._on_scan_error(str(exc)))

        threading.Thread(target=_worker, daemon=True).start()

    def _on_scan_done(self):
        self.progress.stop()
        self.scan_another_btn.configure(state="normal")
        self.review_btn.configure(state="normal")
        conf = self.app.ocr_result.get("_confidence", 0)
        self._set_status(f"✅  Done! OCR confidence: {conf:.1f}%", config.COLOR_SUCCESS)
        tts_engine.speak_script("scan_done", self.app.get_lang())
        
        # Give them the choice to scan another or proceed automatically
        if messagebox.askyesno("Scan Successful", "Scan complete!\n\nDo you want to scan another proof (e.g. Aadhaar + Passbook) to combine data?"):
            self.app.show_screen("DocumentScreen")
        else:
            self.app.show_screen("ReviewScreen")

    def _on_scan_error(self, msg):
        self.progress.stop()
        self.scan_btn.configure(state="normal")
        self._set_status(f"❌ Error: {msg}", config.COLOR_ERROR)
        tts_engine.speak_script("error", self.app.get_lang())
        messagebox.showerror("Scan Error", msg)


# ═══════════════════════════════════════════════════════════
# Screen 4 — Review, Edit, Missing Fields & Print
# ═══════════════════════════════════════════════════════════

class ReviewScreen(BaseScreen):

    _SKIP_KEYS = {"doc_type", "date", "_raw_text", "_confidence",
                  "ai_enhanced", "ai_error"}

    _LABELS = {
        "name"          : "Full Name",
        "dob"           : "Date of Birth",
        "gender"        : "Gender",
        "aadhaar_number": "Aadhaar Number",
        "address"       : "Address",
        "holder_name"   : "Account Holder Name",
        "account_no"    : "Account Number",
        "ifsc"          : "IFSC Code",
        "branch"        : "Branch",
        "bank_name"     : "Bank Name",
        "micr"          : "MICR Code",
        "mobile"        : "Mobile Number",
        "pan_number"    : "PAN Number",
        "father_name"   : "Father's Name",
        "amount"        : "Amount (₹)",
        "cheque_no"     : "Cheque Number",
    }

    _NUMERIC_FIELDS = {"mobile", "account_no", "amount", "cheque_no", "aadhaar_number"}

    def __init__(self, parent, app):
        super().__init__(parent, app)
        self._entries  = {}
        self._build()

    def _build(self):
        # Top bar
        topbar = ctk.CTkFrame(self, fg_color=config.COLOR_SUCCESS, corner_radius=0)
        topbar.pack(fill="x", ipady=12)
        ctk.CTkLabel(topbar, text="✅  Review & Confirm Scanned Data",
                     font=ctk.CTkFont(family=config.FONT_FAMILY, size=22, weight="bold"),
                     text_color="#1A0A00").pack()

        # Confidence + AI badge
        self.conf_label = ctk.CTkLabel(
            self, text="",
            font=ctk.CTkFont(family=config.FONT_FAMILY, size=13),
            text_color=config.COLOR_WARNING
        )
        self.conf_label.pack(pady=(10, 0))

        # ── Full width scrollable form area ──────────────
        main_area = ctk.CTkFrame(self, fg_color="transparent")
        main_area.pack(fill="both", expand=True, padx=40, pady=15)

        self.form_frame = ctk.CTkScrollableFrame(
            main_area, fg_color=config.COLOR_GLASS,
            border_width=2, border_color=config.COLOR_GLASS_BORDER, corner_radius=12
        )
        self.form_frame.pack(fill="both", expand=True)

        # ── Bottom bar ───────────────────────────────────
        bottom = ctk.CTkFrame(self, fg_color=config.COLOR_SURFACE, corner_radius=0, height=90)
        bottom.pack(fill="x", side="bottom")
        bottom.pack_propagate(False)

        btn_font = ctk.CTkFont(family=config.FONT_FAMILY, size=15, weight="bold")

        ctk.CTkButton(
            bottom, text="🏠  Start Over",
            command=self.app.reset_session,
            font=btn_font, fg_color=config.COLOR_ERROR, hover_color="#CC2233",
            text_color="#FFFFFF", width=160, height=45
        ).pack(side="left", padx=20, pady=22)

        ctk.CTkButton(
            bottom, text="← Back to Scan",
            command=lambda: self.app.show_screen("ScanScreen"),
            font=btn_font, fg_color=config.COLOR_SECONDARY, hover_color=config.COLOR_PRIMARY,
            text_color="#FFFFFF", width=180, height=45
        ).pack(side="left", padx=10, pady=22)

        self.pdf_status = ctk.CTkLabel(
            bottom, text="",
            font=ctk.CTkFont(family=config.FONT_FAMILY, size=14),
            text_color=config.COLOR_SUCCESS
        )
        self.pdf_status.pack(side="right", padx=15, pady=22)

        ctk.CTkButton(
            bottom, text="🖨  Generate & Print PDF",
            command=self._generate_pdf,
            font=ctk.CTkFont(family=config.FONT_FAMILY, size=18, weight="bold"),
            fg_color=config.COLOR_PRIMARY, hover_color=config.COLOR_SECONDARY,
            text_color="#1A0A00", width=240, height=55, corner_radius=10
        ).pack(side="right", padx=20, pady=17)


    # ── Populate form ────────────────────────────────────

    def on_show(self):
        self._populate_form()
        self.speak("enter_missing")

    def _populate_form(self):
        for w in self.form_frame.winfo_children():
            w.destroy()
        self._entries.clear()

        data = self.app.ocr_result
        if not data:
            ctk.CTkLabel(self.form_frame, text="No data to display.",
                         text_color=config.COLOR_ERROR).pack(pady=20)
            return

        conf = data.get("_confidence", 0)
        ai   = "🤖 AI-Enhanced  " if data.get("ai_enhanced") else ""
        ft   = config.FORM_TYPES.get(self.app.form_type.get(), {})
        form_label = ft.get("label", "Form")
        self.conf_label.configure(
            text=f"{ai}Scans: {data.get('doc_type', '')}  •  Form: {form_label}"
        )

        # Ensure form-required fields are visible even if OCR didn't find them
        for req in ft.get("requires", []):
            if req not in data:
                data[req] = ""

        row_idx = 0
        for key, value in data.items():
            if key in self._SKIP_KEYS:
                continue

            label_text = self._LABELS.get(key, key.replace("_", " ").title())
            is_missing = (value == "Not found" or not value)
            col_val = config.COLOR_WARNING if is_missing else config.COLOR_SUCCESS
            display_val = str(value) if not is_missing else "—"

            # Row frame for each field
            row_frame = ctk.CTkFrame(self.form_frame, fg_color="transparent")
            row_frame.pack(fill="x", padx=20, pady=6)

            # Label
            ctk.CTkLabel(
                row_frame, text=label_text + ":",
                font=ctk.CTkFont(family=config.FONT_FAMILY, size=14, weight="bold"),
                text_color=config.COLOR_SUBTEXT, anchor="w", width=180
            ).pack(side="left", padx=(0, 10))

            # Value display (read-only, clear, large)
            ctk.CTkLabel(
                row_frame, text=display_val,
                font=ctk.CTkFont(family=config.FONT_FAMILY, size=16, weight="bold"),
                text_color=col_val, anchor="w"
            ).pack(side="left", fill="x", expand=True)

            if is_missing:
                ctk.CTkLabel(
                    row_frame, text="(will be filled by hand)",
                    font=ctk.CTkFont(family=config.FONT_FAMILY, size=11),
                    text_color=config.COLOR_SUBTEXT
                ).pack(side="right", padx=5)

            # Divider line
            ctk.CTkFrame(self.form_frame, fg_color=config.COLOR_GLASS_BORDER,
                         height=1, corner_radius=0).pack(fill="x", padx=20)

            self._entries[key] = tk.StringVar(value=value if not is_missing else "")
            row_idx += 1

        self.form_frame.grid_columnconfigure(1, weight=1)

    def _generate_pdf(self):
        # ── SHOW PAYMENT POPUP FIRST ──
        payment_window = ctk.CTkToplevel(self)
        payment_window.title("Payment Required")
        payment_window.geometry("500x350")
        payment_window.attributes("-topmost", True)
        payment_window.grab_set()  # Focus on popup

        # Center the window
        payment_window.update_idletasks()
        x = (payment_window.winfo_screenwidth() // 2) - (500 // 2)
        y = (payment_window.winfo_screenheight() // 2) - (350 // 2)
        payment_window.geometry(f"+{x}+{y}")

        # Content
        ctk.CTkLabel(payment_window, text="💳 Payment Required",
                     font=ctk.CTkFont(family=config.FONT_FAMILY, size=24, weight="bold"),
                     text_color=config.COLOR_PRIMARY).pack(pady=(30, 10))

        ctk.CTkLabel(payment_window, text="Please insert a ₹5 coin into the machine\nto print your form.",
                     font=ctk.CTkFont(family=config.FONT_FAMILY, size=16),
                     text_color=config.COLOR_TEXT).pack(pady=(10, 30))

        def _on_coin_inserted():
            payment_window.destroy()
            self._process_pdf_generation()

        # Simulate hardware coin inserted
        ctk.CTkButton(payment_window, text="🪙 Simulate Coin Inserted",
                      command=_on_coin_inserted,
                      font=ctk.CTkFont(family=config.FONT_FAMILY, size=18, weight="bold"),
                      fg_color=config.COLOR_SUCCESS, hover_color="#0BA070",
                      text_color="#FFFFFF", height=55, width=280).pack(pady=10)

        ctk.CTkButton(payment_window, text="Cancel",
                      command=payment_window.destroy,
                      font=ctk.CTkFont(family=config.FONT_FAMILY, size=14),
                      fg_color="transparent", text_color=config.COLOR_ERROR, hover_color=config.COLOR_SURFACE).pack(pady=10)

    def _process_pdf_generation(self):
        form_type = self.app.form_type.get()
        ft_cfg = config.FORM_TYPES.get(form_type, {})

        data = dict(self.app.ocr_result)
        for key, var in self._entries.items():
            val = var.get().strip()
            data[key] = val

        default_name = f"bank_form_{form_type}.pdf"
        path = filedialog.asksaveasfilename(
            title="Save Bank Form PDF",
            initialdir=config.PDF_OUTPUT_DIR,
            initialfile=default_name,
            defaultextension=".pdf",
            filetypes=[("PDF files", "*.pdf"), ("All files", "*.*")]
        )
        if not path:
            return

        try:
            out = form_generator.generate_form_by_type(data, form_type, path)

            conf = self.app.ocr_result.get("_confidence", 0)
            db_logger.log_transaction(
                doc_type=data.get("doc_type", ""),
                form_type=ft_cfg.get("label", form_type),
                language=self.app.get_lang(),
                status="completed",
                ocr_confidence=conf,
            )

            tts_engine.speak_script("print_done", self.app.get_lang())
            self.pdf_status.configure(text="✅  PDF Saved!", text_color=config.COLOR_SUCCESS)

            result = messagebox.askyesno(
                "PDF Generated",
                f"Form saved successfully:\n{out}\n\n"
                "Would you like to open it for printing?"
            )
            if result:
                os.startfile(out)

            if messagebox.askyesno("Transaction Complete", "Transaction complete.\n\nStart a new transaction?"):
                self.app.reset_session()

        except Exception as e:
            self.pdf_status.configure(text="❌ Error", text_color=config.COLOR_ERROR)
            tts_engine.speak_script("error", self.app.get_lang())
            messagebox.showerror("PDF Error", str(e))


# ═══════════════════════════════════════════════════════════
# Entry point
# ═══════════════════════════════════════════════════════════

if __name__ == "__main__":
    app = KioskApp()
    app.mainloop()
    tts_engine.stop()
