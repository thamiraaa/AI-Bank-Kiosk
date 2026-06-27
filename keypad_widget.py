"""
keypad_widget.py — Reusable on-screen keypad components using CustomTkinter.

Provides a NumericKeypad and an AlphaKeypad (QWERTY layout)
for touchscreen input without a physical keyboard.
"""

import customtkinter as ctk

class BaseKeypad(ctk.CTkFrame):
    """Base class for on-screen keypads."""

    def __init__(self, parent, target_var, on_confirm=None, **kwargs):
        super().__init__(parent, fg_color="transparent", **kwargs)
        self.target_var = target_var
        self.on_confirm = on_confirm
        self._build_keys()

    def _build_keys(self):
        """Implemented by subclasses."""
        pass

    def _on_key(self, char):
        current = self.target_var.get()
        if char == "⌫":
            self.target_var.set(current[:-1])
        elif char == "Space":
            self.target_var.set(current + " ")
        elif char == "Clear":
            self.target_var.set("")
        elif char == "Done":
            if self.on_confirm:
                self.on_confirm(self.target_var.get())
        else:
            self.target_var.set(current + char)


class NumericKeypad(BaseKeypad):

    def _build_keys(self):
        keys = [
            ["7", "8", "9"],
            ["4", "5", "6"],
            ["1", "2", "3"],
            ["Clear", "0", "⌫"],
            ["Done"]
        ]

        for r, row in enumerate(keys):
            self.grid_rowconfigure(r, weight=1)
            # Full width "Done" button
            if len(row) == 1:
                btn = ctk.CTkButton(
                    self, text=row[0], font=("Segoe UI", 16, "bold"),
                    fg_color="#06D6A0", hover_color="#04A87E", text_color="#1B2A3F",
                    command=lambda c=row[0]: self._on_key(c)
                )
                btn.grid(row=r, column=0, columnspan=3, padx=4, pady=4, sticky="nsew")
                continue

            for c, char in enumerate(row):
                self.grid_columnconfigure(c, weight=1)

                fg = "#0077B6"
                hover = "#00B4D8"
                if char == "Clear":
                    fg = "#EF476F"
                    hover = "#FF809B"
                elif char == "⌫":
                    fg = "#FFD166"
                    hover = "#FFE099"
                    
                btn = ctk.CTkButton(
                    self, text=char, font=("Segoe UI", 16, "bold"),
                    fg_color=fg, hover_color=hover, text_color="#FFFFFF" if char != "⌫" else "#1B2A3F",
                    command=lambda k=char: self._on_key(k)
                )
                btn.grid(row=r, column=c, padx=4, pady=4, sticky="nsew")


class AlphaKeypad(BaseKeypad):

    def _build_keys(self):
        rows = [
            ["1", "2", "3", "4", "5", "6", "7", "8", "9", "0", "⌫"],
            ["Q", "W", "E", "R", "T", "Y", "U", "I", "O", "P"],
            ["A", "S", "D", "F", "G", "H", "J", "K", "L"],
            ["Z", "X", "C", "V", "B", "N", "M"],
            ["Clear", "Space", "Done"]
        ]

        for r, row in enumerate(rows):
            self.grid_rowconfigure(r, weight=1)
            row_frame = ctk.CTkFrame(self, fg_color="transparent")
            row_frame.grid(row=r, column=0, sticky="nsew", pady=2)

            for c, char in enumerate(row):
                row_frame.grid_columnconfigure(c, weight=1)
                
                fg = "#1B2A3F"
                hover = "#2D4460"
                text_col = "#E0E9F4"
                
                if char == "Clear":
                    fg = "#EF476F"
                    hover = "#FF809B"
                elif char == "Done":
                    fg = "#06D6A0"
                    hover = "#04A87E"
                    text_col = "#1B2A3F"
                elif char == "⌫":
                    fg = "#FFD166"
                    hover = "#FFE099"
                    text_col = "#1B2A3F"

                btn = ctk.CTkButton(
                    row_frame, text=char, font=("Segoe UI", 14, "bold"),
                    fg_color=fg, hover_color=hover, text_color=text_col,
                    border_width=1, border_color="#8DA9C4",
                    command=lambda k=char: self._on_key(k)
                )
                btn.grid(row=0, column=c, padx=2, sticky="nsew")

