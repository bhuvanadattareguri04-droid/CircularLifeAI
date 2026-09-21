# ♻ CircularLife AI

A polished desktop application that helps users give everyday items a second life through AI-powered analysis and sustainable recommendations.

Powered by the **Groq API** using the `openai/gpt-oss-20b` model.

---

## Problem Statement

> **How might we use AI to guide people toward the most sustainable second-life or disposal option for everyday items so that we can reduce unnecessary waste and promote responsible consumption?**

Everyday items are often thrown away when they become old, damaged, or no longer useful — even when they could be repaired, reused, repurposed, recycled, or safely disposed of through the right channel. People may also be unsure whether an item is safe to handle at all, or which disposal method is appropriate for their situation.

CircularLife AI addresses this challenge by using AI to analyse an item description and recommend a suitable sustainable pathway, while always prioritising safety first.

### Sustainability Goal

This project primarily supports:

**SDG 12 – Responsible Consumption and Production**

CircularLife AI promotes responsible consumption by encouraging repair, reuse, repurposing, recycling, and responsible disposal of everyday items. By surfacing the most sustainable option for each item, the application helps users make informed choices rather than defaulting to landfill.

---

## Features

| Feature | Detail |
|---|---|
| 🔎 Item Analysis | Identifies the item, primary material, and estimated condition |
| 🛡️ Safety Check | Flags potentially hazardous items and lists mandatory precautions |
| ♻️ Circular Pathway | Recommends one primary action: Repair, Reuse, Repurpose, Recycle, or Safe Disposal |
| 💡 Second-Life Ideas | Provides 2–3 practical, at-home repurposing suggestions for safe items |
| 📋 Step-by-Step Guide | Beginner-friendly numbered instructions for the top suggestion |
| 🌍 Sustainability Impact | Explains the environmental benefit of the recommended choice |
| 🗑️ Disposal Guidance | Responsible disposal or recycling guidance for end-of-life items |
| ⚠️ Hazard Warnings | Full-width red hazard banner and blocked DIY guidance for dangerous items |

---

## How It Works

1. The user types a description of an everyday item — what it is, its material, condition, and any damage.
2. A deterministic keyword check runs on the description to identify known hazardous conditions (e.g. swollen batteries) before any API call is made.
3. The application retrieves relevant circular-economy guidance from a local knowledge base using semantic similarity (RAG — see below).
4. The item description and retrieved context are sent to the Groq API for structured analysis.
5. The AI produces a seven-section response covering identification, safety, pathway, suggestions, guidance, sustainability, and disposal.
6. If any required sections are missing from the first response, the application automatically retries with a targeted continuation prompt.
7. The GUI parses the response and renders each section as a styled card.
8. Hazardous items receive a prominent red banner and DIY sections are suppressed; safe items receive the full second-life and step-by-step content.

---

## RAG — Local Knowledge Retrieval

CircularLife AI includes a simple local Retrieval-Augmented Generation (RAG) layer that runs entirely on-device with no external service.

**How it works:**

1. A knowledge base (`rag/knowledge_base/recycle_guidelines.txt`) contains circular-economy guidance covering smartphones, laptops, batteries, lithium-ion batteries, e-waste, plastics, metals, paper, donation, repair, recycling, and safety rules.
2. On the first analysis, the knowledge base is split into paragraph chunks and each chunk is embedded using the `all-MiniLM-L6-v2` sentence-transformer model (~80 MB, downloaded automatically from HuggingFace on first use and cached locally).
3. The user's description is embedded with the same model and cosine similarity is computed against all chunk embeddings in memory.
4. The top-3 most relevant chunks are retrieved and added to the Groq prompt as labelled background context.
5. The chunk cache is kept in memory for the lifetime of the process — the model is loaded once and reused for every subsequent analysis.

**RAG is a best-effort enhancement.** If the embedding model or knowledge base is unavailable for any reason, the application falls back to the standard Groq analysis without interruption.

---

## Safety Behaviour

CircularLife AI prioritises safety above all else.

A deterministic keyword guard scans the user's input for known hazardous-condition phrases before the Groq API is called. Conditions detected include:

- Swollen, bulging, leaking, punctured, or smoking battery
- Overheating or burning battery
- Battery fire
- Damaged battery
- Exposed battery
- Leaking electrolyte or chemical

If any of these are detected, the application:

1. Selects the hazardous prompt template — no DIY repurposing or step-by-step instructions are requested from the model.
2. Displays a prominent **full-width red hazard banner** at the top of the results.
3. Shows a **HAZARDOUS ⚠** status badge on the summary card.
4. Lists the specific hazards and mandatory safety precautions.
5. Recommends professional handling, e-waste facilities, or certified battery recycling — never DIY disassembly.
6. Suppresses the Second-Life Ideas and Step-by-Step Guide sections from the rendered output.

For items not caught by the keyword guard, a quick LLM pre-check (single yes/no question to the model) is run as a secondary check.

The **HAZARDOUS** status badge is always determined by the deterministic keyword guard — the LLM response cannot downgrade a hazardous classification to SAFE.

---

## Requirements

| Dependency | Minimum version | Notes |
|---|---|---|
| Python | 3.10 | |
| `groq` | ≥ 0.9.0 | Groq Python SDK |
| `python-dotenv` | ≥ 1.0.0 | Loads `.env` at startup |
| `sentence-transformers` | ≥ 2.7.0 | Local RAG embeddings |
| `numpy` | ≥ 1.24.0 | Cosine similarity for RAG |
| `tkinter` | bundled | Desktop GUI |

> **Tkinter** is included with the standard CPython installer on Windows and macOS.  
> On some Linux distributions it must be installed separately:
> ```bash
> sudo apt install python3-tk
> ```

---

## Installation

### 1. Clone the repository

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd CircularLifeAI
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
pip install -r requirements.txt
```

> On the first analysis, `sentence-transformers` will automatically download  
> the `all-MiniLM-L6-v2` embedding model (~80 MB) and cache it locally.  
> No manual download step is required.

---



## Configuration

Create a `.env` file in the project root and add your Groq API key:

```text
GROQ_API_KEY=your_groq_api_key_here


| Variable | Description |
|---|---|
| `GROQ_API_KEY` | Your Groq API key — get one free at [console.groq.com/keys](https://console.groq.com/keys) |

The key is read at startup via `python-dotenv`. It is never displayed in the GUI or written to any file. The `.env` file is excluded from version control by `.gitignore`.

---

## Running the Application

### Desktop GUI (recommended)

```bash
python circular_life_gui.py
```

### Terminal prototype

```bash
python circular_life.py
```

---

## Project Structure

```
CircularLifeAI/
├── circular_life.py              # Core AI logic, prompt templates, terminal entry-point
├── circular_life_gui.py          # Tkinter desktop GUI, result rendering, safety gate
├── rag/
│   ├── __init__.py               # Makes rag/ a Python package
│   ├── embeddings.py             # Sentence-transformer model loading and caching
│   ├── retriever.py              # Chunk loading, cosine similarity, context retrieval
│   └── knowledge_base/
│       └── recycle_guidelines.txt  # Local circular-economy knowledge base
├── requirements.txt              # Python dependencies
├── .env                          # Your API key — never commit (excluded by .gitignore)
├── .env                 # Credential template — safe to commit
├── .gitignore                    # Excludes .env, __pycache__, .venv, etc.
└── README.md                     # This file
```

---

## Example Inputs

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
```
An old laptop that is six years old with a weak battery and a broken keyboard.
```

---

## AI Configuration

| Setting | Value |
|---|---|
| Provider | Groq API |
| Model | `openai/gpt-oss-20b` |
| Temperature | `0.3` — focused, consistent output |
| Max tokens (main call) | `4096` |
| Max tokens (retry call) | `1200` |
| RAG embedding model | `all-MiniLM-L6-v2` (sentence-transformers) |
| RAG top-K chunks | 3 most similar passages |

---

## License

MIT © CircularLife AI contributors
