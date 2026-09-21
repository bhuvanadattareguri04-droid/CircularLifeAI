"""
CircularLife AI — Terminal Prototype
Powered by Groq API (openai/gpt-oss-20b)

Workflow:
  1. Identify item, material, and condition
  2. Safety check (hazardous / non-hazardous)
  3. Repair / Reuse / Repurpose / Recycle decision
  4. Practical, personalised repurposing suggestions
  5. Step-by-step guidance
"""

import os
import sys
import logging
from groq import Groq
from dotenv import load_dotenv

logger = logging.getLogger(__name__)

load_dotenv()

# ── Configuration ────────────────────────────────────────────────────────────

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")
MODEL_ID     = "openai/gpt-oss-20b"

# ── Prompt templates ─────────────────────────────────────────────────────────

SYSTEM_PROMPT = (
    "You are CircularLife AI, an expert in sustainable waste reduction and the "
    "circular economy. You help people repair, reuse, repurpose, and recycle "
    "household and everyday items. You always prioritise safety first.\n\n"
    "IMPORTANT SAFETY RULE: If the item is potentially hazardous — such as a "
    "swollen or damaged battery, exposed electrical components, unknown chemicals, "
    "or dangerously sharp materials — you must clearly flag the hazards and "
    "required precautions BEFORE any other advice. Do NOT provide DIY "
    "disassembly or handling instructions for such items. Instead, direct the "
    "user to the appropriate professional disposal or recycling facility.\n\n"
    "SAFETY OVERRIDE: If an item is hazardous or contains a hazardous component "
    "(including but not limited to: swollen/damaged/leaking batteries, exposed "
    "electrical wiring, corrosive or toxic chemicals, pressurised containers, "
    "high-voltage components, or potentially explosive materials), you MUST NOT "
    "provide DIY disassembly, repair, modification, extraction, removal, or "
    "repurposing instructions of any kind. Do NOT suggest projects that require "
    "accessing or removing the hazardous component. Return safety precautions, "
    "professional handling/recycling guidance, and disposal guidance ONLY."
)

# ── Section markers (duplicated here to avoid a circular import with the GUI) ─
# These must exactly match the heading strings used in circular_life_gui.py.

_ALL_MARKERS = [
    "## 1. Item Identification",
    "## 2. Safety Check",
    "## 3. Circular Decision",
    "## 4. Repurposing Suggestions",
    "## 5. Step-by-Step Guidance",
    "## 6. Sustainability Note",
    "## 7. Disposal Note",
]
_DIY_MARKERS = {"## 4. Repurposing Suggestions", "## 5. Step-by-Step Guidance"}
_REQUIRED_MARKERS = [m for m in _ALL_MARKERS if m not in _DIY_MARKERS]

# ── Standard prompt (safe items) ─────────────────────────────────────────────

USER_PROMPT_TEMPLATE = """A user has an item they want to handle responsibly.

Item description:
{description}

{rag_section}IMPORTANT: You MUST produce ALL 7 sections below in order. Every section is mandatory.
Keep each section concise (2-5 lines for sections 1-3 and 6-7, up to 8 lines for sections 4-5).
Use EXACTLY the heading format shown (e.g. "## 1. Item Identification"). Do not rename, skip, or merge any section.

## 1. Item Identification
- Item name:
- Primary material(s):
- Estimated condition (good / fair / poor / end-of-life):

## 2. Safety Check
- Is this item potentially hazardous? (yes / no)
- If yes, list the specific hazards and mandatory safety precautions. Do NOT provide DIY instructions for dangerous items.
- If no, confirm it is safe to handle normally.

## 3. Circular Decision
Recommend ONE primary action: Repair, Reuse, Repurpose, or Recycle. One or two sentences explaining why.

## 4. Repurposing Suggestions
List 2-3 practical suggestions achievable at home. Keep each to one or two sentences.

## 5. Step-by-Step Guidance
For the top suggestion above, give 4-6 numbered steps a beginner can follow. Keep each step brief.

## 6. Sustainability Note
One or two sentences on the environmental benefit of this choice.

## 7. Disposal Note
One or two sentences on how to dispose of or recycle this item responsibly if needed.
"""

# ── Hazardous-item prompt (omits DIY sections 4 & 5) ─────────────────────────

HAZARDOUS_USER_PROMPT_TEMPLATE = """A user has an item they want to handle responsibly.

Item description:
{description}

{rag_section}SAFETY NOTICE: This item has been identified as potentially hazardous.
Do NOT provide any DIY instructions, repurposing suggestions, component-removal
steps, or disassembly guidance. Provide safety information and disposal guidance only.

IMPORTANT: You MUST produce ALL 7 sections below in order. Every section is mandatory.
Keep each section concise (2-4 lines) so that all 7 sections fit within a single response.
Use EXACTLY the heading format shown. Do not rename, skip, or merge any section.

## 1. Item Identification
- Item name:
- Primary material(s):
- Estimated condition (good / fair / poor / end-of-life):

## 2. Safety Check
- Is this item potentially hazardous? (yes / no)
- List every specific hazard. Do NOT provide DIY handling, opening, or repurposing instructions.
- List mandatory safety precautions.

## 3. Circular Decision
Recommend ONE action: Recycle or Safe Disposal / Professional Handling. One sentence on why.

## 4. Repurposing Suggestions
State: "Due to the hazardous nature of this item, DIY repurposing is not recommended."

## 5. Step-by-Step Guidance
State: "No DIY guidance is provided for hazardous items. Please follow the disposal guidance below."

## 6. Sustainability Note
One sentence on why professional recycling/disposal is the most sustainable choice.

## 7. Disposal Note
Two to three sentences on how to safely dispose of or recycle this item (e.g. certified e-waste facility, battery recycling point). Include what NOT to do.
"""

# ── Client initialisation ────────────────────────────────────────────────────

def build_client() -> Groq:
    """Validate env vars and return an initialised Groq client.

    Raises EnvironmentError when GROQ_API_KEY is missing so that both the
    terminal entry-point and the GUI can handle the error gracefully.
    """
    if not GROQ_API_KEY:
        raise EnvironmentError(
            "GROQ_API_KEY is not set.\n"
            "Copy .env.example to .env and add your Groq API key."
        )
    return Groq(api_key=GROQ_API_KEY)

# ── Core analysis ────────────────────────────────────────────────────────────

def _call_model(client: Groq, prompt: str, max_tokens: int = 4096) -> str:
    """Low-level model call. Returns stripped response text."""
    response = client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user",   "content": prompt},
        ],
        temperature=0.3,
        max_tokens=max_tokens,
    )
    return (response.choices[0].message.content or "").strip()


import re as _re
_DASH_NORM_RE = _re.compile(
    r"[\u2010\u2011\u2012\u2013\u2014\u2015\u2212\ufe58\ufe63\uff0d]"
)

def _normalize_dashes_local(text: str) -> str:
    """Normalise Unicode dash variants to ASCII hyphen for section-marker matching."""
    return _DASH_NORM_RE.sub("-", text)


def _continuation_prompt(partial: str, missing_markers: list[str]) -> str:
    """Build a forceful retry prompt that asks for only the missing sections."""
    section_list = "\n".join(f"  {m}" for m in missing_markers)
    return (
        "Your previous response was incomplete. "
        "The following required sections are missing:\n"
        f"{section_list}\n\n"
        "You MUST now generate ONLY those missing sections. "
        "Use the exact heading format (e.g. '## 6. Sustainability Note'). "
        "Each section must contain real content — 2 to 4 sentences. "
        "Do NOT repeat sections that were already provided. "
        "Do NOT add any preamble or explanation — start immediately with the first missing heading.\n\n"
        "Here is the end of your previous response for context:\n"
        + partial[-600:]
    )


def _complete_response(client: Groq, prompt: str, is_hazardous: bool = False) -> str:
    """
    Call the model and auto-retry once with a continuation prompt if any
    required sections are missing from the first response.
    Uses locally defined markers — no import from circular_life_gui needed.
    Returns the combined raw text ready for the GUI parser.
    """
    raw = _call_model(client, prompt)

    markers_to_check = _REQUIRED_MARKERS if is_hazardous else _ALL_MARKERS
    normalised = _normalize_dashes_local(raw)
    missing = [m for m in markers_to_check if m not in normalised]

    if not missing:
        return raw  # complete on first try — most common path

    # One retry: ask the model to produce only the missing sections
    continuation = _continuation_prompt(raw, missing)
    extra = _call_model(client, continuation, max_tokens=1200)
    combined = raw.rstrip() + "\n\n" + extra.strip()
    return combined


def _quick_hazard_check(client: Groq, description: str) -> bool:
    """
    Run a minimal single-question safety pre-check to decide which prompt
    template to use.  Returns True if the item is actively hazardous.
    This is intentionally fast: a short answer is all we need.

    Only items with ACTIVE hazards (swollen/leaking batteries, exposed wiring,
    corrosive chemicals, etc.) should return True.  An old laptop with a weak
    battery is NOT hazardous — only flag it if the battery is swollen/leaking/smoking.
    """
    probe = (
        f"Item: {description.strip()}\n\n"
        "Does this item have an ACTIVE, IMMEDIATE hazard right now? "
        "Active hazards include: a swollen, leaking, smoking, or punctured battery; "
        "exposed live electrical wiring or components; unknown/corrosive/toxic chemicals; "
        "pressurised or potentially explosive containers; or material confirmed to be "
        "actively dangerous to handle.\n"
        "A normal old laptop with a weak battery is NOT hazardous. "
        "A laptop with a visibly swollen or leaking battery IS hazardous.\n"
        "Answer with ONLY 'yes' or 'no'."
    )
    response = client.chat.completions.create(
        model=MODEL_ID,
        messages=[
            {"role": "system", "content": "You are a safety triage assistant. Answer only yes or no. Be conservative — only answer yes for items with an active, immediate physical hazard."},
            {"role": "user",   "content": probe},
        ],
        temperature=0.0,
        max_tokens=10,
    )
    answer = (response.choices[0].message.content or "").strip().lower()
    return answer.startswith("yes")


def _get_rag_context(description: str) -> str:
    """Retrieve relevant circular-economy guidance from the local knowledge base.

    Uses sentence-transformers + cosine similarity (see rag/retriever.py).
    Returns an empty string on any failure so the rest of the pipeline is
    completely unaffected if RAG is unavailable.
    """
    try:
        from rag.retriever import build_rag_context  # noqa: PLC0415
        return build_rag_context(description)
    except Exception as exc:  # noqa: BLE001
        logger.warning("RAG context retrieval skipped: %s", exc)
        return ""


def analyse_item(client: Groq, description: str) -> str:
    """
    Two-pass analysis with application-level safety gate, plus auto-retry
    for missing sections.  RAG context is retrieved first and injected into
    the prompt as a clearly labelled reference block so the LLM has relevant
    circular-economy guidance available without confusing it with the item
    description itself.

    Pass 1 - quick hazard pre-check (single yes/no question).
    Pass 2 - full analysis using either:
              HAZARDOUS_USER_PROMPT_TEMPLATE  (if hazardous)
              USER_PROMPT_TEMPLATE            (if safe)
    If sections are missing after pass 2, a single continuation call fills them.

    Returns the raw model text (potentially combined from two calls).
    """
    # ── RAG: retrieve relevant guidance from the local knowledge base ─────────
    # Best-effort: if RAG fails for any reason the analysis continues normally.
    rag_context = _get_rag_context(description)

    # Build a clearly labelled rag_section string.
    # It is passed as a SEPARATE template variable so the model can clearly
    # distinguish "what the user described" from "background reference material".
    # When RAG is unavailable, rag_section is empty and the prompt is unchanged.
    if rag_context:
        rag_section = (
            "Relevant background information for your reference "
            "(use this to improve accuracy; do not repeat it verbatim):\n"
            f"{rag_context}\n\n"
        )
    else:
        rag_section = ""

    # ── Pass 1: deterministic keyword check on the user's raw input ───────────
    # This is a hard rule: if the description contains known hazardous phrases
    # (swollen battery, leaking battery, etc.) we bypass the LLM pre-check and
    # force the hazardous prompt path.  The LLM check is only used for cases
    # that the keyword list does not cover.
    try:
        from circular_life_gui import _input_is_hazardous  # noqa: PLC0415
        is_hazardous_prelim = _input_is_hazardous(description)
    except Exception:  # noqa: BLE001
        is_hazardous_prelim = False

    if not is_hazardous_prelim:
        # Keyword check did not fire — fall back to the LLM pre-check.
        is_hazardous_prelim = _quick_hazard_check(client, description)

    # ── Pass 2: full structured analysis ─────────────────────────────────────
    if is_hazardous_prelim:
        prompt = HAZARDOUS_USER_PROMPT_TEMPLATE.format(
            description=description.strip(),
            rag_section=rag_section,
        )
    else:
        prompt = USER_PROMPT_TEMPLATE.format(
            description=description.strip(),
            rag_section=rag_section,
        )

    return _complete_response(client, prompt, is_hazardous=is_hazardous_prelim)

# ── UI helpers ───────────────────────────────────────────────────────────────

DIVIDER = "─" * 60

def print_banner() -> None:
    print(f"\n{'═' * 60}")
    print("  ♻  CircularLife AI  — Powered by Groq")
    print(f"{'═' * 60}")
    print("  Give your items a second life. Reduce. Reuse. Repurpose.")
    print(f"{'═' * 60}\n")

def print_divider() -> None:
    print(f"\n{DIVIDER}\n")

def get_item_description() -> str:
    """Prompt the user for an item description; allow multi-line input."""
    print("Describe the item you want to handle responsibly.")
    print("Include as much detail as you can: what it is, its material,")
    print("its current condition, and any damage or defects.")
    print("(Press Enter twice when done)\n")

    lines = []
    while True:
        line = input("  > " if not lines else "    ")
        if line == "" and lines and lines[-1] == "":
            break
        lines.append(line)

    return " ".join(l for l in lines if l).strip()

def ask_again() -> bool:
    """Ask whether the user wants to analyse another item."""
    print_divider()
    answer = input("Analyse another item? (y / n): ").strip().lower()
    return answer in ("y", "yes")

# ── Main loop ────────────────────────────────────────────────────────────────

def main() -> None:
    print_banner()

    print("Connecting to Groq API …")
    try:
        client = build_client()
    except EnvironmentError as exc:
        sys.exit(f"[ERROR] {exc}")
    print(f"Model ready: {MODEL_ID}\n")

    while True:
        print_divider()
        description = get_item_description()

        if not description:
            print("[WARN] No description entered. Please try again.")
            continue

        print_divider()
        print("Analysing your item — this may take a few seconds …\n")

        try:
            result = analyse_item(client, description)
        except Exception as exc:  # noqa: BLE001
            print(f"[ERROR] The model returned an error:\n  {exc}")
            if not ask_again():
                break
            continue

        print(result)

        if not ask_again():
            break

    print_divider()
    print("Thank you for choosing the circular path. ♻")
    print(f"{'═' * 60}\n")


if __name__ == "__main__":
    main()
