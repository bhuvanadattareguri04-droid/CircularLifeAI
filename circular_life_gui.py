"""
CircularLife AI — Desktop GUI
Powered by Groq API (openai/gpt-oss-20b)

Run:
    python circular_life_gui.py
"""

from __future__ import annotations

import re
import threading
import tkinter as tk
from tkinter import ttk

from dotenv import load_dotenv

# Load .env before importing the backend so GROQ_API_KEY is available.
load_dotenv()

from circular_life import build_client, analyse_item  # noqa: E402

# ── Colour palette ────────────────────────────────────────────────────────────

C = {
    "bg":             "#F5F7F2",
    "surface":        "#FFFFFF",
    "surface_warn":   "#FFF3E0",
    "surface_hazard": "#FFEBEE",
    "surface_safe":   "#E8F5E9",
    "surface_summary":"#EEF4FF",
    "border":         "#DDE3D8",
    "border_warn":    "#FFB300",
    "border_hazard":  "#E53935",
    "border_safe":    "#43A047",
    "border_summary": "#3B82D4",
    "header_bg":      "#1B4332",
    "header_fg":      "#FFFFFF",
    "subtitle_fg":    "#A8D5B5",
    "accent":         "#2D6A4F",
    "accent_light":   "#40916C",
    "btn_fg":         "#FFFFFF",
    "btn_clear_bg":   "#E8F0E9",
    "btn_clear_fg":   "#2D6A4F",
    "btn_new_bg":     "#EEF4FF",
    "btn_new_fg":     "#3B82D4",
    "text_main":      "#1A2E1A",
    "text_muted":     "#5A7363",
    "warn_fg":        "#7B3F00",
    "hazard_hdr":     "#C62828",
    "hazard_badge":   "#D32F2F",
    "safe_hdr":       "#2E7D32",
    "placeholder":    "#9DB5A5",
}

# Maps the model's ## markers to (emoji, display heading).
SECTION_META: list[tuple[str, str, str]] = [
    ("## 1. Item Identification",     "🔎", "ITEM ANALYSIS"),
    ("## 2. Safety Check",            "🛡️", "SAFETY CHECK"),
    ("## 3. Circular Decision",       "♻️", "CIRCULAR PATHWAY"),
    ("## 4. Repurposing Suggestions", "💡", "SECOND-LIFE IDEAS"),
    ("## 5. Step-by-Step Guidance",   "📋", "STEP-BY-STEP GUIDE"),
    ("## 6. Sustainability Note",     "🌍", "SUSTAINABILITY IMPACT"),
    ("## 7. Disposal Note",           "🗑️", "DISPOSAL GUIDANCE"),
]

# All 7 section markers must be present for a response to be considered complete.
_ALL_MARKERS = [m for m, _, _ in SECTION_META]

# ── Text helpers ──────────────────────────────────────────────────────────────

# Unicode dash/hyphen variants the model may emit instead of ASCII hyphen.
_DASH_RE = re.compile(r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212\ufe58\ufe63\uff0d]")


def _normalize_dashes(text: str) -> str:
    """Replace all Unicode dash variants with ASCII hyphen for reliable matching."""
    return _DASH_RE.sub("-", text)


def _strip_markdown(text: str) -> str:
    """Remove common Markdown decorators so only plain text reaches the GUI."""
    # Remove bold/italic markers: **, __, *, _
    text = re.sub(r"\*{1,3}|_{1,3}", "", text)
    # Remove heading markers (## ... at start of line)
    text = re.sub(r"^\s*#{1,6}\s*", "", text, flags=re.MULTILINE)
    # Remove horizontal rules
    text = re.sub(r"^\s*[-*_]{3,}\s*$", "", text, flags=re.MULTILINE)
    # Collapse 3+ blank lines to 2
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def _extract_inline(text: str, label: str) -> str:
    """
    Pull the value from a bullet like '- Item name: Ceramic flower pot'.
    Returns the value, or '' if not found.
    """
    pattern = re.compile(
        r"[-*]\s*" + re.escape(label) + r"\s*[:\-]\s*(.+)", re.IGNORECASE
    )
    m = pattern.search(text)
    return m.group(1).strip() if m else ""


# ── Hazard detection ──────────────────────────────────────────────────────────

def _normalize_for_hazard(text: str) -> str:
    """Strip Markdown formatting before hazard detection to handle bold variations."""
    # Remove bold/italic so "**Yes**" becomes "Yes", "**hazardous?** Yes" works
    return re.sub(r"\*{1,3}|_{1,3}", "", text)


# Explicit YES answer on the hazard question (after markdown normalization).
_HAZARD_YES_RE = re.compile(
    r"""
    (?:
        potentially\s+hazardous\??\s*[:\-]?\s*yes       # hazardous? yes (inline)
        | hazardous[?:]?\s*[:\-]?\s*yes                  # hazardous: yes
        | (?:^|\n)\s*[-*]\s*yes\b                        # bullet: yes
        | \byes[,.]?\s+this\s+item\s+is\s+(?:potentially\s+)?hazardous
        # "hazardous?\n  yes" — answer on its own line after the question
        | potentially\s+hazardous\?[^\n]*\n\s*yes\b
        | hazardous\?[^\n]*\n\s*yes\b
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)

# Explicit NO answer — vetoes any YES match.
# Patterns are intentionally tight: they must appear on a direct answer line
# or as a clearly negative statement about the hazard question itself.
# We deliberately exclude generic phrases like "safe to handle normally" that
# can appear as conditional boilerplate inside a hazardous response.
_HAZARD_NO_RE = re.compile(
    r"""
    (?:
        # Direct answer bullet: "- potentially hazardous? no"
        potentially\s+hazardous\??\s*[:\-]?\s*no
        |
        # Direct field answer: "hazardous: no" / "hazardous? no"
        hazardous[?:]?\s*[:\-]?\s*no
        |
        # Standalone bullet answer: "- no" / "* no"
        (?:^|\n)\s*[-*]\s*no\b
        |
        # "This item is not hazardous" / "not potentially hazardous"
        \bthis\s+item\s+is\s+not\s+(?:potentially\s+)?hazardous\b
        |
        # "no hazard identified"
        \bno\s+hazard\b
    )
    """,
    re.IGNORECASE | re.VERBOSE,
)


def _is_hazardous(safety_body: str) -> bool:
    """
    Return True only when the Safety Check section explicitly answers YES.
    Markdown bold markers are stripped first so **Yes** / **No** are handled.
    Explicit NO always vetoes an ambiguous YES.
    """
    normalized = _normalize_for_hazard(safety_body)
    has_yes = bool(_HAZARD_YES_RE.search(normalized))
    has_no  = bool(_HAZARD_NO_RE.search(normalized))
    return has_yes and not has_no


# ── Deterministic input-side hazard guard ─────────────────────────────────────
# This check runs on the RAW USER INPUT — before any LLM output is examined.
# It is intentionally simple and conservative: if the user's own description
# contains well-known hazardous-condition phrases, we treat the item as
# hazardous regardless of what the LLM says.  The LLM is probabilistic; this
# guard is deterministic and cannot be overridden by an unexpected model reply.

_INPUT_HAZARD_PHRASES: list[re.Pattern[str]] = [
    re.compile(p, re.IGNORECASE) for p in [
        r"\bswollen\b.{0,40}\bbatter",          # swollen battery / swollen li-ion battery
        r"\bbatter.{0,40}\bswollen\b",           # battery … swollen
        r"\bbulging\b.{0,40}\bbatter",           # bulging battery
        r"\bbatter.{0,40}\bbulging\b",
        r"\bleaking\b.{0,40}\bbatter",           # leaking battery
        r"\bbatter.{0,40}\bleaking\b",
        r"\bpunctured\b.{0,40}\bbatter",         # punctured battery
        r"\bbatter.{0,40}\bpunctured\b",
        r"\bsmoking\b.{0,40}\bbatter",           # smoking battery
        r"\bbatter.{0,40}\bsmoking\b",
        r"\boverheating\b.{0,40}\bbatter",       # overheating battery
        r"\bbatter.{0,40}\boverheating\b",
        r"\bburning\b.{0,40}\bbatter",           # burning battery
        r"\bbatter.{0,40}\bburning\b",
        r"\bbatter.{0,20}\bfire\b",              # battery fire
        r"\bfire\b.{0,20}\bbatter",
        r"\bdamaged\b.{0,40}\bbatter",           # damaged battery
        r"\bbatter.{0,40}\bdamaged\b",
        r"\bexposed\b.{0,40}\bbatter",           # exposed battery
        r"\bcracked\b.{0,40}\bbatter",           # cracked battery
        r"\bleaking\b.{0,40}\belectrolyte",      # leaking electrolyte
        r"\bleaking\b.{0,40}\bchemical",         # leaking chemical
        r"\blithium.{0,10}ion\b.{0,40}\bswollen",
        r"\bswollen\b.{0,40}\blithium",          # swollen lithium
    ]
]


def _input_is_hazardous(description: str) -> bool:
    """Deterministic hazard check on the user's raw input text.

    Returns True if the description contains any well-known hazardous-condition
    phrase (swollen battery, leaking battery, etc.).  This result ALWAYS takes
    priority over the LLM-derived is_hazard flag — the model cannot override it.
    """
    for pattern in _INPUT_HAZARD_PHRASES:
        if pattern.search(description):
            return True
    return False


# ── Response parsing ──────────────────────────────────────────────────────────

# Sections that are suppressed for hazardous items — their absence is acceptable.
_DIY_MARKERS = {"## 4. Repurposing Suggestions", "## 5. Step-by-Step Guidance"}

# Sections that must always be present regardless of hazard status.
_REQUIRED_MARKERS = [m for m in _ALL_MARKERS if m not in _DIY_MARKERS]


def _is_complete(raw: str, is_hazard: bool = False) -> bool:
    """Return True when all required section markers are present.

    For hazardous responses the DIY sections (4 & 5) are optional — the
    hazardous prompt tells the model to fill them with refusal text, but
    we do not fail completeness validation if they are absent.
    Normalises Unicode dashes before checking.
    """
    normalised = _normalize_dashes(raw)
    markers_to_check = _REQUIRED_MARKERS if is_hazard else _ALL_MARKERS
    return all(marker in normalised for marker in markers_to_check)


def _split_sections(raw: str) -> list[tuple[str, str, str]]:
    """
    Parse the model response into (emoji, display_heading, cleaned_body) tuples.
    Falls back to a single raw block if no section markers are recognised.
    """
    sections: list[tuple[str, str, str]] = []
    # Normalise dashes once so all marker lookups work regardless of hyphen variant.
    remaining = _normalize_dashes(raw)

    for i, (marker, emoji, heading) in enumerate(SECTION_META):
        idx = remaining.find(marker)
        if idx == -1:
            continue

        after_marker = remaining[idx + len(marker):]

        # Find the start of the next known section marker.
        next_idx = len(after_marker)
        for next_marker, _, _ in SECTION_META[i + 1:]:
            ni = after_marker.find(next_marker)
            if ni != -1 and ni < next_idx:
                next_idx = ni

        body = after_marker[:next_idx].strip()
        body = re.sub(r"^\s*[:\-]\s*", "", body, count=1)  # strip leading colon/dash
        body = _strip_markdown(body)
        sections.append((emoji, heading, body))
        remaining = after_marker[next_idx:]

    if not sections:
        sections = [("📄", "AI RESPONSE", _strip_markdown(raw))]
    return sections


def _build_summary(sections: list[tuple[str, str, str]], is_hazard: bool) -> dict:
    """
    Extract the compact summary fields from the parsed sections.
    Returns a dict with keys: item, material, condition, status, pathway.
    """
    item = material = condition = pathway = ""

    for _, heading, body in sections:
        if "ITEM ANALYSIS" in heading:
            item      = _extract_inline(body, "Item name")
            material  = _extract_inline(body, "Primary material")
            condition = _extract_inline(body, "Estimated condition")
        elif "CIRCULAR PATHWAY" in heading:
            # First non-empty line usually starts with the action word.
            for line in body.splitlines():
                line = line.strip().lstrip("-* ")
                if line:
                    pathway = line
                    break

    return {
        "item":      item      or "Item",
        "material":  material  or "",
        "condition": condition or "",
        "status":    "HAZARDOUS ⚠" if is_hazard else "SAFE ✓",
        "pathway":   pathway   or "See results below",
    }


# ── Scrollable frame ──────────────────────────────────────────────────────────

class _ScrollFrame(tk.Frame):
    """A vertically scrollable container backed by a Canvas."""

    def __init__(self, parent: tk.Misc, **kw):
        super().__init__(parent, bg=C["bg"], **kw)

        self._canvas = tk.Canvas(self, bg=C["bg"], highlightthickness=0, bd=0)
        self._scrollbar = ttk.Scrollbar(
            self, orient="vertical", command=self._canvas.yview
        )
        self.inner = tk.Frame(self._canvas, bg=C["bg"])

        self._win_id = self._canvas.create_window(
            (0, 0), window=self.inner, anchor="nw"
        )
        self._canvas.configure(yscrollcommand=self._scrollbar.set)
        self._scrollbar.pack(side="right", fill="y")
        self._canvas.pack(side="left", fill="both", expand=True)

        self.inner.bind("<Configure>", self._on_inner_configure)
        self._canvas.bind("<Configure>", self._on_canvas_configure)
        self._canvas.bind_all("<MouseWheel>", self._on_mousewheel)
        self._canvas.bind_all("<Button-4>",   self._on_mousewheel)
        self._canvas.bind_all("<Button-5>",   self._on_mousewheel)

    def _on_inner_configure(self, _event=None):
        self._canvas.configure(scrollregion=self._canvas.bbox("all"))

    def _on_canvas_configure(self, event):
        self._canvas.itemconfig(self._win_id, width=event.width)

    def _on_mousewheel(self, event):
        if event.num == 4:
            self._canvas.yview_scroll(-1, "units")
        elif event.num == 5:
            self._canvas.yview_scroll(1, "units")
        else:
            self._canvas.yview_scroll(int(-event.delta / 120), "units")

    def scroll_to_top(self):
        self._canvas.yview_moveto(0)


# ── Summary card ──────────────────────────────────────────────────────────────

class _SummaryCard(tk.Frame):
    """Compact top-of-results card: ANALYSIS COMPLETE + key fields."""

    def __init__(self, parent: tk.Widget, summary: dict, **kw):
        is_hazard = "HAZARDOUS" in summary["status"]
        bg     = C["surface_hazard"] if is_hazard else C["surface_summary"]
        border = C["border_hazard"]  if is_hazard else C["border_summary"]
        super().__init__(parent, bg=bg,
                         highlightbackground=border, highlightthickness=2, **kw)

        # Header strip
        hdr_bg = C["hazard_hdr"] if is_hazard else C["accent"]
        hdr = tk.Frame(self, bg=hdr_bg)
        hdr.pack(fill="x")

        check = "⚠" if is_hazard else "✓"
        tk.Label(
            hdr,
            text=f"  {check}  ANALYSIS COMPLETE",
            bg=hdr_bg,
            fg=C["header_fg"],
            font=("Segoe UI", 11, "bold"),
            padx=14, pady=8,
            anchor="w",
        ).pack(side="left")

        # Body grid
        body = tk.Frame(self, bg=bg)
        body.pack(fill="x", padx=16, pady=10)

        fields = [
            ("Item",      summary["item"]),
            ("Status",    summary["status"]),
            ("Pathway",   summary["pathway"]),
        ]
        if summary["condition"]:
            fields.insert(1, ("Condition", summary["condition"]))

        for row, (label, value) in enumerate(fields):
            tk.Label(
                body,
                text=label + ":",
                bg=bg,
                fg=C["text_muted"],
                font=("Segoe UI", 9, "bold"),
                anchor="w",
            ).grid(row=row, column=0, sticky="w", padx=(0, 12), pady=2)

            fg = C["hazard_hdr"] if (label == "Status" and is_hazard) else C["text_main"]
            tk.Label(
                body,
                text=value,
                bg=bg,
                fg=fg,
                font=("Segoe UI", 9),
                anchor="w",
                wraplength=620,
                justify="left",
            ).grid(row=row, column=1, sticky="w", pady=2)


# ── Hazard banner ─────────────────────────────────────────────────────────────

class _HazardBanner(tk.Frame):
    """Full-width red hazard warning shown above all section cards."""

    def __init__(self, parent: tk.Widget, **kw):
        super().__init__(parent, bg=C["hazard_badge"], **kw)

        tk.Label(
            self,
            text="⚠   HAZARDOUS ITEM DETECTED",
            bg=C["hazard_badge"],
            fg="#FFFFFF",
            font=("Segoe UI", 12, "bold"),
            padx=16, pady=10,
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            self,
            text=(
                "Do not attempt to open, puncture, disassemble, modify, or repurpose "
                "this item yourself.\n"
                "Do not place it in regular household waste.\n"
                "Take it to an appropriate e-waste, hazardous-material, or professional "
                "recycling facility. Follow the precautions in the Safety Check section below."
            ),
            bg="#B71C1C",
            fg="#FFEBEE",
            font=("Segoe UI", 10),
            padx=16, pady=10,
            justify="left",
            wraplength=780,
            anchor="nw",
        ).pack(fill="x")


# ── Section card ──────────────────────────────────────────────────────────────

class _SectionCard(tk.Frame):
    """One result card: coloured header strip + plain-text body."""

    def __init__(self, parent: tk.Widget, emoji: str, heading: str,
                 body: str, is_hazard: bool = False, **kw):

        is_safety = "SAFETY" in heading
        if is_safety and is_hazard:
            bg, border, hdr_bg = C["surface_hazard"], C["border_hazard"], C["hazard_hdr"]
        elif is_safety and not is_hazard:
            bg, border, hdr_bg = C["surface_safe"],   C["border_safe"],   C["safe_hdr"]
        else:
            bg, border, hdr_bg = C["surface"],        C["border"],        C["accent"]

        super().__init__(parent, bg=bg,
                         highlightbackground=border, highlightthickness=1, **kw)

        # Header
        hdr = tk.Frame(self, bg=hdr_bg)
        hdr.pack(fill="x")

        tk.Label(
            hdr,
            text=f"  {emoji}  {heading}",
            bg=hdr_bg,
            fg=C["header_fg"],
            font=("Segoe UI", 11, "bold"),
            padx=14, pady=8,
            anchor="w",
        ).pack(side="left")

        if is_safety and is_hazard:
            tk.Label(
                hdr,
                text="  ⚠  HAZARDOUS",
                bg=C["hazard_badge"],
                fg="#FFFFFF",
                font=("Segoe UI", 9, "bold"),
                padx=8, pady=4,
            ).pack(side="right", padx=(0, 6))
        elif is_safety and not is_hazard:
            tk.Label(
                hdr,
                text="  ✓  SAFE",
                bg=C["safe_hdr"],
                fg="#FFFFFF",
                font=("Segoe UI", 9, "bold"),
                padx=8, pady=4,
            ).pack(side="right", padx=(0, 6))

        # Body
        body_frame = tk.Frame(self, bg=bg)
        body_frame.pack(fill="both", expand=True, padx=16, pady=12)

        body_fg = C["hazard_hdr"] if (is_safety and is_hazard) else C["text_main"]
        body_text = tk.Text(
            body_frame,
            bg=bg,
            fg=body_fg,
            font=("Segoe UI", 10),
            wrap="word",
            relief="flat",
            bd=0,
            padx=0,
            pady=0,
            cursor="arrow",
            state="normal",
            height=1,
        )

        # For hazardous safety cards, prepend an explicit safety notice.
        display_body = body
        if is_safety and is_hazard:
            notice = (
                "SAFETY NOTICE: Do not open, puncture, disassemble, or attempt to "
                "repurpose this item. Handle with care and dispose of it through an "
                "appropriate professional, e-waste, or hazardous-material facility.\n\n"
            )
            display_body = notice + body

        body_text.insert("1.0", display_body)
        body_text.configure(state="disabled")

        line_count = int(body_text.index("end-1c").split(".")[0])
        body_text.configure(height=max(line_count, 2))
        body_text.pack(fill="both", expand=True)


# ── Main application ──────────────────────────────────────────────────────────

class CircularLifeApp(tk.Tk):

    def __init__(self):
        super().__init__()
        self.title("CircularLife AI")
        self.geometry("880x800")
        self.minsize(660, 580)
        self.configure(bg=C["bg"])

        try:
            self.iconbitmap(default="")
        except Exception:
            pass

        self._client = None
        self._busy   = False

        self._build_ui()
        self._init_client()

    # ── UI construction ───────────────────────────────────────────────────────

    def _build_ui(self):
        self._build_header()
        self._build_input_panel()
        self._build_results_panel()

    def _build_header(self):
        hdr = tk.Frame(self, bg=C["header_bg"])
        hdr.pack(fill="x")

        inner = tk.Frame(hdr, bg=C["header_bg"])
        inner.pack(fill="x", padx=28, pady=18)

        tk.Label(
            inner,
            text="♻  CircularLife AI",
            bg=C["header_bg"],
            fg=C["header_fg"],
            font=("Segoe UI", 20, "bold"),
            anchor="w",
        ).pack(anchor="w")

        tk.Label(
            inner,
            text="Give old products a second life.",
            bg=C["header_bg"],
            fg=C["subtitle_fg"],
            font=("Segoe UI", 11),
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

        tk.Label(
            inner,
            text="AI-powered circular economy assistant",
            bg=C["header_bg"],
            fg="#6BAF85",
            font=("Segoe UI", 9),
            anchor="w",
        ).pack(anchor="w", pady=(2, 0))

    def _build_input_panel(self):
        panel = tk.Frame(self, bg=C["bg"])
        panel.pack(fill="x", padx=24, pady=18)

        tk.Label(
            panel,
            text="What item do you want to handle responsibly?",
            bg=C["bg"],
            fg=C["text_main"],
            font=("Segoe UI", 11, "bold"),
            anchor="w",
        ).pack(anchor="w", pady=(0, 6))

        # Bordered input wrapper — uses place() so the placeholder label can
        # float over the Text widget without inserting text into it.
        input_border = tk.Frame(
            panel,
            bg=C["border"],
            highlightbackground=C["border"],
            highlightthickness=1,
        )
        input_border.pack(fill="x")

        self._input_text = tk.Text(
            input_border,
            height=5,
            font=("Segoe UI", 10),
            bg=C["surface"],
            fg=C["text_main"],
            relief="flat",
            bd=0,
            padx=12,
            pady=10,
            wrap="word",
            insertbackground=C["accent"],
        )
        self._input_text.pack(fill="x", padx=1, pady=1)

        # True placeholder: a Label placed *over* the Text widget.
        # The Text widget itself is always empty while the placeholder shows.
        # This means self._input_text.get() is NEVER polluted with placeholder text.
        self._placeholder_label = tk.Label(
            input_border,
            text=(
                "Example:\nI have an old cracked ceramic flower pot that I "
                "want to reuse in my garden."
            ),
            bg=C["surface"],
            fg=C["placeholder"],
            font=("Segoe UI", 10),
            justify="left",
            anchor="nw",
        )
        # Place over the Text widget; offset matches padx=12, pady=10 of the Text.
        self._placeholder_label.place(x=13, y=11)
        self._placeholder_active = True

        # Clicking the overlay label should focus the real Text widget.
        self._placeholder_label.bind("<Button-1>", lambda e: self._input_text.focus_set())

        self._input_text.bind("<FocusIn>",  self._on_focus_in)
        self._input_text.bind("<FocusOut>", self._on_focus_out)
        # Also hide placeholder on any key press (belt-and-suspenders).
        self._input_text.bind("<Key>",      self._on_key)

        # Button row
        btn_row = tk.Frame(panel, bg=C["bg"])
        btn_row.pack(fill="x", pady=(10, 0))

        self._analyze_btn = tk.Button(
            btn_row,
            text="  🔍  Analyze Item",
            command=self._on_analyze,
            bg=C["accent"],
            fg=C["btn_fg"],
            activebackground=C["accent_light"],
            activeforeground=C["btn_fg"],
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            bd=0,
            padx=20,
            pady=9,
            cursor="hand2",
        )
        self._analyze_btn.pack(side="left", padx=(0, 10))

        self._clear_btn = tk.Button(
            btn_row,
            text="  ✕  Clear",
            command=self._on_clear,
            bg=C["btn_clear_bg"],
            fg=C["btn_clear_fg"],
            activebackground=C["border"],
            activeforeground=C["accent"],
            font=("Segoe UI", 10),
            relief="flat",
            bd=0,
            padx=16,
            pady=9,
            cursor="hand2",
        )
        self._clear_btn.pack(side="left")

        self._status_var = tk.StringVar(value="")
        self._status_lbl = tk.Label(
            btn_row,
            textvariable=self._status_var,
            bg=C["bg"],
            fg=C["text_muted"],
            font=("Segoe UI", 9, "italic"),
        )
        self._status_lbl.pack(side="left", padx=(16, 0))

    def _build_results_panel(self):
        sep = tk.Frame(self, bg=C["border"], height=1)
        sep.pack(fill="x")

        lbl_frame = tk.Frame(self, bg=C["bg"])
        lbl_frame.pack(fill="x", padx=24, pady=(14, 4))

        tk.Label(
            lbl_frame,
            text="Analysis Results",
            bg=C["bg"],
            fg=C["text_muted"],
            font=("Segoe UI", 9, "bold"),
        ).pack(anchor="w")

        self._scroll_frame = _ScrollFrame(self)
        self._scroll_frame.pack(fill="both", expand=True, padx=24, pady=(0, 16))

        self._show_empty_state()

    # ── Placeholder helpers ───────────────────────────────────────────────────

    def _show_empty_state(self):
        self._clear_results()
        tk.Label(
            self._scroll_frame.inner,
            text=(
                "Enter an item description above and press\n"
                "\"🔍  Analyze Item\" to get started."
            ),
            bg=C["bg"],
            fg=C["placeholder"],
            font=("Segoe UI", 11),
            justify="center",
        ).pack(expand=True, pady=60)

    def _clear_results(self):
        for child in self._scroll_frame.inner.winfo_children():
            child.destroy()

    # ── Input placeholder behaviour ───────────────────────────────────────────
    # The placeholder is a tk.Label overlay — the Text widget stays EMPTY while
    # the placeholder is visible.  _placeholder_active tracks which state we're in.
    # Reading self._input_text.get() is therefore always safe and clean.

    def _show_placeholder(self):
        """Show the overlay label and mark placeholder as active."""
        self._placeholder_label.place(x=13, y=11)
        self._placeholder_active = True

    def _hide_placeholder(self):
        """Remove the overlay label and mark placeholder as inactive."""
        self._placeholder_label.place_forget()
        self._placeholder_active = False

    def _on_focus_in(self, _event=None):
        """Hide placeholder as soon as the text box receives focus."""
        if self._placeholder_active:
            self._hide_placeholder()

    def _on_focus_out(self, _event=None):
        """Restore placeholder when user leaves the box and it is empty."""
        if not self._input_text.get("1.0", "end").strip():
            self._show_placeholder()

    def _on_key(self, _event=None):
        """Belt-and-suspenders: hide placeholder on any keypress."""
        if self._placeholder_active:
            self._hide_placeholder()

    # ── Client init ───────────────────────────────────────────────────────────

    def _init_client(self):
        try:
            self._client = build_client()
        except EnvironmentError as exc:
            self._show_config_error(str(exc))

    def _show_config_error(self, message: str):
        self._clear_results()
        card = tk.Frame(
            self._scroll_frame.inner,
            bg=C["surface_warn"],
            highlightbackground=C["border_warn"],
            highlightthickness=1,
        )
        card.pack(fill="x", padx=4, pady=8)

        tk.Label(
            card,
            text="⚙  Configuration Required",
            bg=C["warn_icon_bg"] if "warn_icon_bg" in C else "#FF8F00",
            fg=C["header_fg"],
            font=("Segoe UI", 11, "bold"),
            padx=14, pady=8,
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            card,
            text=message,
            bg=C["surface_warn"],
            fg=C["warn_fg"],
            font=("Segoe UI", 10),
            justify="left",
            wraplength=700,
            padx=16, pady=12,
            anchor="nw",
        ).pack(fill="x")

        self._analyze_btn.configure(state="disabled")

    # ── Analyze action ────────────────────────────────────────────────────────

    def _on_analyze(self):
        if self._busy:
            return
        if self._client is None:
            self._init_client()
            if self._client is None:
                return

        client = self._client  # narrowed: Groq (None already excluded above)

        # With the overlay-label placeholder, the Text widget is always truly
        # empty when no user input has been entered — so a plain .get() is safe.
        description = self._input_text.get("1.0", "end").strip()

        if not description:
            self._set_status("⚠  Please describe the item first.", error=True)
            self._input_text.focus_set()
            return

        self._busy = True
        self._analyze_btn.configure(state="disabled", text="  ⏳  Analysing…")
        self._clear_btn.configure(state="disabled")
        self._set_status("Connecting to Groq API…")
        self._clear_results()
        self._show_loading_indicator()

        def worker():
            try:
                raw = analyse_item(client, description)
                # Pass description so _display_results can apply the
                # deterministic hazard override on the user's own words.
                self.after(0, lambda: self._display_results(raw, description))
            except Exception as exc:  # noqa: BLE001
                self.after(0, lambda: self._show_api_error(str(exc)))

        threading.Thread(target=worker, daemon=True).start()

    def _show_loading_indicator(self):
        tk.Label(
            self._scroll_frame.inner,
            text="🔄  Analysing your item…\n\nThis may take a few seconds.",
            bg=C["bg"],
            fg=C["text_muted"],
            font=("Segoe UI", 11),
            justify="center",
        ).pack(expand=True, pady=60)

    def _on_clear(self):
        if self._busy:
            return
        # 1. Wipe the real text widget — guaranteed empty, no placeholder text.
        self._input_text.delete("1.0", "end")
        # 2. Show the overlay placeholder label (no text inserted into the widget).
        self._show_placeholder()
        # 3. Reset the results area to the initial empty state.
        self._show_empty_state()
        # 4. Clear the status line.
        self._set_status("")

    def _set_status(self, text: str, error: bool = False):
        self._status_var.set(text)
        self._status_lbl.configure(fg="#C62828" if error else C["text_muted"])

    def _reset_buttons(self):
        self._busy = False
        self._analyze_btn.configure(state="normal", text="  🔍  Analyze Item")
        self._clear_btn.configure(state="normal")

    # ── Result rendering ──────────────────────────────────────────────────────

    def _display_results(self, raw: str, description: str = ""):
        # ── Deterministic hazard override from the user's own input ──────────
        # This fires BEFORE any LLM output is read.  If the user's description
        # contains known hazardous phrases (swollen battery, leaking battery,
        # etc.) we lock input_forced_hazard = True and the LLM cannot override it.
        input_forced_hazard = _input_is_hazardous(description)

        # ── Preliminary LLM-based hazard check (for completeness gating only) ─
        # Used only to decide which marker set to validate against (_REQUIRED vs
        # _ALL_MARKERS).  The final status badge is decided further below.
        safety_raw_match = re.search(
            r"## 2\. Safety Check(.+?)(?=## 3\.|\Z)", _normalize_dashes(raw), re.DOTALL | re.IGNORECASE
        )
        safety_raw = safety_raw_match.group(1) if safety_raw_match else ""
        is_hazard = _is_hazardous(safety_raw) or input_forced_hazard

        # ── Truncation guard ──────────────────────────────────────────────────
        if not raw:
            self._reset_buttons()
            self._set_status("⚠  Empty response received.", error=True)
            self._show_inline_error(
                "The AI returned an empty response. Please try again."
            )
            return

        if not _is_complete(raw, is_hazard=is_hazard):
            normalised = _normalize_dashes(raw)
            markers_to_check = _REQUIRED_MARKERS if is_hazard else _ALL_MARKERS
            missing = [m for m in markers_to_check if m not in normalised]
            self._reset_buttons()
            self._set_status("⚠  Incomplete response.", error=True)
            self._show_inline_error(
                "Analysis could not be completed because the AI response was "
                "incomplete (missing sections: "
                + ", ".join(missing)
                + ").\n\nPlease try again."
            )
            return

        # ── Parse ─────────────────────────────────────────────────────────────
        sections = _split_sections(raw)

        # ── Final status decision ─────────────────────────────────────────────
        # The STATUS badge (HAZARDOUS ⚠ vs SAFE ✓) is governed by a strict
        # priority order:
        #
        #   1. input_forced_hazard = True  → ALWAYS HAZARDOUS, no exceptions.
        #      (deterministic keyword match on the user's own words)
        #
        #   2. input_forced_hazard = False → SAFE, regardless of what the LLM
        #      wrote in Section 2.  The LLM can hallucinate "yes" when RAG
        #      context mentions batteries; we must not let that override the
        #      deterministic guard.
        #
        # The LLM's Section 2 text is still displayed verbatim — we only
        # override the STATUS BADGE and the DIY-suppression gate.
        is_hazard = input_forced_hazard

        summary = _build_summary(sections, is_hazard)

        # ── Application-level safety gate ─────────────────────────────────────
        # Sections that must NEVER be shown for hazardous items, regardless of
        # what the model returned.
        _DIY_HEADINGS = {"SECOND-LIFE IDEAS", "STEP-BY-STEP GUIDE"}

        # ── Render (top → bottom order matters for pack) ──────────────────────
        self._clear_results()
        self._scroll_frame.scroll_to_top()

        # 1. Hazard banner (only when hazardous) — rendered FIRST so it appears at top.
        if is_hazard:
            _HazardBanner(self._scroll_frame.inner).pack(
                fill="x", padx=4, pady=(0, 8)
            )

        # 2. Summary card.
        _SummaryCard(self._scroll_frame.inner, summary).pack(
            fill="x", padx=4, pady=(0, 10)
        )

        # 3. Section cards — with application-level safety gate.
        for emoji, heading, body in sections:
            # ── SAFETY GATE: suppress DIY sections for hazardous items ────────
            if is_hazard and heading in _DIY_HEADINGS:
                continue  # never render DIY content for hazardous items

            card_is_hazard = is_hazard and "SAFETY" in heading
            _SectionCard(
                self._scroll_frame.inner,
                emoji=emoji,
                heading=heading,
                body=body,
                is_hazard=card_is_hazard,
            ).pack(fill="x", padx=4, pady=(0, 10))

        # 4. "New Analysis" button at the bottom.
        btn_frame = tk.Frame(self._scroll_frame.inner, bg=C["bg"])
        btn_frame.pack(fill="x", padx=4, pady=(6, 4))

        tk.Button(
            btn_frame,
            text="  ✦  New Analysis",
            command=self._on_new_analysis,
            bg=C["btn_new_bg"],
            fg=C["btn_new_fg"],
            activebackground=C["border_summary"],
            activeforeground="#FFFFFF",
            font=("Segoe UI", 10, "bold"),
            relief="flat",
            bd=0,
            padx=20,
            pady=9,
            cursor="hand2",
        ).pack(side="left")

        # Bottom spacer.
        tk.Frame(self._scroll_frame.inner, bg=C["bg"], height=20).pack()

        # ── Finalise ──────────────────────────────────────────────────────────
        self._reset_buttons()
        status = "⚠  Analysis complete — HAZARDOUS ITEM." if is_hazard else "✔  Analysis complete."
        self._set_status(status, error=is_hazard)

    def _show_inline_error(self, message: str):
        """Show a friendly error card inside the results area (not a crash)."""
        self._clear_results()
        card = tk.Frame(
            self._scroll_frame.inner,
            bg=C["surface_warn"],
            highlightbackground=C["border_warn"],
            highlightthickness=1,
        )
        card.pack(fill="x", padx=4, pady=8)

        tk.Label(
            card,
            text="⚠  Analysis Error",
            bg="#FF8F00",
            fg=C["header_fg"],
            font=("Segoe UI", 11, "bold"),
            padx=14, pady=8,
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            card,
            text=message,
            bg=C["surface_warn"],
            fg=C["warn_fg"],
            font=("Segoe UI", 10),
            justify="left",
            wraplength=700,
            padx=16, pady=12,
            anchor="nw",
        ).pack(fill="x")

    def _on_new_analysis(self):
        """Clear results and return focus to the input box."""
        self._show_empty_state()
        self._set_status("")
        # Show the placeholder only if the box is empty, then focus it.
        # _on_focus_in will hide the placeholder when focus arrives.
        if not self._input_text.get("1.0", "end").strip():
            self._show_placeholder()
        self._input_text.focus_set()

    def _show_api_error(self, message: str):
        self._reset_buttons()
        self._set_status("⚠  Request failed — see results panel.", error=True)

        self._clear_results()
        card = tk.Frame(
            self._scroll_frame.inner,
            bg=C["surface_warn"],
            highlightbackground=C["border_warn"],
            highlightthickness=1,
        )
        card.pack(fill="x", padx=4, pady=8)

        tk.Label(
            card,
            text="⚠  API Error",
            bg="#FF8F00",
            fg=C["header_fg"],
            font=("Segoe UI", 11, "bold"),
            padx=14, pady=8,
            anchor="w",
        ).pack(fill="x")

        tk.Label(
            card,
            text=(
                f"{message}\n\n"
                "Unable to complete the analysis. "
                "Please check your API connection and GROQ_API_KEY, then try again."
            ),
            bg=C["surface_warn"],
            fg=C["warn_fg"],
            font=("Segoe UI", 10),
            justify="left",
            wraplength=700,
            padx=16, pady=12,
            anchor="nw",
        ).pack(fill="x")


# ── Entry point ───────────────────────────────────────────────────────────────

def main():
    app = CircularLifeApp()
    app.mainloop()


if __name__ == "__main__":
    main()
