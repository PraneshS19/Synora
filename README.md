# SYNORA

SYNORA is an institutional document intelligence platform engineered for universities, administrative bodies, and organizations requiring private, verifiable document processing. It pairs a React + TypeScript frontend with a Python + FastAPI backend.

The platform is designed around local-first execution: all core workflows—vector search, evidence synthesis, multilingual translation, audio transcription, and minutes drafting—operate completely on your machine without external cloud APIs, usage fees, or data leaks.

---

## Table of Contents

1. [Project Overview](#1-project-overview)
2. [Technology and Architecture](#2-technology-and-architecture)
3. [Prerequisites](#3-prerequisites)
4. [Installation from a Fresh Clone](#4-installation-from-a-fresh-clone)
5. [Model and Dependency Setup](#5-model-and-dependency-setup)
6. [How to Use Each Module](#6-how-to-use-each-module)
7. [Configuration](#7-configuration)
8. [Data, Privacy, and Persistence](#8-data-privacy-and-persistence)
9. [Tests and Production Build](#9-tests-and-production-build)
10. [Troubleshooting](#10-troubleshooting)
11. [Repository Hygiene and Contribution Handoff](#11-repository-hygiene-and-contribution-handoff)

---

## 1. Project Overview

### Implemented Modules

* **02 — Institutional RAG** *(Fully Implemented)*:
  Document-grounded question answering over private collections. Parses PDFs, DOCX, and TXT files, indexes passages with local subword embeddings, and retrieves citations with exact file names, page numbers, and section titles. If evidence is missing, it explicitly reports that no statement was found rather than inventing facts.
* **04 — IndicTranslate** *(Fully Implemented)*:
  Reviewable document translation between English and Indian languages (Tamil, Hindi, Telugu, Kannada, Malayalam, Bengali, Marathi). Supports DOCX and TXT upload and download. Reconstructs DOCX documents preserving headings, bulleted lists, tables, and pagination without flattening layouts. Integrates with AI4Bharat IndicTrans2 for local neural machine translation.
* **05 — ForumNotes** *(Fully Implemented)*:
  Speech-to-text transcription and structured meeting minutes synthesis. Transcribes MP3, WAV, and M4A recordings locally using OpenAI Whisper. Extracts key discussion topics with timestamps, formal decisions, and action items with owners and deadlines. Features an interactive transcript editor, SQLite draft persistence, draft reopening, and institutional formatted DOCX export.

### Prototype Modules

* **01 — ChangeLens** *(Prototype UI mode)*:
  Visual document version comparison interface. Allows selecting earlier and revised document versions to inspect diff structures. Server-side automated comparison requires configuring a custom diff engine.
* **03 — IndicShield** *(Prototype UI mode)*:
  PII and sensitive information inspection interface. Displays illustrative privacy detection cards. Server-side scanning and redaction require configuring a security provider.

---

## 2. Technology and Architecture

### System Stack

| Layer | Technologies | Notes |
| :--- | :--- | :--- |
| **Frontend** | React 19, TypeScript 5.9, Vite 8.3 | Hash-based routing, dark theme UI, zero UI component libraries |
| **Backend** | Python 3.10–3.13, FastAPI 0.110, Uvicorn 0.28 | Asynchronous REST API with CORS middleware and stream handling |
| **Data Validation** | Pydantic v2, Python-Multipart | Strict schema enforcement and magic-byte file validation |
| **Document Processing** | PyPDF 4.0+, Python-Docx 1.1+ | Multi-format text and structure extraction |
| **Local Vector Search** | Scikit-Learn 1.4+, NumPy 1.26+ | Normalized character n-gram hashing vectorizer (256 dimensions) |
| **Local Neural MT** | AI4Bharat IndicTrans2, PyTorch, Transformers | Optional local neural translation (~1.1 GB dist-200M or 4 GB 1B) |
| **Local Audio STT** | OpenAI Whisper, FFmpeg | Local speech-to-text with segment timestamp preservation |
| **Database & Storage** | SQLite 3, Local File Storage | Stored in `backend/data/synora.db` and `backend/data/uploads/` |

### Architecture and Request Flow

```
                      +---------------------------------------+
                      |         React + Vite Frontend         |
                      |        http://localhost:5173          |
                      +-------------------+-------------------+
                                          |
                                    /api/* proxy
                                          v
                      +---------------------------------------+
                      |          FastAPI Backend API          |
                      |        http://127.0.0.1:8000          |
                      +-------------------+-------------------+
                                          |
         +--------------------------------+--------------------------------+
         |                                |                                |
         v                                v                                v
+------------------+             +------------------+             +------------------+
| Institutional    |             | IndicTranslate   |             | ForumNotes       |
| RAG Service      |             | Service          |             | Service          |
+--------+---------+             +--------+---------+             +--------+---------+
         |                                |                                |
         | Scikit Hashing                 | IndicTrans2 (Torch)            | Whisper + FFmpeg
         | Extractive Synthesizer         | DOCX Layout Builder            | DOCX Report Builder
         v                                v                                v
+------------------------------------------------------------------------------------+
|                         Local Persistence & Storage                                |
|   - SQLite: backend/data/synora.db (Collections, Chunks, Jobs, Drafts)             |
|   - Disk:   backend/data/uploads/  (Private raw documents and audio recordings)     |
+------------------------------------------------------------------------------------+
```

### Local Runtime Guarantee

All default providers execute 100% offline on your machine. At runtime, SYNORA makes no external outbound network calls or API requests. No account keys or subscriptions are required.

---

## 3. Prerequisites

### Operating System
* **Windows 10 / 11** (recommended and primary test environment)
* **Linux** (Ubuntu 22.04+ or Debian 12+)
* **macOS** (12+ Monterey, Ventura, Sonoma)

### Runtimes and Compilers
* **Python**: `3.10`, `3.11`, `3.12`, or `3.13` (tested with Python 3.13.1)
* **Node.js**: `v18.0.0` or higher (tested with Node v20/v22) and `npm`

### System Tools: FFmpeg (Required for Audio Processing)
FFmpeg is required by OpenAI Whisper and the backend audio decodability validator to decode `.mp3`, `.wav`, and `.m4a` files.

#### Windows Installation via WinGet:
```powershell
winget install Gyan.FFmpeg
```

#### Windows Verification:
Close and reopen your terminal, then run:
```powershell
ffmpeg -version
```
If `ffmpeg` is not recognized, add the directory containing `ffmpeg.exe` (typically under `AppData\Local\Microsoft\WinGet\Packages\...` or `C:\Program Files\ffmpeg\bin`) to your Windows User or System `PATH` environment variable.

#### Linux Installation:
```bash
sudo apt update && sudo apt install -y ffmpeg
```

#### macOS Installation:
```bash
brew install ffmpeg
```

### Hardware Considerations
* **Base Platform (RAG & Local Translation)**: Runs on standard CPU hardware with at least 4 GB of system RAM.
* **AI4Bharat IndicTrans2 (Optional Neural MT)**: Requires ~1.1 GB disk space for the distilled model (`dist-200M`) or ~4 GB for `1B`. Recommended: 4 GB+ GPU VRAM or 8 GB+ free system RAM for CPU inference.
* **OpenAI Whisper (Optional Audio STT)**: The default `base` model requires ~140 MB disk space and ~1 GB RAM. Automatically uses NVIDIA CUDA if available (`WHISPER_DEVICE=auto`), and falls back cleanly to CPU if CUDA is absent.

---

## 4. Installation from a Fresh Clone

### Windows (PowerShell)

Open **two separate PowerShell terminals** to run the backend and frontend simultaneously.

#### Terminal 1: Backend Setup & Server

```powershell
# 1. Clone the repository and navigate into the project
git clone https://github.com/your-org/synora.git
cd synora\backend

# 2. Create and activate a Python virtual environment
python -m venv .venv
.\.venv\Scripts\Activate.ps1

# 3. Install backend dependencies
pip install -r requirements.txt

# 4. Initialize the environment file from template
Copy-Item .env.example .env

# 5. Start the backend service
python run.py
```

The backend starts at `http://127.0.0.1:8000`. You should see:
```text
INFO:     Uvicorn running on http://127.0.0.1:8000 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

#### Terminal 2: Frontend Setup & Dev Server

```powershell
# 1. Navigate to the root folder of the project
cd synora

# 2. Install Node dependencies
npm install

# 3. Start the Vite development server
npm run dev
```

The frontend will report:
```text
  VITE v8.3.4  ready in 180 ms

  ➜  Local:   http://localhost:5173/
```

#### Open the Application
Open your browser and navigate to:
```text
http://localhost:5173
```
Vite automatically proxies backend requests from `http://localhost:5173/api/*` to `http://127.0.0.1:8000/api/*`.

To stop either server, press `Ctrl + C` in its respective terminal window.

---

### Linux / macOS (Bash / Zsh)

#### Terminal 1: Backend
```bash
cd synora/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
python3 run.py
```

#### Terminal 2: Frontend
```bash
cd synora
npm install
npm run dev
```

---

## 5. Model and Dependency Setup

### 1. Institutional RAG
* **Model**: Built-in `LocalEmbeddingProvider` using scikit-learn `HashingVectorizer(n_features=256)` and `LocalExtractiveLLMProvider`.
* **Downloads**: Zero external weight downloads required. Fully operational immediately upon installing `requirements.txt`.
* **Licensing**: Built on BSD-licensed scikit-learn and NumPy.

### 2. IndicTranslate (AI4Bharat IndicTrans2)
* **Model**: `ai4bharat/indictrans2-en-indic-dist-200M` (English to Indic) and `ai4bharat/indictrans2-indic-en-dist-200M` (Indic to English), or the full `1B` checkpoints.
* **License**: MIT / CC-BY 4.0.
* **Dependencies**:
  ```powershell
  pip install torch transformers sentencepiece accelerate
  pip install git+https://github.com/VarunGumma/IndicTransToolkit.git
  ```
* **Weight Download**: The backend **never** auto-downloads weights on startup. Pre-download the weights to your HuggingFace cache using the Hugging Face CLI:
  ```powershell
  huggingface-cli download ai4bharat/indictrans2-en-indic-dist-200M
  ```
* **Configuration**: Set in `backend/.env`:
  ```env
  TRANSLATION_PROVIDER=indictrans2
  INDICTRANS2_EN_INDIC_MODEL=ai4bharat/indictrans2-en-indic-dist-200M
  ```
* **Verification**: Run the smoke test:
  ```powershell
  pytest backend/tests/test_live_providers.py -k test_live_indictrans2_smoke_test
  ```

### 3. ForumNotes (OpenAI Whisper)
* **Model**: OpenAI Whisper (`base`, `tiny`, `small`, `medium`, or `large-v3`).
* **License**: MIT.
* **Dependencies**:
  ```powershell
  pip install openai-whisper
  ```
* **Weight Download**: Whisper lazily downloads the model weights on the first transcription request to `~/.cache/whisper`. It does not download weights at server boot.
* **Configuration**: Set in `backend/.env`:
  ```env
  AUDIO_PROVIDER=whisper
  WHISPER_MODEL_SIZE=base
  WHISPER_DEVICE=auto
  ```
* **Verification**: Ensure FFmpeg is on PATH and run:
  ```powershell
  pytest backend/tests/test_live_providers.py -k test_live_whisper_audio_smoke_test
  ```

---

## 6. How to Use Each Module

### 01 — ChangeLens (Prototype)
1. Select an earlier version and a revised version of a document (`.pdf`, `.docx`, `.txt` up to 20 MB).
2. Click **Compare changes** to inspect the illustrative diff layout.
3. A notification confirms that server-side automated comparison requires a configured comparison provider.

### 02 — Institutional RAG
1. In the workspace, enter a **Collection Title** (e.g. `Admissions Regulations 2026`).
2. Upload one or more source documents (`.pdf`, `.docx`, `.txt`).
3. Click **Create private collection**. The backend parses sections, computes 256-dimensional subword hash vectors, and stores them in SQLite.
4. Type an institutional question into the query box and click **Ask collection**.
5. The system returns the synthesized answer alongside clickable passage citations (document filename, page number, and section header).
6. **No-Evidence Handling**: If the inquiry cannot be substantiated by the uploaded texts, the system returns `evidenceFound: false` with `"No sufficient evidence was found in the private collection to answer this question."` and zero citations.

### 03 — IndicShield (Prototype)
1. Upload a sensitive document (`.pdf`, `.docx`, `.txt`).
2. Click **Inspect content** to review privacy risk markers.
3. A notification confirms that server-side automated PII detection requires a configured security provider.

### 04 — IndicTranslate
1. Select the **Source Language** (English, Tamil, Hindi, Telugu, Kannada, Malayalam).
2. Select the **Target Language** (Tamil, Hindi, Telugu, Kannada, Malayalam, Bengali, Marathi, English).
   * *Note: The system rejects identical source and target selections or unsupported pairs.*
3. Upload a document (`.docx` or `.txt`) or enter text in the editor.
4. Click **Translate document** (or **Generate draft**).
5. Review each segment side-by-side in the human-in-the-loop review table. Edit any translated segment directly in the text field.
6. Click **Download translated document**.
   * For DOCX files, headings, lists, tables, and pagination structures are preserved in the downloaded file (`<title>-<target>.docx`).
   * For TXT files, original line breaks and paragraph spacing are retained.

### 05 — ForumNotes
1. Choose your input:
   * **Audio**: Upload an audio file (`.mp3`, `.wav`, `.m4a` up to 200 MB).
   * **Transcript**: Upload a pre-existing transcript (`.txt`, `.docx`, `.pdf`, `.vtt`, `.srt` up to 20 MB).
2. For audio, click **Transcribe audio recording**. Whisper transcribes the recording locally, generating timestamped segments (`[MM:SS - MM:SS]`).
3. **Review & Edit Transcript**: Inspect the timestamped dialogue in the editable textarea. Refine technical terms, speaker names, or dialogue.
4. Click **Generate draft minutes** (or **Regenerate minutes from edited transcript**).
5. The generated draft renders:
   * **Title & Executive Summary**
   * **Discussion Topics** (with timestamps)
   * **Formal Decisions Table** (with status: `agreed` or `pending`)
   * **Action Items Table** (with task, owner, deadline, and uncertainty status)
   * **Reviewable Uncertainties Box**
6. **Action-Owner Extraction**:
   * Recognizes speaker commitments following the pattern: `Speaker, I will [action] by [deadline]` (e.g., `Maya, I will send the room layout by Friday.`).
   * *Limitation*: Whisper does not perform speaker diarization. Names are assigned as owners only when explicitly identified before a commitment; otherwise, owners are left blank for human review.
7. Click **Save draft edits** to persist changes to SQLite.
8. Switch to the **Saved Drafts** tab to browse past meetings, view metrics (topics, decisions, action items), and click **Reopen & Edit** on any draft.
9. Click **⬇ Download formatted DOCX** to export an institutional record with tables, badges, and 1-inch margins.

---

## 7. Configuration

All configuration is loaded from environment variables and managed in `backend/.env`. A complete template is provided in `backend/.env.example`.

| Variable | Default Value | Description |
| :--- | :--- | :--- |
| `HOST` | `127.0.0.1` | Local IP address for the FastAPI backend |
| `PORT` | `8000` | Port for the FastAPI backend service |
| `ENVIRONMENT` | `development` | Deployment environment mode |
| `CORS_ORIGINS` | `http://localhost:5173,http://127.0.0.1:5173` | Allowed frontend origins (comma-separated) |
| `UPLOAD_DIR` | `./data/uploads` | Path to private uploaded file directory |
| `DATABASE_PATH` | `./data/synora.db` | Path to the SQLite database file |
| `MAX_DOC_SIZE_MB` | `20` | Maximum allowed document size (in MB) |
| `MAX_AUDIO_SIZE_MB` | `200` | Maximum allowed audio recording size (in MB) |
| `EMBEDDING_PROVIDER` | `local` | Vector provider: `local` (offline Scikit-Learn hashing) |
| `LLM_PROVIDER` | `local` | Synthesizer: `local` (offline extractive synthesizer) or `openai` |
| `TRANSLATION_PROVIDER` | `local` | Translation engine: `local` (manual review), `indictrans2`, or `none` |
| `AUDIO_PROVIDER` | `none` | Audio engine: `whisper` (local Whisper STT) or `none` |
| `INDICTRANS2_EN_INDIC_MODEL` | `ai4bharat/indictrans2-en-indic-dist-200M` | Hugging Face model checkpoint for En $\rightarrow$ Indic |
| `INDICTRANS2_INDIC_EN_MODEL` | `ai4bharat/indictrans2-indic-en-dist-200M` | Hugging Face model checkpoint for Indic $\rightarrow$ En |
| `WHISPER_MODEL_SIZE` | `base` | Whisper model: `tiny`, `base`, `small`, `medium`, `large-v3` |
| `WHISPER_DEVICE` | `auto` | Whisper device: `auto` (detects CUDA, falls back to CPU), `cuda`, `cpu` |
| `MAX_AUDIO_MINUTES` | `180` | Maximum audio duration in minutes (default 3 hours) |

> **Important**: Never commit `backend/.env` to source control. It is ignored by `.gitignore`.

---

## 8. Data, Privacy, and Persistence

### Storage Locations
* **SQLite Database**: `backend/data/synora.db`
  Stores collection metadata, vector chunk representations, translation jobs, and meeting draft revisions.
* **Uploaded Files**: `backend/data/uploads/`
  Uploaded files are assigned UUID filenames and stored privately on disk. Files are never served as public web assets.
* **Model Cache**:
  * HuggingFace models: `~/.cache/huggingface/hub/`
  * Whisper models: `~/.cache/whisper/`

### Privacy and Isolation
* All processing occurs within the user's local operating environment.
* Data from one collection or meeting is isolated and never leaks into other jobs.
* No data is transmitted externally unless an optional third-party API key (such as OpenAI) is explicitly configured.

### Backup Instructions
To back up all collections, translation jobs, and saved meeting minutes:
1. Make a copy of `backend/data/synora.db`.
2. Make a copy of `backend/data/uploads/`.
3. To restore on a new machine, place these files in the corresponding `backend/data/` directory before starting the backend. Never overwrite a database without keeping a backup.

---

## 9. Tests and Production Build

### Automated Test Suites

The backend test suite verifies upload validation, magic bytes verification, empty/corrupt file rejection, audio formats, Whisper setup handling, timestamped parsing, minutes regeneration, saved draft reopening, DOCX layouts, and rejection of unsupported cloud providers.

#### Run Backend API & Unit Tests:
```powershell
# From the project root (using the backend virtualenv):
.\backend\.venv\Scripts\python -m pytest backend/tests/test_api.py -v
```
*Result: **44 passed** in ~18s.*

#### Run Live Model Smoke Tests:
Exercises real local IndicTrans2 translation and Whisper audio transcription when models and FFmpeg are present:
```powershell
.\backend\.venv\Scripts\python -m pytest backend/tests/test_live_providers.py -v
```
*Result: **2 passed** in ~7s.*

### Frontend Production Build

Verifies TypeScript type safety, module bundling, and CSS asset generation:
```powershell
npm run build
```
*Result: `tsc -b && vite build` completes in ~120ms with **0 errors**, outputting production assets into `dist/`.*

---

## 10. Troubleshooting

### 1. `502 Bad Gateway` in Browser
* **Cause**: The Vite frontend cannot reach the FastAPI backend at `http://127.0.0.1:8000`.
* **Fix**: Ensure Terminal 1 is running `python run.py`. Verify backend liveness by visiting `http://127.0.0.1:8000/api/health` directly in your browser.

### 2. `ModuleNotFoundError: No module named 'app'`
* **Cause**: Running Python from outside the `backend` folder or with an inactive virtual environment.
* **Fix**: Navigate to `synora/backend`, activate `.venv` (`.\.venv\Scripts\Activate.ps1` on Windows or `source .venv/bin/activate` on Linux/macOS), and execute `python run.py`.

### 3. `Whisper speech-to-text requires 'ffmpeg' installed on system PATH`
* **Cause**: FFmpeg is not installed or the current terminal session has not refreshed its environment variables.
* **Fix**: Run `winget install Gyan.FFmpeg` on Windows (or `sudo apt install ffmpeg` on Linux). Close and reopen all PowerShell windows, then verify with `ffmpeg -version`.

### 4. `IndicTrans2 model weights for '...' are not present in local HuggingFace cache`
* **Cause**: `TRANSLATION_PROVIDER=indictrans2` was set without downloading model weights.
* **Fix**: Run `huggingface-cli download ai4bharat/indictrans2-en-indic-dist-200M` or switch back to `TRANSLATION_PROVIDER=local` in `backend/.env`.

### 5. `CUDA out of memory` / Memory Error during Transcription
* **Cause**: The selected Whisper model size exceeds available GPU VRAM.
* **Fix**: In `backend/.env`, set `WHISPER_MODEL_SIZE=tiny` or force CPU execution with `WHISPER_DEVICE=cpu`.

### 6. Port Conflicts (`Address already in use: 8000` or `5173`)
* **Fix**:
  * For backend: Change `PORT=8001` in `backend/.env` and update the proxy target in `vite.config.ts`.
  * For frontend: Vite automatically offers the next available port (e.g. `5174`).

---

## 11. Repository Hygiene and Contribution Handoff

### Git Exclusions (`.gitignore`)
The repository explicitly ignores local development artifacts, dependencies, and private data:
* `node_modules/` and `dist/`
* `backend/.venv/`
* `backend/.env`
* `backend/data/synora.db` and SQLite journal files
* `backend/data/uploads/*` (except `.gitkeep`)
* `__pycache__/` and `*.pyc`
* `.pytest_cache/`

### Contribution Checklist
* When sharing or contributing to this repository, ensure `.env`, SQLite databases, audio files, and user documents are not committed.
* Run `npm run build` and `pytest backend/tests/test_api.py` before submitting changes to ensure all automated checks pass.
