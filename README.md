# Lumina Sales Agent

Lumina Sales Agent is an AI-driven sales assistant MVP, developed specifically for Expertise AI position application.

## Project Architecture

### Backend (Python/Flask)
- **`app.py`** - Flask main program, provides RESTful API
- **`ingestion.py`** - Web crawling and vectorization module
- **`vector_store.py`** - Pinecone vector database integration
- **`requirements.txt`** - Python dependencies

### Frontend (React/TypeScript)
- **Vite** - Build tool
- **React 18** - UI framework
- **TypeScript** - Type safety (strict mode)
- **Tailwind CSS** - Styling framework
- **shadcn/ui** - UI component library
- **Chat Interface** - Main interaction interface

### Database
- **SQLite** - Local Lead storage (simulating enterprise PostgreSQL)

## Quick Start

### 1. Environment Configuration

Copy `.env.example` to `.env` and fill in necessary API keys:

```bash
cp .env.example .env
```

Edit `.env` file and fill in:
- `AZURE_OPENAI_API_KEY` - Azure OpenAI API key
- `AZURE_OPENAI_ENDPOINT` - Azure OpenAI Endpoint
- `PINECONE_API_KEY` - Pinecone API key
- `PINECONE_INDEX` - Pinecone index name (default: lumina-sales-agent)

### 2. Backend Setup

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Run server
python app.py
```

Backend service will run on `http://localhost:5000`.

### 3. Frontend Setup

```bash
cd frontend

# Install dependencies
npm install

# Run development server
npm run dev
```

Frontend service will run on `http://localhost:3000`.

## API Endpoints

### Health Check
- `GET /api/health` - Service health status

### Chat
- `POST /api/chat` - Send message and get AI response
  ```json
  {
    "message": "User message content"
  }
  ```

### Leads Management
- `GET /api/leads` - Get all leads
- `POST /api/leads` - Create new lead
  ```json
  {
    "name": "Name",
    "email": "email@example.com",
    "company": "Company Name",
    "phone": "Phone Number",
    "status": "new",
    "notes": "Notes"
  }
  ```

### Data Ingestion
- `POST /api/ingest` - Crawl web page and vectorize
  ```json
  {
    "url": "https://example.com"
  }
  ```

## Features

- ✅ **AI Conversation** - Context-aware conversation based on Hybrid Search (Dense + Sparse)
- ✅ **Web Crawling** - Automatically extract web content and vectorize
- ✅ **Hybrid Search** - Semantic + Keyword search using Pinecone & BM25
- ✅ **Lead Management** - SQLite database storage for sales leads
- ✅ **Session Persistence** - Chat history stored in SQLite
- ✅ **Dynamic Sales Strategy** - LLM-driven timing for asking contact info
- ✅ **Modern UI** - Tailwind CSS + shadcn/ui components
- ✅ **TypeScript Strict Mode** - Type safety guarantee

## Tech Stack

### Backend
- Flask 3.0.0
- Pinecone Client 3.0.0 & **pinecone-text** (Hybrid Search)
- OpenAI (Azure OpenAI)
- BeautifulSoup4 4.12.2
- SQLite3 (Leads & Session Store)

### Frontend
- React 18.2.0
- TypeScript 5.2.2
- Vite 5.0.8
- Tailwind CSS 3.3.6
- shadcn/ui
- Lucide React (icons)

## Project Structure

```
.
├── backend/
│   ├── app.py              # Flask main program
│   ├── ingestion.py        # Data ingestion module
│   ├── vector_store.py     # Pinecone integration
│   ├── reset_vector_db.py  # Utility to reset vector db
│   ├── view_leads.py       # Utility to view leads
│   ├── requirements.txt    # Python dependencies
│   └── lumina_leads.db     # SQLite database (auto-created)
├── frontend/
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/         # shadcn/ui components
│   │   │   └── Chat.tsx    # Chat interface
│   │   ├── lib/
│   │   │   └── utils.ts    # Utility functions
│   │   ├── App.tsx
│   │   ├── main.tsx
│   │   └── index.css
│   ├── package.json
│   ├── tsconfig.json
│   ├── vite.config.ts
│   └── tailwind.config.js
├── .env.example            # Environment variable example
├── .gitignore
└── README.md
```

## Development Notes

### Unified API Response Format

All API endpoints follow a unified response format:

```json
{
  "success": true,
  "message": "Operation successful",
  "data": { ... }
}
```

### TypeScript Strict Mode

The project uses TypeScript strict mode, including:
- `strict: true`
- `noUnusedLocals: true`
- `noUnusedParameters: true`
- `noUncheckedIndexedAccess: true`

### Flask Production-Grade Syntax

- Complete type hints
- Unified error handling
- Standardized code structure

## License

This project is an MVP demo project for Expertise AI position application.
