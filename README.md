# ♻ CircularLife AI

A polished desktop application that helps you give everyday items a second life.  
Powered by the **Groq API** (`openai/gpt-oss-20b`).

---

## Features

| Feature | Detail |
|---|---|
| 🔎 Item Analysis | Identifies item, primary material, and condition |
| 🛡️ Safety Check | Flags hazardous items with mandatory precautions |
| ♻️ Circular Pathway | Recommends Repair · Reuse · Repurpose · Recycle |
| 💡 Second-Life Ideas | 2–4 practical, at-home repurposing suggestions |
| 📋 Step-by-Step Guide | Beginner-friendly instructions for the top idea |
| 🌍 Sustainability Impact | Explains the environmental benefit of the choice |
| 🗑️ Disposal Guidance | Responsible disposal path for end-of-life items |
| ⚠️ Hazard Warnings | Full-width red banner + blocked DIY for dangerous items |

---

## Requirements

| Dependency | Version |
|---|---|
| Python | ≥ 3.10 |
| groq | ≥ 0.9 |
| python-dotenv | ≥ 1.0 |
| tkinter | bundled with Python |

> **Note:** `tkinter` is included with the standard CPython installer on  
> Windows and macOS. On Linux install it with `sudo apt install python3-tk`.

---

## Installation

### 1. Clone or download the project

```bash
git clone https://github.com/your-org/circularlife-ai.git
cd circularlife-ai
```

### 2. Create a virtual environment (recommended)

```bash
python -m venv .venv
# Windows
.venv\Scripts\activate
# macOS / Linux
source .venv/bin/activate
```

### 3. Install dependencies

```bash
pip install groq python-dotenv
```

---

## Configuration

```bash
cp .env.example .env
```

Open `.env` and set your Groq API key:

```
GROQ_API_KEY=your_groq_api_key_here
```

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Your Groq API key |

> **Get a free API key:** <https://console.groq.com/keys>

The API key is read at startup from `.env` via `python-dotenv`.  
It is **never** displayed in the GUI or written to any file.

---

## How to run

### Desktop GUI (recommended)

```bash
python circular_life_gui.py
```

### Terminal (original prototype)

```bash
python circular_life.py
```

---

## Project structure

```
circularlife-ai/
├── circular_life.py       # Core AI logic + terminal entry-point
├── circular_life_gui.py   # Tkinter desktop GUI
├── .env.example           # Credential template (safe to commit)
├── .env                   # Your credentials   (never commit)
└── README.md              # This file
```

---

## Example inputs

```
An old wooden chair with a broken leg and peeling paint.
```
```
A cracked terracotta flower pot I want to reuse in my garden.
```
```
A pile of old newspapers and cardboard boxes from moving house.
```
```
An old smartphone with a cracked screen that no longer powers on.
```
```
A swollen lithium-ion laptop battery.
```

---

## Safety behavior

CircularLife AI prioritises safety above all else.

If the item is identified as potentially hazardous — including:

- Swollen or damaged lithium-ion batteries
- Exposed electrical wiring or components
- Unknown or dangerous chemicals
- Toxic materials
- Dangerously sharp objects
- Potentially explosive or flammable materials

The application will:

1. Display a prominent **full-width red hazard banner** at the top of the results
2. Show a **⚠ HAZARDOUS ITEM** badge on the Safety Check card
3. List the specific hazards and **mandatory precautions**
4. Set the Circular Pathway to **"Safe Disposal / Professional Handling"**
5. **Not** provide any DIY disassembly or repurposing instructions

---

## AI components

| Component | Detail |
|---|---|
| Provider | Groq API |
| Model | `openai/gpt-oss-20b` |
| System prompt | Analysis-first, safety-first circular economy expert |
| Temperature | 0.3 (focused, consistent output) |
| Max tokens | 800 |

---

## License

MIT © CircularLife AI contributors
