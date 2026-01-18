# Lumina Sales Agent

> **AI-driven B2B Sales Assistant MVP**
> *Developed for Expertise AI application*

## 📋 Project Overview

Lumina Sales Agent is a full-stack AI application designed to autonomously qualify B2B leads. It features a **Goal-Oriented RAG system** (Retrieval-Augmented Generation) that combines semantic search with keyword matching to provide accurate product information. The system intelligently decides when to ask for contact information based on conversation context and persists sales leads into a local database.

---

## 🎯 Core Features

### 1. **Intelligent Conversation System (Goal-Oriented RAG)**
- **Context-Aware Responses**: Uses **Hybrid Search** (Dense + Sparse) to retrieve precise information from the knowledge base, combining OpenAI Embeddings with BM25 keyword matching.
- **Dynamic Sales Strategy**: The AI autonomously determines the optimal timing to request contact details based on user purchase intent, rather than following a rigid decision tree.
- **Persistent Sessions**: Conversation history and state are stored in **SQLite**, ensuring context is preserved even across server restarts.

### 2. **Advanced Web Crawler & Ingestion**
- **Dynamic Content Support**: Uses **Playwright** (Headless Chromium) to render and scrape JavaScript-heavy SPAs (React/Vue sites).
- **Structure-Aware Processing**: Converts HTML to Markdown using **Markdownify** to preserve headers and lists for better LLM comprehension.
- **Recursive Chunking**: Smartly splits text by semantic boundaries (paragraphs > sentences) rather than fixed characters to maintain context.
- **Multi-Tenant Isolation**: Implements metadata filtering (`client_id`) in vector storage to simulate SaaS data isolation.

### 3. **Lead Management System**
- **Automatic Capture**: Regex-based detection automatically extracts emails from natural conversation.
- **Lead Storage**: Stores qualified leads in a structured **SQLite** database.
- **Visual Feedback**: Frontend provides real-time UI indicators when a lead is successfully captured.

### 4. **Modern Streaming UI**
- **Real-time Streaming**: Implements **Server-Sent Events (SSE)** for specific character-by-character typing effects.
- **Interactive Training**: Users can input any URL to instantly train the agent on new product data.

---

## 🛠️ Technology Stack

### Backend
- **Framework**: Python (Flask)
- **AI/LLM**: Azure OpenAI (GPT-4o)
- **Vector DB**: Pinecone (Serverless) + `pinecone-text` (Hybrid Search)
- **Crawler**: Playwright + BeautifulSoup4 + Markdownify
- **Database**: SQLite (Leads & Sessions)

### Frontend
- **Framework**: React 18 + TypeScript + Vite
- **Styling**: Tailwind CSS + shadcn/ui
- **State/Effects**: Custom React Hooks for SSE streaming

---

## 🔄 Architecture & Logic Flow

### Data Ingestion Pipeline
```
User inputs URL → Playwright renders page → Markdown conversion → Recursive Chunking → 
Generate Open AI Embeddings (Dense) + BM25 Vectors (Sparse) → Upsert to Pinecone
```

### Conversation Flow
```
User Message → Check Session/History (SQLite) → Detect Intent/Email → 
Hybrid Search (Pinecone) → Assemble Context → Azure OpenAI (Stream) → 
Frontend Render → SQLite Log
```

---

## 🚀 Getting Started

### Prerequisites
1. **Python 3.11+**
2. **Node.js 18+** & npm
3. **Azure OpenAI API Key & Endpoint** (Required for LLM)
4. **Pinecone API Key** (Required for Vector Search)

### 1. Environment Configuration

Create a `.env` file in the root directory:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your-azure-key
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# Pinecone Configuration
PINECONE_API_KEY=your-pinecone-key
PINECONE_INDEX=lumina-sales-agent

# Flask Configuration
FLASK_ENV=development
PORT=5000
```

### 2. Backend Setup

```bash
cd backend

# Create & Activate Virtual Environment
python -m venv venv
# Windows:
venv\Scripts\activate
# Mac/Linux:
source venv/bin/activate

# Install Dependencies
pip install -r requirements.txt

# Run Playwright Install (First time only)
playwright install chromium

# Start Server
python app.py
```
*Server runs at http://localhost:5000*

### 3. Frontend Setup

```bash
cd frontend

# Install Dependencies
npm install

# Start Dev Server
npm run dev
```
*App runs at http://localhost:3000*

---

## 📁 Project Structure

```
.
├── backend/
│   ├── app.py                 # Main Flask Application
│   ├── ingestion.py           # Crawler & Vectorization Logic
│   ├── vector_store.py        # Pinecone Wrapper
│   ├── reset_vector_db.py     # Utility: Reset Pinecone Index
│   ├── view_leads.py          # Utility: View SQLite Leads
│   ├── requirements.txt       # Python Dependencies
│   └── lumina_leads.db        # SQLite Database (Auto-generated)
│
├── frontend/
│   ├── src/
│   │   ├── components/        # React Components (Chat, UI)
│   │   ├── lib/               # Utilities
│   │   └── App.tsx            # Main Entry Logic
│   ├── vite.config.ts         # Vite Config (Proxy Setup)
│   └── tailwind.config.js     # Tailwind Styling
│
└── README.md                  # This file
```

---

## 🔧 API Documentation

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/health` | Check service status |
| `POST` | `/api/ingest` | Crawl URL and train AI (`{url: string}`) |
| `POST` | `/api/chat` | Send message (`{message: string, stream: true}`) |
| `GET` | `/api/leads` | Retrieve all captured sales leads |

---

## 💡 Development Challenges & Solutions

1.  **Dynamic Content Extraction**:
    *   *Challenge*: `requests` library couldn't scrape SPA sites (React/Vue).
    *   *Solution*: Implemented **Playwright** to render full DOM before extraction.

2.  **Semantic Context Loss**:
    *   *Challenge*: Simple character splitting broke sentences and headers.
    *   *Solution*: Used **Markdownify** to preserve structure and implemented **Recursive Chunking** to respect paragraph boundaries.

3.  **Accuracy vs. Keywords**:
    *   *Challenge*: Pure semantic search missed specific product model numbers.
    *   *Solution*: Implemented **Hybrid Search** weighting Dense vectors (0.7) and Sparse BM25 vectors (0.3).

---

## ⚠️ Common Issues

*   **Backend Startup Error**: If `PINECONE_API_KEY` is missing, check your `.env` file location.
*   **Playwright Error**: If you see "Executable not found", run `python -m playwright install chromium`.
*   **Frontend Network Error**: Ensure backend is running on port 5000.
