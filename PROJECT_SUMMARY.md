# Lumina Sales Agent - Project Features and Running Guide

## 📋 Project Overview

Lumina Sales Agent is an **AI-driven B2B sales assistant MVP** that I created after researching Expertise AI's business model and product features. The project adopts a frontend-backend separation architecture, implementing core features such as intelligent conversation, knowledge base construction, and sales lead management.

---

## 🎯 Core Features

### 1. **Intelligent Conversation System (Goal-Oriented RAG)**

#### Features:
- ✅ **Streaming Response**: Uses SSE (Server-Sent Events) to display text character by character, providing real-time interactive experience
- ✅ **Context-Aware**: RAG (Retrieval-Augmented Generation) based on Hybrid Search (Dense + Sparse), retrieving relevant information from knowledge base
- ✅ **Dynamic Sales Strategy**:
  - **LLM-Driven Logic**: The AI intelligently decides the best timing to ask for contact information based on conversation flow and purchase intent, rather than hardcoded rules
  - **Persistent Sessions**: Conversation history and state are stored in SQLite (not memory), surviving server restarts using `sessions` and `messages` tables
  - Automatically capture user email and create sales leads

#### Technical Implementation:
- Backend: Flask + OpenAI GPT-4o + Pinecone (Hybrid Search) + SQLite
- Frontend: React + TypeScript + streaming data processing

---

### 2. **Enhanced Web Crawler and Hybrid Vectorization**

#### Features:
- ✅ **Hybrid Search Architecture**:
  - **Dense Vectors**: OpenAI `text-embedding-3-small` for semantic understanding
  - **Sparse Vectors**: BM25 (via `pinecone-text`) for precise keyword matching
  - Combines both using Pinecone's `dotproduct` metric for superior retrieval accuracy
- ✅ **Dynamic Content Support**:
  - Uses **Playwright** (headless Chromium) to render JavaScript-heavy webpages (SPA, React, Vue).
  - Handles `networkidle` states to ensure full content loading before extraction.
- ✅ **Structure-Aware Extraction**:
  - Uses **Markdownify** to convert HTML to Markdown.
  - Preserves headers (`#`), lists (`-`), and emphasis, maintaining semantic structure for the LLM.
- ✅ **Recursive Chunking**:
  - Intelligent splitting based on separators [`\n\n`, `\n`, `. `, ` `].
  - Ensures semantic units (paragraphs, sentences) are kept together unlike simple fixed-size cutting.
- ✅ **False Multi-Tenant Isolation**:
  - All vector data must include `client_id` metadata
  - Automatically filter queries by `client_id` to ensure strict data isolation

#### Technical Implementation:
- **Playwright** (Headless Browser)
- **Markdownify** (HTML to Markdown)
- OpenAI text-embedding-3-small + BM25Encoder
- Pinecone Serverless Index (dotproduct metric)

---

### 3. **Sales Lead Management**

#### Features:
- ✅ **Automatic Capture**: Automatically identify email addresses from conversations and create Leads
- ✅ **Data Storage**: Use SQLite database (simulating enterprise PostgreSQL)
- ✅ **Visual Feedback**: Frontend displays email capture status in real-time (green border + notification)

#### Data Structure:
```sql
leads (
  id, name, email, company, phone,
  status, notes, created_at, updated_at
)
```

---

### 4. **Modern User Interface**

#### Features:
- ✅ **Streaming Conversation Interface**: Text displayed character by character, similar to ChatGPT
- ✅ **URL Training Feature**: Input web page URL, display progress bar and training status
- ✅ **Real-Time Feedback**:
  - Upload progress bar animation
  - Success notification: "AI training completed, you can start chatting now!"
  - Email capture visual notification

#### UI Tech Stack:
- React 18 + TypeScript (strict mode)
- Tailwind CSS + shadcn/ui component library
- Lucide React icon library

---

## 🔄 Running Logic Details

### Overall Architecture Flow

```
User inputs URL
    ↓
Frontend sends /api/ingest request
    ↓
Backend crawls web page → extracts content → chunks → generates vectors → stores to Pinecone
    ↓
Returns success notification
    ↓
User starts conversation
    ↓
Frontend sends /api/chat request (stream: true)
    ↓
Backend: detects email → generates query vector → Pinecone search → OpenAI generates response
    ↓
SSE streaming response → frontend displays character by character
    ↓
If email detected → automatically creates Lead → frontend displays green notification
```

---

### 1. Data Ingestion Flow (`/api/ingest`)

```
1. Receive URL request (with optional client_id)
   ↓
2. fetch_url() - Use requests to get web page HTML
   ↓
3. extract_text() - BeautifulSoup parsing (content prioritization)
   ↓
4. chunk_text() - Overlapping text chunking
   ↓
5. Vectorize:
   - get_embeddings(): Generate Dense Vectors (OpenAI)
   - get_sparse_vector(): Generate Sparse Vectors (BM25)
   ↓
6. upsert() - Store to Pinecone (with client_id metadata)
   - Payload: { values: dense, sparse_values: sparse, metadata: {...} }
   ↓
7. Return success result
```

---

### 2. Conversation Processing Flow (`/api/chat`)

```
1. Receive user message
   ↓
2. Load/Create Session (SQLite):
   - Retrieve conversation history from `messages` table
   - Check `sessions` table for email_provided status
   ↓
3. Detect email (regex)
   - If email found → Create Lead in DB → Update `sessions` table
   ↓
4. Hybrid Search:
   - Generate query dense vector (OpenAI)
   - Generate query sparse vector (BM25)
   - Pinecone Search (Dense + Sparse, filtered by client_id)
   ↓
5. Build Context & Prompt:
   - Construct System Prompt dynamically based on email status
   - Append retrieved context and recent history from DB
   ↓
6. OpenAI Streaming Response:
   - Stream text chunk by chunk to frontend
   - Store assistant response to SQLite `messages` table asynchronously
   ↓
7. Frontend Processing:
   - Render stream text
   - Update UI indicators based on response flags
```

---

### 3. Multi-Tenant Isolation Mechanism

```
When storing:
  metadata = {
    "client_id": "demo",  # Force add
    "url": "...",
    "text": "..."
  }

When querying:
  filter = {"client_id": {"$eq": "demo"}}  # Pinecone filter

Result: Each tenant can only access their own data
```

---

## 🚀 How to Run the Code

### Prerequisites

1. **Python 3.11+**
2. **Node.js 18+** and **npm**
3. **Azure OpenAI API Key & Endpoint**
   - Ensure you have an Azure OpenAI resource deployed.
   - You need the API Key (`AZURE_OPENAI_API_KEY`) and the Endpoint URL (`AZURE_OPENAI_ENDPOINT`).
4. **Pinecone API Key**
   - Visit: https://www.pinecone.io/
   - Register account and get API Key
   - Note: Index dimension is 1536 (text-embedding-3-small)

---

### Step 1: Environment Configuration

#### 1.1 Create `.env` File

Create `.env` file in project root directory:

```bash
# In project root directory
# Windows PowerShell
New-Item -Path .env -ItemType File
```

Edit `.env` file and fill in the following:

```env
# Azure OpenAI Configuration
AZURE_OPENAI_API_KEY=your-azure-openai-api-key
AZURE_OPENAI_ENDPOINT=https://your-resource-name.openai.azure.com/
AZURE_OPENAI_API_VERSION=2024-12-01-preview

# Pinecone Configuration
PINECONE_API_KEY=your-pinecone-api-key-here
PINECONE_INDEX=lumina-sales-agent

# Flask Configuration
FLASK_ENV=development
PORT=5000
```

---

### Step 2: Backend Setup

#### 2.1 Enter Backend Directory

```bash
cd backend
```

#### 2.2 Create Python Virtual Environment

**Windows:**
```bash
python -m venv venv
venv\Scripts\activate
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

#### 2.3 Install Dependencies

```bash
pip install -r requirements.txt
```

#### 2.4 Run Backend Server

```bash
python app.py
```

**Expected Output:**
```
 * Running on http://0.0.0.0:5000
```

Backend service will run on `http://localhost:5000`.

**Note:**
- First run will automatically create SQLite database `lumina_leads.db`
- If Pinecone index doesn't exist, it will be automatically created (takes a few seconds)

---

### Step 3: Frontend Setup

#### 3.1 Open New Terminal Window

Keep backend running, open a new terminal window.

#### 3.2 Enter Frontend Directory

```bash
cd frontend
```

#### 3.3 Install Dependencies

```bash
npm install
```

#### 3.4 Run Development Server

```bash
npm run dev
```

**Expected Output:**
```
  VITE v5.0.8  ready in 500 ms

  ➜  Local:   http://localhost:3000/
  ➜  Network: use --host to expose
```

Frontend service will run on `http://localhost:3000`.

---

### Step 4: Using the Application

#### 4.1 Open Browser

Visit: `http://localhost:3000`

#### 4.2 Train AI (Optional but Recommended)

1. Enter web page URL in the top URL input box, for example:
   ```
   https://www.example.com
   ```
2. Click upload button (or press Enter)
3. Wait for progress bar to complete
4. See notification: "AI training completed, you can start chatting now!"

#### 4.3 Start Conversation

1. Enter message in bottom input box, for example:
   ```
   What is the price of your product?
   ```
2. Press Enter or click send button
3. Observe streaming response: text displayed character by character
4. If AI asks for email, enter email address, for example:
   ```
   myemail@example.com
   ```
5. Observe green notification: "Your email information has been automatically saved"

---

## 📁 Project Structure

```
.
├── backend/                    # Backend service
│   ├── app.py                 # Flask main program (API endpoints)
│   ├── inset_vector_db.py     # Utility to reset vector database
│   ├── view_leads.py          # Utility to view captured leads
│   ├── regestion.py           # Web crawling and vectorization
│   ├── vector_store.py        # Pinecone vector database integration
│   ├── requirements.txt       # Python dependencies
│   └── lumina_leads.db        # SQLite database (auto-created)
│
├── frontend/                   # Frontend application
│   ├── src/
│   │   ├── components/
│   │   │   ├── ui/            # shadcn/ui components
│   │   │   │   ├── button.tsx
│   │   │   │   └── input.tsx
│   │   │   └── Chat.tsx        # Main chat interface
│   │   ├── lib/
│   │   │   └── utils.ts        # Utility functions
│   │   ├── App.tsx            # Root component
│   │   ├── main.tsx           # Entry file
│   │   └── index.css          # Global styles
│   ├── package.json           # Node dependencies
│   ├── tsconfig.json          # TypeScript configuration
│   ├── vite.config.ts         # Vite configuration
│   └── tailwind.config.js     # Tailwind configuration
│
├── .env                       # Environment variables (need to create)
├── .env.example               # Environment variable example
├── .gitignore                 # Git ignore file
├── README.md                  # Project documentation
└── PROJECT_SUMMARY.md         # This document
```

---

## 🔧 API Endpoint Documentation

### 1. Health Check
```
GET /api/health
```
Returns service status

---

### 2. Data Ingestion
```
POST /api/ingest
Content-Type: application/json

{
  "url": "https://example.com"
}
```

**Response:**
```json
{
  "success": true,
  "message": "Data ingestion successful",
  "data": {
    "url": "https://example.com",
    "chunks": 10,
    "stored": 10
  }
}
```

---

### 3. Chat (Streaming)
```
POST /api/chat
Content-Type: application/json

{
  "message": "User message",
  "session_id": "session_123",
  "stream": true
}
```

**Response:** SSE stream
```
data: {"type": "chunk", "content": "text fragment"}

data: {"type": "done", "session_id": "...", "email_provided": false}
```

---

### 4. Get Leads
```
GET /api/leads
```

**Response:**
```json
{
  "success": true,
  "data": [
    {
      "id": 1,
      "name": "User",
      "email": "user@example.com",
      "status": "new",
      "created_at": "2024-01-01 12:00:00"
    }
  ]
}
```

---

### 5. Create Lead
```
POST /api/leads
Content-Type: application/json

{
  "name": "Name",
  "email": "email@example.com",
  "company": "Company",
  "phone": "Phone"
}
```

---

## ⚠️ Common Issues

### 1. Backend Startup Failure

**Issue:** `PINECONE_API_KEY environment variable not set`

**Solution:** Check if `.env` file exists and contains correct API Key

---

### 2. Frontend Cannot Connect to Backend

**Issue:** Frontend displays network error

**Solution:**
- Confirm backend is running on `http://localhost:5000`
- Check proxy configuration in `frontend/vite.config.ts`

---

### 3. Pinecone Index Creation Failed

**Issue:** Index creation timeout

**Solution:**
- Check if Pinecone API Key is correct
- Confirm network connection is normal
- Wait a few seconds and retry (index creation takes time)

---

### 4. Streaming Response Not Working

**Issue:** Text displays all at once, not character by character

**Solution:**
- Check if request includes `"stream": true`
- Check browser console for errors
- Confirm backend supports SSE (check response headers)

---

## 🎓 Technical Highlights

1. **Goal-Oriented RAG**: Combines vector search and LLM to achieve goal-oriented conversations
2. **Multi-Tenant Architecture**: Demonstrates SaaS-level data isolation capabilities
3. **Streaming Processing**: SSE implements real-time interactive experience
4. **Intelligent Content Extraction**: Prioritizes capturing main content, improves data quality
5. **Overlapping Chunking**: Text chunking strategy that prevents semantic loss
6. **Automatic Lead Capture**: Automatically identifies and saves sales leads from conversations

---

## 📝 Development Standards

- **TypeScript Strict Mode**: All types must be explicitly defined
- **Unified API Response Format**: `{success, message, data}`
- **Flask Production-Grade Syntax**: Complete type hints and error handling
- **Code Style**: Follow PEP 8 (Python) and ESLint (TypeScript)

---

## 🚀 Next Steps for Extension

- [ ] Integrate Redis for session management
- [ ] Add user authentication and authorization
- [ ] Implement multi-tenant dynamic switching
- [ ] Add conversation history persistence
- [ ] Implement more complex sales script logic
- [ ] Add data analytics dashboard

---

## �️ Development Challenges & Solutions

During the development process, several technical challenges were encountered. Here is a summary of the issues and their solutions:

### 1. Handling Dynamic Web Content
**Challenge:** Initially used `requests` and `BeautifulSoup` for crawling. This failed on modern Single Page Applications (SPAs) built with React/Vue because the content is rendered via JavaScript after the initial page load.
**Solution:** Migrated to **Playwright**, a headless browser automation tool. It allows the backend to fully render the page (executing JS) and wait for network idle states before extracting the HTML content.

### 2. Playwright Executable Missing
**Challenge:** After installing the `playwright` Python package, the backend crashed with `Executable doesn't exist`. This occurred because the Python package does not bundle the actual browser binaries by default.
**Solution:** Executed `python -m playwright install chromium` command to download the necessary browser binaries (Chromium) to the local environment.

### 3. Preserving Semantic Structure in Text
**Challenge:** `BeautifulSoup.get_text()` flattened the HTML into a single string, losing important structural cues like headers (`<h1>`), lists (`<li>`), and bold text. This resulted in poor quality chunks where headers were merged with body text.
**Solution:** Integrated **Markdownify**. By converting HTML to Markdown, we preserved the document structure (headers become `#`, lists become `-`). This allows the LLM to better understand the hierarchy of the information.

### 4. Semantic Chunking Strategy
**Challenge:** Fixed-size character chunking often cut sentences in half or separated related paragraphs, reducing retrieval quality.
**Solution:** Implemented **Recursive Character Chunking**. The system now splits text based on a hierarchy of separators (`\n\n` > `\n` > `. ` > ` `). It tries to keep paragraphs together first, then sentences, ensuring that chunks are semantically coherent.

### 5. Dependency Management on Windows
**Challenge:** Encountered `ModuleNotFoundError` and path issues when managing `requirements.txt` and installing dependencies in the complex nested workspace structure.
**Solution:** Standardized the dependency installation process to ensure all packages (`playwright`, `pinecone-text`, `markdownify`) are explicitly listed and installed in the active virtual environment.

---

## �📞 Support

If you encounter issues, please check:
1. Whether `.env` file configuration is correct
2. Whether all dependencies are installed
3. Whether both backend and frontend are running
4. Browser console and terminal logs

---

**Enjoy using!** 🎉
