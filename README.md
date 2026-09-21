# ♻ CircularLife AI

A desktop application that helps users give everyday items a second life through AI-powered analysis and sustainable recommendations.

Powered by the **Groq API** using the `openai/gpt-oss-20b` model.

---

## Problem Statement

> **How might we use AI to guide people toward the most sustainable second-life or disposal option for everyday items so that we can reduce unnecessary waste and promote responsible consumption?**

Everyday items are often thrown away when they become old, damaged, or no longer useful — even when they could be repaired, reused, repurposed, recycled, or safely disposed of through the right channel. People may also be unsure whether an item is safe to handle or which disposal method is appropriate.

**CircularLife AI** addresses this challenge by using AI to analyse an item description and recommend a suitable circular pathway while prioritising safety.

---

## Sustainability Goal

This project primarily supports:

### **SDG 12 – Responsible Consumption and Production**

CircularLife AI encourages responsible consumption by helping users consider repair, reuse, repurposing, recycling, and responsible disposal before throwing items away.

The project aims to help users make more informed decisions about the next step for everyday items and reduce unnecessary waste.

---

## Features

| Feature | Detail |
|---|---|
| 🔎 Item Analysis | Identifies the item, primary material, and estimated condition |
| 🛡️ Safety Check | Flags potentially hazardous items and lists safety precautions |
| ♻️ Circular Pathway | Recommends Repair, Reuse, Repurpose, Recycle, or Safe Disposal |
| 💡 Second-Life Ideas | Provides 2–3 practical repurposing suggestions for suitable items |
| 📋 Step-by-Step Guide | Provides beginner-friendly instructions for the selected idea |
| 🌍 Sustainability Impact | Explains the environmental benefit of the recommended pathway |
| 🗑️ Disposal Guidance | Provides responsible disposal or recycling guidance |
| ⚠️ Hazard Warnings | Displays prominent warnings and blocks DIY guidance for dangerous items |

---

## Technologies Used

| Technology | Purpose |
|---|---|
| Python | Core application development |
| Tkinter | Desktop graphical user interface |
| Groq API | AI-powered item analysis and recommendations |
| GPT-OSS-20B | Large language model used for analysis |
| Sentence Transformers | Local semantic embeddings for RAG |
| all-MiniLM-L6-v2 | Embedding model for semantic similarity |
| NumPy | Cosine similarity calculations |
| python-dotenv | Environment variable management |
| RAG | Retrieval of relevant circular-economy guidance |

---

## How It Works

1. The user enters a description of an everyday item, including its type, material, condition, and damage if applicable.
2. A deterministic keyword safety check scans the description for known hazardous conditions before the main AI analysis.
3. The application retrieves relevant circular-economy information from a local knowledge base using semantic similarity.
4. The item description and retrieved context are provided to the Groq API for structured analysis.
5. The AI generates information covering item identification, safety, circular pathway, second-life suggestions, guidance, sustainability impact, and disposal.
6. If required sections are missing from the first response, the application uses a targeted retry prompt to complete the response.
7. The GUI parses the response and displays the information using separate result cards.
8. Hazardous items receive a prominent warning and DIY sections are suppressed, while suitable non-hazardous items receive second-life suggestions and guidance.

---

## RAG — Local Knowledge Retrieval

CircularLife AI includes a local **Retrieval-Augmented Generation (RAG)** layer to provide relevant circular-economy information to the AI.

The retrieval process runs locally and does not require an external vector database.

### How It Works

1. A local knowledge base is stored in:

```text
rag/knowledge_base/recycle_guidelines.txt
```

The knowledge base contains guidance related to smartphones, laptops, batteries, lithium-ion batteries, e-waste, plastics, metals, paper, donation, repair, recycling, and safety.

2. The knowledge base is divided into paragraph-level chunks.

3. Each chunk is converted into an embedding using the `all-MiniLM-L6-v2` sentence-transformer model.

4. When the user submits an item description, the description is also converted into an embedding.

5. Cosine similarity is calculated between the user's description and the knowledge-base chunks.

6. The **top 3 most relevant chunks** are retrieved.

7. The retrieved information is added to the Groq prompt as background context.

8. The AI uses this context along with the user's item description to generate the final recommendation.

The embedding model is loaded once and reused during the application's lifetime.

### RAG Fallback

RAG is implemented as a best-effort enhancement. If the embedding model or local knowledge base cannot be loaded, the application can fall back to the standard Groq analysis.

---

## Safety Behaviour

CircularLife AI prioritises safety when analysing potentially hazardous items.

A deterministic keyword guard checks the user's input for known hazardous conditions before the main Groq analysis.

Examples include:

- Swollen or bulging batteries
- Leaking batteries
- Punctured batteries
- Smoking batteries
- Overheating or burning batteries
- Battery fires
- Damaged batteries
- Exposed batteries
- Leaking electrolyte or chemicals

### When a Hazardous Condition Is Detected

The application:

1. Uses a dedicated hazardous-item prompt.
2. Displays a prominent **full-width red hazard banner**.
3. Shows a **HAZARDOUS ⚠** status indicator.
4. Displays the detected hazards and safety precautions.
5. Recommends professional handling, appropriate e-waste facilities, or certified recycling where applicable.
6. Suppresses DIY repurposing and step-by-step instructions for dangerous items.

For conditions not identified by the deterministic safety check, an additional AI-based safety pre-check can be used.

---

## Requirements

| Dependency | Minimum Version | Purpose |
|---|---|---|
| Python | 3.10 | Core programming language |
| `groq` | ≥ 0.9.0 | Groq Python SDK |
| `python-dotenv` | ≥ 1.0.0 | Loads environment variables |
| `sentence-transformers` | ≥ 2.7.0 | RAG embeddings |
| `numpy` | ≥ 1.24.0 | Similarity calculations |
| `tkinter` | Bundled | Desktop GUI |

> **Tkinter** is included with the standard CPython installation on Windows and macOS.
>
> On some Linux distributions, it may need to be installed separately:
>
> ```bash
> sudo apt install python3-tk
> ```

---

## Installation

### 1. Clone the Repository

Replace `<YOUR_GITHUB_REPOSITORY_URL>` with the actual repository URL:

```bash
git clone <YOUR_GITHUB_REPOSITORY_URL>
cd CircularLifeAI
```

### 2. Create a Virtual Environment

Creating a virtual environment is recommended.

```bash
python -m venv .venv
```

#### Windows

```bash
.venv\Scripts\activate
```

#### macOS / Linux

```bash
source .venv/bin/activate
```

### 3. Install Dependencies

```bash
pip install -r requirements.txt
```

On the first analysis, the `sentence-transformers` package may download the `all-MiniLM-L6-v2` embedding model automatically.

No manual model download is required.

---

## Configuration

Create a `.env` file in the project root:

```text
GROQ_API_KEY=your_groq_api_key_here
```

The application reads the API key using `python-dotenv`.

| Variable | Description |
|---|---|
| `GROQ_API_KEY` | API key used to access the Groq API |

You can obtain a Groq API key from the **Groq Console**:

https://console.groq.com/keys

> **Important:** Never commit your `.env` file or expose your API key publicly. The `.env` file is excluded from version control using `.gitignore`.

---

## Running the Application

### Desktop GUI

The recommended way to run CircularLife AI is:

```bash
python circular_life_gui.py
```

### Terminal Prototype

The original terminal-based version can be run using:

```bash
python circular_life.py
```

---

## Project Structure

```text
CircularLifeAI/
│
├── circular_life.py
│   └── Core AI logic, prompts, and terminal entry point
│
├── circular_life_gui.py
│   └── Tkinter desktop interface and result rendering
│
├── rag/
│   ├── __init__.py
│   ├── embeddings.py
│   │   └── Sentence-transformer model loading and caching
│   │
│   ├── retriever.py
│   │   └── Knowledge-base retrieval and similarity calculation
│   │
│   └── knowledge_base/
│       └── recycle_guidelines.txt
│           └── Local circular-economy knowledge base
│
├── requirements.txt
│   └── Python dependencies
│
├── .gitignore
│   └── Excludes .env, __pycache__, .venv, etc.
│
└── README.md
    └── Project documentation
```

> The `.env` file is created locally and is intentionally excluded from version control.

---

## Example Inputs

### ♻ Repair / Reuse

```text
An old wooden chair with a broken leg and peeling paint.
```

### 🌱 Repurposing

```text
A cracked terracotta flower pot I want to reuse in my garden.
```

### 📦 Recycling

```text
A pile of old newspapers and cardboard boxes from moving house.
```

### 📱 E-Waste

```text
An old smartphone with a cracked screen that no longer powers on.
```

### ⚠️ Hazardous Item

```text
A swollen lithium-ion laptop battery.
```

### 💻 Repair / Disposal Decision

```text
An old laptop that is six years old with a weak battery and a broken keyboard.
```

---

## AI Configuration

| Setting | Value |
|---|---|
| AI Provider | Groq API |
| Model | `openai/gpt-oss-20b` |
| Temperature | `0.3` |
| Main Response Max Tokens | `4096` |
| Retry Response Max Tokens | `1200` |
| RAG Embedding Model | `all-MiniLM-L6-v2` |
| RAG Top-K | 3 most relevant chunks |

---

## Future Improvements

Possible future enhancements include:

- 📷 **Image-Based Item Recognition**  
  Allow users to upload an image of an item instead of describing it only through text.

- 📍 **Location-Aware Recycling Guidance**  
  Recommend nearby recycling and e-waste facilities based on the user's location.

- 🌍 **Regional Sustainability Guidance**  
  Expand the knowledge base with region-specific recycling and disposal guidelines.

- 🌐 **Multilingual Support**  
  Support multiple languages to make the application accessible to more users.

- 📊 **Improved Sustainability Impact Estimation**  
  Estimate potential environmental benefits based on item type, material, and selected pathway.

- 📚 **Expanded Knowledge Base**  
  Add more product categories, materials, repair options, and recycling guidance.

- 📈 **User Action History**  
  Allow users to track their sustainable reuse, repair, recycling, and disposal decisions over time.

---

## Demo

CircularLife AI runs as a Python desktop application using Tkinter.

Launch the application with:

```bash
python circular_life_gui.py
```

The application provides different analysis paths for everyday items, recyclable materials, reusable objects, e-waste, and potentially hazardous items.

---

## License

MIT © CircularLife AI contributors
