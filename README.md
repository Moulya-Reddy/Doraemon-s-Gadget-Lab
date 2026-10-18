# Doraemon's Gadget Lab

**Ask a question. Watch Doraemon choose a gadget. Discover the answer.**

Doraemon's Gadget Lab is an interactive AI learning app built with Python and Flask. It combines a playful browser interface with a local knowledge library, gadget-based question routing, live utilities, optional language models, and a tiny GPT implementation for learning how Transformers work.

## ✨ Features

- **Gadget-based answers:** Routes questions to a gadget designed for that kind of task.
- **Knowledge search (RAG):** Retrieves relevant paragraphs from your local knowledge files.
- **Wikipedia fallback:** Looks up information when the local library does not contain a strong match.
- **Live tools:** Supports time/date, weather, and arithmetic questions when the question matches a supported pattern.
- **Optional AI backends:** Use Ollama locally, Gemini with an API key, or the built-in extractive fallback.
- **Answer cards:** Show the answer, selected gadget, source, and suggested follow-up questions.
- **Read-aloud dialogue:** Uses your browser's built-in text-to-speech voices.
- **TinyGPT:** A small decoder-only Transformer learning module implemented with PyTorch.
- **Custom knowledge:** Add your own text files to expand what the app can answer.

## 🚀 Quick Start

### Requirements

- Python 3.10 or newer recommended
- Internet access for weather, Wikipedia fallback, Gemini, and first-time model downloads
- macOS, Windows, or Linux; CPU use is supported

### 1. Extract the ZIP

Extract the project and open a terminal inside the `doraemons-gadget-lab` folder.

### 2. Create a virtual environment

**macOS / Linux**

```bash
python3 -m venv .venv
source .venv/bin/activate
```

**Windows PowerShell**

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
```

### 3. Install dependencies

```bash
python -m pip install --upgrade pip
pip install -r requirements.txt
```

The first launch may download a sentence-transformer model. If it is unavailable, the project can fall back to TF-IDF retrieval.

### 4. Run the app

```bash
python app.py
```

Open **http://localhost:8000** in your browser. Stop the server with `Ctrl+C`.

## 🧠 Optional Language Model

The knowledge library and supported live tools work without a generative LLM. To get more natural wording, configure one of the options below.

### Option A: Ollama (local, no API key)

1. Install Ollama from [ollama.com/download](https://ollama.com/download) and open it once.
2. Pull a small model:

   ```bash
   ollama pull llama3.2:1b
   ```

   If your computer has enough memory, try `llama3.2:3b` for stronger responses.

### Option B: Gemini API

1. Create an API key in [Google AI Studio](https://aistudio.google.com/).
2. Set the key in the same terminal before starting the app.

**macOS / Linux**

```bash
export GEMINI_API_KEY="your_key_here"
python app.py
```

**Windows PowerShell**

```powershell
$env:GEMINI_API_KEY="your_key_here"
python app.py
```

Keep API keys private and never commit them to GitHub. The default `LLM_BACKEND=auto` tries available backends and falls back to extractive mode. See `llm.py` for backend settings.

## ⚙️ How It Works

```text
Browser UI (static/index.html)
          |
          | POST /api/ask
          v
       app.py (Flask)
          |
          v
 gadgets.py (question router)
       /             \
 live-tool match    knowledge question
      |                    |
   tools.py               rag.py
 time / weather /     retrieve local text
    arithmetic              |
                    optional Wikipedia lookup
                             |
                           llm.py
                  format a grounded answer
                             |
                             v
               answer card + source + follow-ups
```

Live-tool patterns are checked first for supported questions. Other questions are routed to a suitable gadget and sent through retrieval. When an LLM is configured, it is instructed to use the retrieved context to keep answers grounded.

## 🧰 Gadget Guide

| Gadget | What it helps with |
|---|---|
| Pocket Watch | Time and date for a city or country |
| Weather Vane | Current weather for a place |
| Calc Cube | Arithmetic, percentages, and square roots |
| Portal Door | Places and geography |
| Rewind Cloth | History and timelines |
| Recall Toast | Summaries and key points |
| Shrink Light | Simple explanations |
| Sky Propeller | How-to questions and recipes |
| Fact Scanner | Quick facts and comparisons |

## 📚 Add Knowledge to the Library

1. Add `.txt` files inside `data/knowledge/`.
2. Separate facts or topics with a blank line. Each paragraph becomes a retrieval chunk.
3. Optionally add example questions to `data/questions.json`.
4. Restart `python app.py` and ask a related question.

If the local library cannot find a useful match, the app can try Wikipedia. Set `WEB_FALLBACK=off` to disable this fallback.

## 🗂️ Project Structure

```text
doraemons-gadget-lab/
├── app.py                 # Flask server and API endpoints
├── gadgets.py             # Gadget definitions and question routing
├── tools.py               # Live time, weather, and maths tools
├── rag.py                 # Embeddings, retrieval, and Wikipedia fallback
├── llm.py                 # Ollama, Gemini, and extractive backends
├── characters.py          # Doraemon dialogue and character settings
├── cast.py                # Follow-up questions, quizzes, and fun facts
├── names.py               # Character-name configuration
├── static/
│   ├── index.html         # Browser UI and animations
│   ├── characters.js      # Character interactions
│   ├── sounds.js          # Audio and speech behavior
│   └── cast.json          # Display names and layout settings
├── data/
│   ├── knowledge/         # Local knowledge text files
│   └── questions.json     # Example questions
└── tinygpt/               # Small GPT implementation
```

## 🔬 TinyGPT Learning Module

The `tinygpt/` folder contains a small decoder-only Transformer implemented in PyTorch. It demonstrates token and position embeddings, causal self-attention, feed-forward layers, next-token training, and autoregressive text generation.

It is intended for learning—not as the app's primary answer engine. The main question-answering flow relies on retrieval and, optionally, a pretrained language model.

## 🛠️ Troubleshooting

- **Port 8000 is already in use:** Stop the other process or configure a different port in the app code.
- **Answers are brief or extractive:** Configure Ollama or Gemini, or continue using the local knowledge and live tools.
- **Weather or Wikipedia lookup fails:** Check your internet connection; these features require network access.
- **First launch takes a while:** The embedding model may need to download and initialize.
- **The answer is missing from the library:** Add relevant paragraphs under `data/knowledge/` and restart the server.

## 🔐 Privacy and Artwork

Questions may be sent to an external service when Gemini or the Wikipedia fallback is used. Avoid entering sensitive information, and keep API keys out of source control.

This project uses the Doraemon character and related third-party material. The README and source code do not grant rights to Doraemon or any third-party artwork. Check that you have permission to use and redistribute all character assets before publishing or sharing the project. Add a software license only if you have the rights to license the code and included materials.
