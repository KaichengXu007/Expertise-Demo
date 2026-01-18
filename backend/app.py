"""
Lumina Sales Agent - Flask Backend Main Program
Provides API endpoints for sales agent functionality
"""
from flask import Flask, jsonify, request, Response, stream_with_context
from flask_cors import CORS
from typing import Dict, Any, Optional, List
import os
import sqlite3
import re
import json
from datetime import datetime
from dotenv import load_dotenv
from openai import AzureOpenAI

from vector_store import VectorStore
from ingestion import DataIngestion

# Clear proxy environment variables before loading environment variables
# Avoid new version httpx client reading unsupported proxies parameter
proxy_vars = ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']
_saved_proxies = {}
for var in proxy_vars:
    if var in os.environ:
        _saved_proxies[var] = os.environ.pop(var)

# Load environment variables
# Load .env file from project root directory (parent of backend)
import pathlib
env_path = pathlib.Path(__file__).parent.parent / '.env'
load_dotenv(dotenv_path=env_path)
# If root directory doesn't have it, also try current directory (backward compatibility)
if not env_path.exists():
    load_dotenv()

app = Flask(__name__)
CORS(app)

# Configuration
app.config['JSON_AS_ASCII'] = False
app.config['JSONIFY_PRETTYPRINT_REGULAR'] = False

# Initialize components
vector_store: Optional[VectorStore] = None
data_ingestion: Optional[DataIngestion] = None
openai_client: Optional[AzureOpenAI] = None

# SQLite database path
DB_PATH = os.path.join(os.path.dirname(__file__), 'lumina_leads.db')

# Session storage (for tracking conversation turns and history)
# Should use Redis or database in production environment
session_store: Dict[str, Dict[str, Any]] = {}


def init_db() -> None:
    """Initialize SQLite database"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Leads table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS leads (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL,
            company TEXT,
            phone TEXT,
            status TEXT DEFAULT 'new',
            notes TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Sessions table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS sessions (
            session_id TEXT PRIMARY KEY,
            client_id TEXT NOT NULL,
            email_provided BOOLEAN DEFAULT 0,
            turn_count INTEGER DEFAULT 0,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')

    # Messages table (history)
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS messages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            session_id TEXT NOT NULL,
            role TEXT NOT NULL,
            content TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (session_id) REFERENCES sessions (session_id)
        )
    ''')
    
    conn.commit()
    conn.close()


def get_db_connection() -> sqlite3.Connection:
    """Get database connection"""
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_response(
    success: bool,
    data: Any = None,
    message: str = "",
    status_code: int = 200
) -> tuple[Dict[str, Any], int]:
    """
    Unified API response format
    
    Args:
        success: Whether the request was successful
        data: Response data
        message: Response message
        status_code: HTTP status code
    
    Returns:
        tuple: (response dictionary, HTTP status code)
    """
    response: Dict[str, Any] = {
        "success": success,
        "message": message,
        "data": data
    }
    return jsonify(response), status_code


def initialize_services() -> None:
    """Initialize services"""
    global vector_store, data_ingestion, openai_client
    
    # Initialize database (does not depend on external services)
    try:
        init_db()
        print("✓ Database initialized successfully")
    except Exception as e:
        print(f"✗ Database initialization failed: {e}")
    
    # Initialize Azure OpenAI (required)
    try:
        azure_api_key = os.getenv('AZURE_OPENAI_API_KEY')
        azure_endpoint = os.getenv('AZURE_OPENAI_ENDPOINT')
        azure_api_version = os.getenv('AZURE_OPENAI_API_VERSION', '2024-12-01-preview')
        
        if not azure_api_key or not azure_endpoint:
            print("⚠ Warning: AZURE_OPENAI_API_KEY or AZURE_OPENAI_ENDPOINT not set, Azure OpenAI functionality will be unavailable")
        else:
            # Ensure proxy environment variables are cleared (cleared at module load time)
            for var in ['HTTP_PROXY', 'HTTPS_PROXY', 'http_proxy', 'https_proxy', 'ALL_PROXY', 'all_proxy']:
                os.environ.pop(var, None)
            
            # Use custom httpx client, explicitly do not pass proxies parameter
            import httpx
            http_client = httpx.Client(
                timeout=httpx.Timeout(60.0, connect=10.0)
                # Do not pass proxies parameter to avoid conflicts with new version
            )
            
            openai_client = AzureOpenAI(
                api_key=azure_api_key,
                api_version=azure_api_version,
                azure_endpoint=azure_endpoint,
                http_client=http_client
            )
            print("✓ Azure OpenAI client initialized successfully")
    except Exception as e:
        print(f"✗ Azure OpenAI client initialization failed: {e}")
        print(f"   Error details: {type(e).__name__}")
        import traceback
        traceback.print_exc()
        openai_client = None
    
    # Initialize Pinecone (optional, skip if not configured)
    try:
        pinecone_api_key = os.getenv('PINECONE_API_KEY')
        if not pinecone_api_key:
            print("⚠ Warning: PINECONE_API_KEY not set, vector search functionality will be unavailable")
            vector_store = None
            data_ingestion = None
        else:
            vector_store = VectorStore()
            data_ingestion = DataIngestion(vector_store)
            print("✓ Pinecone vector store initialized successfully")
    except Exception as e:
        print(f"✗ Pinecone initialization failed: {e}")
        print("Note: Vector search functionality will be unavailable, but other features can still work normally")
        vector_store = None
        data_ingestion = None


@app.route('/api/health', methods=['GET'])
def health_check() -> tuple[Dict[str, Any], int]:
    """Health check endpoint"""
    return create_response(
        success=True,
        data={"status": "healthy", "service": "lumina-sales-agent"},
        message="Service is running normally"
    )


def extract_email(text: str) -> Optional[str]:
    """
    Extract email address from text
    
    Args:
        text: Input text
    
    Returns:
        Email address, returns None if not found
    """
    email_pattern = r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b'
    matches = re.findall(email_pattern, text)
    return matches[0] if matches else None


def detect_purchase_intent(message: str) -> bool:
    """
    Detect if user message implies purchase intent
    
    Args:
        message: User message
    
    Returns:
        Whether purchase intent is implied
    """
    purchase_keywords = [
        'price', 'cost', 'pricing', 'how much',
        'how to start', 'how to buy', 'get started',
        'trial', 'demo', 'free trial',
        'buy', 'purchase', 'subscribe',
        'plan', 'package', 'pricing plan'
    ]
    message_lower = message.lower()
    return any(keyword in message_lower for keyword in purchase_keywords)


@app.route('/api/chat', methods=['POST'])
def chat() -> tuple[Dict[str, Any], int]:
    """
    Handle chat messages (Goal-Oriented RAG sales script, Hybrid Search, Persistent Session, LLM-driven email request)
    """
    try:
        json_data = request.get_json()
        if json_data is None:
            return create_response(
                success=False,
                message="Request body must contain JSON data",
                status_code=400
            )
        
        message: str = json_data.get('message', '')
        session_id: str = json_data.get('session_id', 'default_session')
        client_id: str = json_data.get('client_id', 'demo_client')
        
        if not message:
            return create_response(
                success=False,
                message="Message content cannot be empty",
                status_code=400
            )
        
        # Check if services are initialized
        if vector_store is None or data_ingestion is None or openai_client is None:
            return create_response(
                success=False,
                message="Services not initialized, please check environment variable configuration",
                status_code=500
            )
        
        conn = get_db_connection()
        cursor = conn.cursor()

        # Initialize/Retrieve session
        cursor.execute('SELECT * FROM sessions WHERE session_id = ?', (session_id,))
        session_row = cursor.fetchone()
        
        if not session_row:
            cursor.execute('''
                INSERT INTO sessions (session_id, client_id, email_provided, turn_count)
                VALUES (?, ?, ?, ?)
            ''', (session_id, client_id, False, 0))
            conn.commit()
            session_data = {"turn_count": 0, "email_provided": False}
        else:
            session_data = {
                "turn_count": session_row['turn_count'],
                "email_provided": bool(session_row['email_provided'])
            }

        # Update turn count
        new_turn_count = session_data["turn_count"] + 1
        cursor.execute('UPDATE sessions SET turn_count = ? WHERE session_id = ?', (new_turn_count, session_id))
        conn.commit()
        
        # Store user message
        cursor.execute('INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)', 
                       (session_id, 'user', message))
        conn.commit()
        
        # Detect email
        email = extract_email(message)
        email_captured = False
        if email and not session_data["email_provided"]:
            # Automatically create lead
            try:
                cursor.execute('''
                    INSERT INTO leads (name, email, status, notes)
                    VALUES (?, ?, ?, ?)
                ''', (
                    message.split('@')[0] if '@' in message else "Unknown",
                    email,
                    'new',
                    f"Auto-created from chat session, Session ID: {session_id}"
                ))
                cursor.execute('UPDATE sessions SET email_provided = 1 WHERE session_id = ?', (session_id,))
                conn.commit()
                session_data["email_provided"] = True
                email_captured = True
            except Exception as e:
                print(f"Failed to create lead: {e}")
        
        # Get message embedding vector & sparse vector
        embeddings = data_ingestion.get_embeddings([message])
        sparse_vector = data_ingestion.get_sparse_vector_query(message)

        if not embeddings:
            conn.close()
            return create_response(
                success=False,
                message="Unable to generate message embedding vector",
                status_code=500
            )
        
        # Search for relevant context (Hybrid Search + multi-tenant isolation)
        query_vector = embeddings[0]
        context_results = vector_store.search(
            query_vector=query_vector, 
            sparse_vector=sparse_vector,
            top_k=5, 
            client_id=client_id
        )
        
        # Build context text
        context_text = "\n".join([
             f"- [Source: {item.get('metadata', {}).get('url', 'unknown')}] {item.get('metadata', {}).get('text', '')}"
            for item in context_results
        ]) if context_results else "No relevant context available"
        
        # Retrieve recent history
        cursor.execute('SELECT role, content FROM messages WHERE session_id = ? ORDER BY id DESC LIMIT 6', (session_id,))
        history_rows = cursor.fetchall()
        # Reverse to chronological order
        recent_history = [{"role": row['role'], "content": row['content']} for row in reversed(history_rows)]

        # Determine if we should instruct LLM to ask for email
        # We leave this to LLM but provide context about status
        email_status_instruction = ""
        if not session_data["email_provided"]:
             email_status_instruction = "The user has NOT provided their email address yet. If the user shows strong interest or the conversation reaches a natural point to follow up, please politely ask for their email address to send more information or schedule a demo."
        else:
             email_status_instruction = "The user has ALREADY provided their email address. Do not ask for it again."

        # Build System Prompt
        system_prompt = f"""You are a B2B sales expert. Your responses must be concise, professional, and persuasive.

Please answer user questions based on the provided context information. 
If context information is insufficient, please answer based on your professional knowledge but mention you are not 100% sure about specific details not in context.
Maintain a professional, friendly, and concise tone.

{email_status_instruction}

Context Information:
{context_text}"""
        
        # We don't need complex user_content wrapper anymore since context is in system prompt
        
        messages_payload = [{"role": "system", "content": system_prompt}]
        messages_payload.extend(recent_history)
        
        
        # Call OpenAI Chat API
        try:
            # Check if streaming response should be used
            use_stream = json_data.get('stream', False)
            
            if use_stream:
                # Streaming response
                def generate():
                    assistant_response = ""
                    try:
                        # Call Azure OpenAI Stream API
                        chat_deployment = os.getenv('AZURE_DEPLOYMENT_CHAT', 'gpt-4o')
                        stream = openai_client.chat.completions.create(
                            model=chat_deployment,
                            messages=messages_payload,
                            temperature=0.7,
                            max_tokens=500,
                            stream=True
                        )
                        
                        for chunk in stream:
                            if len(chunk.choices) > 0 and chunk.choices[0].delta.content:
                                content = chunk.choices[0].delta.content
                                assistant_response += content
                                # Send SSE data
                                yield f"data: {json.dumps({'type': 'chunk', 'content': content})}\n\n"
                        
                        # Store assistant response to DB
                        # We need a new connection for the generator thread usually, or handle it carefully
                        # Here simplistic approach:
                        with sqlite3.connect(DB_PATH) as stream_conn:
                             stream_cursor = stream_conn.cursor()
                             stream_cursor.execute('INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)', 
                                            (session_id, 'assistant', assistant_response))
                             stream_conn.commit()

                        # Send completion signal
                        yield f"data: {json.dumps({'type': 'done', 'session_id': session_id, 'turn_count': new_turn_count, 'email_provided': session_data['email_provided'] or email_captured})}\n\n"
                    except Exception as e:
                        print(f"Error in stream generation: {e}")
                        import traceback
                        traceback.print_exc()
                        yield f"data: {json.dumps({'type': 'error', 'message': str(e)})}\n\n"
                
                conn.close() # Close main connection before stream
                return Response(
                    stream_with_context(generate()),
                    mimetype='text/event-stream',
                    headers={
                        'Cache-Control': 'no-cache',
                        'X-Accel-Buffering': 'no'
                    }
                )
            else:
                # Non-streaming response
                chat_deployment = os.getenv('AZURE_DEPLOYMENT_CHAT', 'gpt-4o')
                response = openai_client.chat.completions.create(
                    model=chat_deployment,
                    messages=messages_payload,
                    temperature=0.7,
                    max_tokens=500
                )
                
                assistant_response = response.choices[0].message.content or "Sorry, I cannot generate a response."
                
                # Store assistant response
                cursor.execute('INSERT INTO messages (session_id, role, content) VALUES (?, ?, ?)', 
                               (session_id, 'assistant', assistant_response))
                conn.commit()
                conn.close()

                return create_response(
                    success=True,
                    data={
                        "response": assistant_response,
                        "session_id": session_id,
                        "turn_count": new_turn_count,
                        "email_provided": session_data["email_provided"] or email_captured
                    }
                )

        except Exception as e:
            if conn:
                conn.close()
            print(f"Error calling OpenAI: {e}")
            return create_response(
                success=False,
                message=f"Error processing request: {str(e)}",
                status_code=500
            )

    except Exception as e:
        print(f"Server Error: {e}")
        return create_response(
            success=False,
            message=f"Internal server error: {str(e)}",
            status_code=500
        )


@app.route('/api/leads', methods=['GET'])
def get_leads() -> tuple[Dict[str, Any], int]:
    """Get all leads"""
    try:
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM leads ORDER BY created_at DESC')
        leads = [dict(row) for row in cursor.fetchall()]
        conn.close()
        
        return create_response(
            success=True,
            data=leads,
            message="Successfully retrieved leads"
        )
    except Exception as e:
        return create_response(
            success=False,
            message=f"Error occurred while retrieving leads: {str(e)}",
            status_code=500
        )


@app.route('/api/leads', methods=['POST'])
def create_lead() -> tuple[Dict[str, Any], int]:
    """Create a new lead"""
    try:
        json_data = request.get_json()
        if json_data is None:
            return create_response(
                success=False,
                message="Request body must contain JSON data",
                status_code=400
            )
        
        name = json_data.get('name', '')
        email = json_data.get('email', '')
        
        if not name or not email:
            return create_response(
                success=False,
                message="Name and email are required fields",
                status_code=400
            )
        
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute('''
            INSERT INTO leads (name, email, company, phone, status, notes)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            name,
            email,
            json_data.get('company', ''),
            json_data.get('phone', ''),
            json_data.get('status', 'new'),
            json_data.get('notes', '')
        ))
        conn.commit()
        lead_id = cursor.lastrowid
        conn.close()
        
        return create_response(
            success=True,
            data={"id": lead_id},
            message="Lead created successfully",
            status_code=201
        )
    except Exception as e:
        return create_response(
            success=False,
            message=f"Error occurred while creating lead: {str(e)}",
            status_code=500
        )


@app.route('/api/ingest', methods=['POST'])
def ingest_data() -> tuple[Dict[str, Any], int]:
    """Data crawling and vectorization (Hybrid Search)"""
    try:
        json_data = request.get_json()
        if json_data is None:
            return create_response(
                success=False,
                message="Request body must contain JSON data",
                status_code=400
            )
        
        url = json_data.get('url', '')
        client_id = json_data.get('client_id', 'demo_client') # Default to demo_client
        
        if not url:
            return create_response(
                success=False,
                message="URL cannot be empty",
                status_code=400
            )
        
        if data_ingestion is None:
            return create_response(
                success=False,
                message="Data ingestion service not initialized",
                status_code=500
            )
        
        # Execute data ingestion
        result = data_ingestion.ingest_url(url, client_id=client_id)
        
        return create_response(
            success=True,
            data=result,
            message="Data ingestion successful"
        )
    except Exception as e:
        print(f"Error in ingest_data endpoint: {e}")
        import traceback
        traceback.print_exc()
        return create_response(
            success=False,
            message=f"Error occurred during data ingestion: {str(e)}",
            status_code=500
        )


if __name__ == '__main__':
    # Initialize database and services
    initialize_services()
    
    port = int(os.environ.get('PORT', 5000))
    debug = os.environ.get('FLASK_ENV', 'production') == 'development'
    app.run(host='0.0.0.0', port=port, debug=debug)
