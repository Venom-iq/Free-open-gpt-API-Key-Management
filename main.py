import os
import uuid
import time
import asyncio
import threading
import json
import re
import sqlite3
from typing import Optional
from datetime import datetime, timedelta
from fastapi import FastAPI, Header, HTTPException, Request, Cookie
from fastapi.responses import JSONResponse, HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
import hashlib
import secrets

# ====================================================================
# Authentication Functions (MUST be first)
# ====================================================================

def hash_password(password: str) -> str:
    """Hash password using SHA256"""
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, password_hash: str) -> bool:
    """Verify password against hash"""
    return hash_password(password) == password_hash

def generate_session_token() -> str:
    """Generate a secure session token"""
    return secrets.token_urlsafe(32)

def create_session(user_type: str, user_id: str, hours: int = 24) -> str:
    """Create a new session and return token"""
    token = generate_session_token()
    expires_at = (datetime.utcnow() + timedelta(hours=hours)).isoformat()
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "INSERT INTO user_sessions (token, user_type, user_id, expires_at) VALUES (?, ?, ?, ?)",
        (token, user_type, user_id, expires_at)
    )
    conn.commit()
    conn.close()
    return token

def validate_session(token: str) -> Optional[dict]:
    """Validate session token and return session info"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(
        "SELECT token, user_type, user_id, expires_at FROM user_sessions WHERE token = ?",
        (token,)
    )
    row = c.fetchone()
    conn.close()
    
    if not row:
        return None
    
    token, user_type, user_id, expires_at = row
    if datetime.fromisoformat(expires_at) < datetime.utcnow():
        # Session expired, delete it
        conn = sqlite3.connect(DB_PATH)
        c = conn.cursor()
        c.execute("DELETE FROM user_sessions WHERE token = ?", (token,))
        conn.commit()
        conn.close()
        return None
    
    return {"user_type": user_type, "user_id": user_id}

def logout_session(token: str):
    """Delete a session"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM user_sessions WHERE token = ?", (token,))
    conn.commit()
    conn.close()

# ====================================================================
# Database Setup — API Keys Management
# ====================================================================
DB_PATH = os.getenv("DB_PATH", "open_gpt_keys.db")
MASTER_ADMIN_KEY = os.getenv("MASTER_ADMIN_KEY", "admin-master-key-2026")

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            name TEXT DEFAULT '',
            token_limit INTEGER DEFAULT -1,
            tokens_used INTEGER DEFAULT 0,
            requests_count INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_used TEXT DEFAULT NULL,
            notes TEXT DEFAULT ''
        )
    ''')
    c.execute('''
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'success'
        )
    ''')
    # Insert default key if no keys exist
    c.execute("SELECT COUNT(*) FROM api_keys")
    if c.fetchone()[0] == 0:
        default_key = os.getenv("API_SECRET_KEY", "admin-password-2026")
        c.execute(
            "INSERT INTO api_keys (key, name, token_limit) VALUES (?, ?, ?)",
            (default_key, "Default Key", -1)
        )
    conn.commit()
    conn.close()

def validate_api_key(key: str):
    """Returns key record if valid and active, else None"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM api_keys WHERE key=? AND is_active=1", (key,))
    row = c.fetchone()
    conn.close()
    if not row:
        return None
    columns = ["id","key","name","token_limit","tokens_used","requests_count",
               "is_active","created_at","last_used","notes"]
    record = dict(zip(columns, row))
    # Check token limit
    if record["token_limit"] != -1 and record["tokens_used"] >= record["token_limit"]:
        return None
    return record

def update_usage(key: str, prompt_tokens: int, completion_tokens: int, endpoint: str):
    total = prompt_tokens + completion_tokens
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("""
        UPDATE api_keys 
        SET tokens_used = tokens_used + ?,
            requests_count = requests_count + 1,
            last_used = ?
        WHERE key = ?
    """, (total, datetime.utcnow().isoformat(), key))
    c.execute("""
        INSERT INTO usage_logs (api_key, endpoint, prompt_tokens, completion_tokens, total_tokens)
        VALUES (?, ?, ?, ?, ?)
    """, (key, endpoint, prompt_tokens, completion_tokens, total))
    conn.commit()
    conn.close()

# ====================================================================
# Complete init_db function with all table creation
# ====================================================================

def complete_init_db():
    """Initialize database with all tables"""
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    
    # Create api_keys table
    c.execute('''
        CREATE TABLE IF NOT EXISTS api_keys (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            key TEXT UNIQUE NOT NULL,
            name TEXT DEFAULT '',
            token_limit INTEGER DEFAULT -1,
            tokens_used INTEGER DEFAULT 0,
            requests_count INTEGER DEFAULT 0,
            is_active INTEGER DEFAULT 1,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            last_used TEXT DEFAULT NULL,
            notes TEXT DEFAULT ''
        )
    ''')
    
    # Create usage_logs table
    c.execute('''
        CREATE TABLE IF NOT EXISTS usage_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            api_key TEXT NOT NULL,
            endpoint TEXT NOT NULL,
            prompt_tokens INTEGER DEFAULT 0,
            completion_tokens INTEGER DEFAULT 0,
            total_tokens INTEGER DEFAULT 0,
            timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
            status TEXT DEFAULT 'success'
        )
    ''')
    
    # Create admin_users table
    c.execute('''
        CREATE TABLE IF NOT EXISTS admin_users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # Create user_sessions table
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_sessions (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            token TEXT UNIQUE NOT NULL,
            user_type TEXT NOT NULL,
            user_id TEXT NOT NULL,
            created_at TEXT DEFAULT CURRENT_TIMESTAMP,
            expires_at TEXT NOT NULL
        )
    ''')
    
    # Insert default API key if no keys exist
    c.execute("SELECT COUNT(*) FROM api_keys")
    if c.fetchone()[0] == 0:
        default_key = os.getenv("API_SECRET_KEY", "change-secret-key-2026")
        c.execute(
            "INSERT INTO api_keys (key, name, token_limit) VALUES (?, ?, ?)",
            (default_key, "Default Key", -1)
        )
    
    # Insert default admin if no admins exist
    c.execute("SELECT COUNT(*) FROM admin_users")
    admin_count = c.fetchone()[0]
    print(f"[DB] Admin users count: {admin_count}")
    if admin_count == 0:
        admin_pass = os.getenv("ADMIN_PASSWORD", "admin-password-2026")
        admin_hash = hash_password(admin_pass)
        print(f"[DB] Creating admin user with hash: {admin_hash}")
        c.execute(
            "INSERT INTO admin_users (username, password_hash) VALUES (?, ?)",
            ("admin", admin_hash)
        )
        print("[DB] Admin user created successfully")
    
    conn.commit()
    conn.close()
    print("[DB] Database initialization complete")

# Initialize DB on startup
complete_init_db()

def extract_api_key(request: Request) -> str:
    auth = request.headers.get("authorization", "")
    return auth.replace("Bearer ", "").strip()


class AsyncBrowserThread(threading.Thread):
    def __init__(self):
        super().__init__(daemon=True)
        self.loop = asyncio.new_event_loop()
        self.ready_event = threading.Event()
        self.browser = None
        self.playwright = None

    def run(self):
        asyncio.set_event_loop(self.loop)
        self.loop.run_until_complete(self._start_browser())
        self.ready_event.set()
        print("[LITE-SERVER].....")
        self.loop.run_forever()

    async def _start_browser(self):
        from playwright.async_api import async_playwright
        print("[LITE-SERVER].....")
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(
            headless=True,
            channel="chrome",
            args=[
                '--disable-blink-features=AutomationControlled',
                '--no-sandbox',
                '--disable-gpu',
                '--disable-dev-shm-usage-for-fast-performance',
                '--disable-setuid-sandbox',
            ]
        )

    async def _talk_to_chatgpt(self, prompt: str):
        context = await self.browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
            viewport={'width': 1920, 'height': 1080}
        )
        
        await context.add_init_script("Object.defineProperty(navigator, 'webdriver', {get: () => undefined})")
        
        page = await context.new_page()
        
        try:
            page.set_default_timeout(120000)
            await page.goto("https://chatgpt.com/", wait_until="domcontentloaded")
            
            await page.wait_for_selector('#prompt-textarea', timeout=60000)
            await page.fill('#prompt-textarea', prompt)
            await asyncio.sleep(0.5)
            await page.press('#prompt-textarea', 'Enter')
            
            await page.wait_for_selector('[data-message-author-role="assistant"]', timeout=120000)
            
            last_text = ""
            unchanged_count = 0
            while unchanged_count < 4:
                messages = await page.query_selector_all('[data-message-author-role="assistant"]')
                if messages:
                    current_text = await messages[-1].inner_text()
                    if current_text == last_text and current_text.strip() != "":
                        unchanged_count += 1
                    else:
                        last_text = current_text
                        unchanged_count = 0
                await asyncio.sleep(0.5)
                
            return last_text.strip()
            
        except Exception as e:
            print(f"[LITE-SERVER] Error: {e}")
            raise e
        finally:
            await page.close()
            await context.close()

    def process_request(self, prompt: str):
        if not self.ready_event.wait(timeout=30):
            raise Exception("Error From Browser")
            
        future = asyncio.run_coroutine_threadsafe(self._talk_to_chatgpt(prompt), self.loop)
        return future.result(timeout=120)

browser_engine = AsyncBrowserThread()
browser_engine.start()

# ====================================================================
# Smart Prompt Builder
# ====================================================================
def format_prompt(messages, tools=None):
    parts = []
    system_parts = []
    has_tool_results = False
    user_question = ""
    
    for msg in messages:
        role = msg.get("role", "")
        msg_type = msg.get("type", "")
        content = msg.get("content", "")
        
        if isinstance(content, list):
            text_parts = []
            for item in content:
                if isinstance(item, dict):
                    text_parts.append(item.get("text", item.get("content", str(item))))
                else:
                    text_parts.append(str(item))
            content = "\n".join(text_parts)
        
        if role == "system":
            system_parts.append(content)
        elif role == "tool":
            has_tool_results = True
            tool_name = msg.get("name", "tool")
            parts.append(f"[TOOL RESULT from '{tool_name}']:\n{content}")
        elif msg_type == "function_call_output":
            has_tool_results = True
            call_id = msg.get("call_id", "")
            output_content = msg.get("output", content)
            parts.append(f"[TOOL RESULT (call_id: {call_id})]:\n{output_content}")
        elif msg_type == "function_call":
            func_name = msg.get("name", "?")
            func_args = msg.get("arguments", "{}")
            parts.append(f"[PREVIOUS TOOL CALL: Called '{func_name}' with arguments: {func_args}]")
        elif role == "assistant":
            assistant_content = content if content else ""
            tool_calls_in_msg = msg.get("tool_calls", [])
            if tool_calls_in_msg:
                tc_descriptions = []
                for tc in tool_calls_in_msg:
                    func = tc.get("function", {})
                    tc_descriptions.append(f"Called '{func.get('name', '?')}' with: {func.get('arguments', '{}')}")
                assistant_content += "\n[Previous tool calls: " + "; ".join(tc_descriptions) + "]"
            if assistant_content.strip():
                parts.append(f"[Assistant]: {assistant_content}")
        elif role == "user" or (msg_type == "message" and role != "system"):
            user_question = content
            parts.append(content)
            has_tool_results = False
        elif content:
            parts.append(content)
    
    final = ""
    
    if system_parts:
        if tools and not has_tool_results:
            final += "=== YOUR ROLE ===\n"
            final += "\n\n".join(system_parts)
            final += "\n=== END OF ROLE ===\n\n"
        else:
            final += "=== SYSTEM INSTRUCTIONS (FOLLOW STRICTLY) ===\n"
            final += "\n\n".join(system_parts)
            final += "\n=== END OF INSTRUCTIONS ===\n\n"
    
    if tools and not has_tool_results:
        final += format_tools_instruction(tools, user_question)
    
    if has_tool_results:
        final += "=== CONTEXT FROM TOOLS ===\n"
        final += "The following information was retrieved by the tools you requested.\n"
        final += "Use ONLY this information to answer the user's question.\n\n"
    
    if parts:
        final += "\n".join(parts)
    
    if has_tool_results:
        final += "\n\n=== INSTRUCTION ===\n"
        final += "Now answer the user's question based ONLY on the tool results above.\n"
    
    return final

def format_tools_instruction(tools, user_question=""):
    instruction = "\n=== MANDATORY TOOL USAGE ===\n"
    instruction += "You MUST use one of the tools below to answer this question.\n"
    instruction += "Do NOT answer directly. Do NOT say you don't have information.\n"
    instruction += "You MUST respond with ONLY a JSON object to call the tool.\n\n"
    
    instruction += "RESPONSE FORMAT - respond with ONLY this JSON, nothing else:\n"
    instruction += '{"tool_calls": [{"name": "TOOL_NAME", "arguments": {"param": "value"}}]}\n\n'
    
    instruction += "RULES:\n"
    instruction += "- Your ENTIRE response must be valid JSON only\n"
    instruction += "- No markdown, no code blocks, no explanation\n"
    instruction += "- No text before or after the JSON\n\n"
    
    instruction += "Available tools:\n\n"
    
    for tool in tools:
        func = tool.get("function", tool)
        name = func.get("name", "unknown")
        desc = func.get("description", "No description")
        params = func.get("parameters", {})
        
        instruction += f"Tool: {name}\n"
        instruction += f"Description: {desc}\n"
        
        if params.get("properties"):
            instruction += "Parameters:\n"
            required_params = params.get("required", [])
            for param_name, param_info in params["properties"].items():
                param_type = param_info.get("type", "string")
                param_desc = param_info.get("description", "")
                is_required = "required" if param_name in required_params else "optional"
                instruction += f"  - {param_name} ({param_type}, {is_required}): {param_desc}\n"
        instruction += "\n"
    
    instruction += "=== END OF TOOLS ===\n\n"
    
    first_tool = tools[0] if tools else {}
    first_func = first_tool.get("function", first_tool)
    first_name = first_func.get("name", "tool")
    
    instruction += f'EXAMPLE: If the user asks a question, respond with:\n'
    instruction += '{"tool_calls": [{"name": "' + first_name + '", "arguments": {"input": "the user question here"}}]}\n\n'
    
    instruction += "Now respond with the JSON to call the appropriate tool:\n\n"
    return instruction

def parse_tool_calls(response_text):
    cleaned = response_text.strip()
    if "```" in cleaned:
        code_block_match = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', cleaned, re.DOTALL)
        if code_block_match:
            cleaned = code_block_match.group(1).strip()
    
    json_candidates = [cleaned]
    json_match = re.search(r'\{[\s\S]*"tool_calls"[\s\S]*\}', cleaned)
    if json_match:
        json_candidates.append(json_match.group(0))
    
    for candidate in json_candidates:
        try:
            parsed = json.loads(candidate)
            if isinstance(parsed, dict) and "tool_calls" in parsed:
                raw_calls = parsed["tool_calls"]
                if isinstance(raw_calls, list) and len(raw_calls) > 0:
                    formatted_calls = []
                    for call in raw_calls:
                        tool_name = call.get("name", "")
                        arguments = call.get("arguments", {})
                        if isinstance(arguments, dict):
                            arguments_str = json.dumps(arguments, ensure_ascii=False)
                        else:
                            arguments_str = str(arguments)
                        
                        formatted_calls.append({
                            "id": f"call_{uuid.uuid4().hex[:24]}",
                            "type": "function",
                            "function": {
                                "name": tool_name,
                                "arguments": arguments_str
                            }
                        })
                    return formatted_calls
        except (json.JSONDecodeError, TypeError, KeyError):
            continue
    return None

# ====================================================================
# FastAPI App
# ====================================================================
app = FastAPI(title="open-gpt")

# ====================================================================
# Authentication Endpoints
# ====================================================================

@app.get("/")
async def login_page():
    """Serve login page"""
    try:
        import pathlib
        static_dir = pathlib.Path(__file__).parent / "static"
        login_file = static_dir / "login.html"
        if login_file.exists():
            with open(login_file, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        else:
            return HTMLResponse(content="<h1>Login page not found</h1>", status_code=404)
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error: {str(e)}</h1>", status_code=500)

@app.get("/admin")
async def admin_dashboard(session: str = Cookie(None)):
    """Serve admin dashboard"""
    if not session or not validate_session(session) or validate_session(session).get("user_type") != "admin":
        return HTMLResponse(content="<script>window.location.href='/'</script>")
    try:
        import pathlib
        static_dir = pathlib.Path(__file__).parent / "static"
        admin_file = static_dir / "admin.html"
        if admin_file.exists():
            with open(admin_file, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        else:
            return HTMLResponse(content="<h1>Admin page not found</h1>", status_code=404)
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error: {str(e)}</h1>", status_code=500)

@app.get("/user")
async def user_portal(session: str = Cookie(None)):
    """Serve user portal"""
    if not session or not validate_session(session) or validate_session(session).get("user_type") != "user":
        return HTMLResponse(content="<script>window.location.href='/'</script>")
    try:
        import pathlib
        static_dir = pathlib.Path(__file__).parent / "static"
        user_file = static_dir / "user.html"
        if user_file.exists():
            with open(user_file, "r", encoding="utf-8") as f:
                return HTMLResponse(content=f.read())
        else:
            return HTMLResponse(content="<h1>User page not found</h1>", status_code=404)
    except Exception as e:
        return HTMLResponse(content=f"<h1>Error: {str(e)}</h1>", status_code=500)

@app.post("/auth/admin/login")
async def admin_login(request: Request):
    """Admin login endpoint"""
    try:
        data = await request.json()
    except:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    
    username = data.get("username")
    password = data.get("password")
    
    if not username or not password:
        return JSONResponse(status_code=400, content={"error": "Username and password required"})
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT password_hash FROM admin_users WHERE username = ?", (username,))
    row = c.fetchone()
    conn.close()
    
    if not row:
        print(f"[AUTH] Admin user '{username}' not found in database")
        return JSONResponse(status_code=401, content={"error": "Invalid credentials"})
    
    if not verify_password(password, row[0]):
        print(f"[AUTH] Invalid password for admin user '{username}'")
        return JSONResponse(status_code=401, content={"error": "Invalid credentials"})
    
    token = create_session("admin", username, hours=24)
    print(f"[AUTH] Admin user '{username}' logged in successfully")
    return {"success": True, "token": token}

@app.post("/auth/user/login")
async def user_login(request: Request):
    """User login with API key"""
    try:
        data = await request.json()
    except:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    
    api_key = data.get("api_key")
    
    if not api_key:
        return JSONResponse(status_code=400, content={"error": "API key required"})
    
    key_record = validate_api_key(api_key)
    if not key_record:
        return JSONResponse(status_code=401, content={"error": "Invalid API key"})
    
    token = create_session("user", api_key, hours=168)  # 7 days
    return {"success": True, "token": token}

@app.post("/auth/logout")
async def logout(request: Request):
    """Logout endpoint"""
    auth = request.headers.get("authorization", "")
    token = auth.replace("Bearer ", "").strip()
    if token:
        logout_session(token)
    return {"success": True}

@app.post("/v1/chat/completions")
async def chat_completions(request: Request):

    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": {"message": "Invalid JSON payload"}})
    
    api_key = extract_api_key(request)
    key_record = validate_api_key(api_key)
    if not key_record:
        return JSONResponse(status_code=401, content={"error": {"message": "Invalid or expired API Key"}})

    messages = data.get("messages", [])
    if not messages:
        return JSONResponse(status_code=400, content={"error": {"message": "messages field is required"}})
        
    try:
        tools = data.get("tools", None)
        prompt = format_prompt(messages, tools=tools)
        
        start_time = time.time()
        print(f"[LITE-SERVER]..... ({len(prompt)} len)")
        
        response_text = browser_engine.process_request(prompt)
        
        p_tokens = len(prompt.split())
        c_tokens = len(response_text.split())
        
        update_usage(api_key, p_tokens, c_tokens, "/v1/chat/completions")
        
        tool_calls = None
        if tools:
            tool_calls = parse_tool_calls(response_text)

        if tool_calls:
            return {
                "id": f"chatcmpl-{uuid.uuid4().hex[:29]}",
                "object": "chat.completion",
                "created": int(start_time),
                "model": data.get("model", "gpt-4o-mini"),
                "choices": [{
                    "index": 0,
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": tool_calls
                    },
                    "finish_reason": "tool_calls"
                }],
                "usage": {
                    "prompt_tokens": p_tokens,
                    "completion_tokens": c_tokens,
                    "total_tokens": p_tokens + c_tokens
                }
            }
        else:
            return {
                "id": f"chatcmpl-{uuid.uuid4().hex[:29]}",
                "object": "chat.completion",
                "created": int(start_time),
                "model": data.get("model", "gpt-4o-mini"),
                "choices": [{
                    "index": 0,
                    "message": {"role": "assistant", "content": response_text},
                    "finish_reason": "stop"
                }],
                "usage": {
                    "prompt_tokens": p_tokens,
                    "completion_tokens": c_tokens,
                    "total_tokens": p_tokens + c_tokens
                }
            }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.post("/v1/responses")
async def responses(request: Request):

    try:
        data = await request.json()
    except Exception:
        return JSONResponse(status_code=400, content={"error": {"message": "Invalid JSON payload"}})
        
    api_key = extract_api_key(request)
    key_record = validate_api_key(api_key)
    if not key_record:
        return JSONResponse(status_code=401, content={"error": {"message": "Invalid or expired API Key"}})

    input_data = data.get("input", "")
    if isinstance(input_data, str):
        messages = [{"role": "user", "content": input_data}]
    elif isinstance(input_data, list):
        messages = input_data
    else:
        messages = data.get("messages", [])

    if not messages:
        return JSONResponse(status_code=400, content={"error": {"message": "input field is required"}})

    try:
        tools = data.get("tools", None)
        instructions = data.get("instructions", "")
        if instructions:
            messages.insert(0, {"role": "system", "content": instructions})
            
        prompt = format_prompt(messages, tools=tools)
        start_time = time.time()
        
        response_text = browser_engine.process_request(prompt)
        p_tokens = len(prompt.split())
        c_tokens = len(response_text.split())

        update_usage(api_key, p_tokens, c_tokens, "/v1/responses")

        tool_calls = None
        if tools:
            tool_calls = parse_tool_calls(response_text)

        if tool_calls:
            output_items = []
            for tc in tool_calls:
                output_items.append({
                    "type": "function_call",
                    "id": tc["id"],
                    "call_id": tc["id"],
                    "name": tc["function"]["name"],
                    "arguments": tc["function"]["arguments"],
                    "status": "completed"
                })
            
            return {
                "id": f"resp-{uuid.uuid4().hex[:29]}",
                "object": "response",
                "created_at": int(start_time),
                "model": data.get("model", "gpt-4o-mini"),
                "status": "completed",
                "output": output_items,
                "usage": {
                    "input_tokens": p_tokens,
                    "output_tokens": c_tokens,
                    "total_tokens": p_tokens + c_tokens
                }
            }
        else:
            return {
                "id": f"resp-{uuid.uuid4().hex[:29]}",
                "object": "response",
                "created_at": int(start_time),
                "model": data.get("model", "gpt-4o-mini"),
                "status": "completed",
                "output": [
                    {
                        "type": "message",
                        "role": "assistant",
                        "content": [{"type": "output_text", "text": response_text}]
                    }
                ],
                "usage": {
                    "input_tokens": p_tokens,
                    "output_tokens": c_tokens,
                    "total_tokens": p_tokens + c_tokens
                }
            }
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/v1/models")
async def list_models():

    return {
        "object": "list",
        "data": [{"id": "gpt-4o-mini", "object": "model", "owned_by": "open-gpt"}]
    }

@app.get("/")
async def health_check():
    return {"status": "running", "message": "open-gpt Server is active!"}

# ====================================================================
# Admin Endpoints — API Key Management
# (Protected by Session Authentication)
# ====================================================================

def require_admin(request: Request):
    auth = request.headers.get("authorization", "")
    token = auth.replace("Bearer ", "").strip()
    session = validate_session(token)
    if not session or session.get("user_type") != "admin":
        raise HTTPException(status_code=403, detail="Admin access required")

@app.get("/admin/keys")
async def list_keys(request: Request):
    """List all API keys"""
    require_admin(request)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, key, name, token_limit, tokens_used, requests_count, is_active, created_at, last_used, notes FROM api_keys")
    rows = c.fetchall()
    conn.close()
    columns = ["id","key","name","token_limit","tokens_used","requests_count","is_active","created_at","last_used","notes"]
    return {"keys": [dict(zip(columns, row)) for row in rows]}

@app.post("/admin/keys/create")
async def create_key(request: Request):
    """Create a new API key"""
    require_admin(request)
    try:
        data = await request.json()
    except:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    
    new_key = data.get("key") or f"ogpt-{uuid.uuid4().hex[:32]}"
    name = data.get("name", "")
    token_limit = data.get("token_limit", -1)  # -1 = unlimited
    notes = data.get("notes", "")
    
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute(
            "INSERT INTO api_keys (key, name, token_limit, notes) VALUES (?, ?, ?, ?)",
            (new_key, name, token_limit, notes)
        )
        conn.commit()
    except sqlite3.IntegrityError:
        conn.close()
        return JSONResponse(status_code=409, content={"error": "Key already exists"})
    conn.close()
    return {"success": True, "key": new_key, "name": name, "token_limit": token_limit}

@app.post("/admin/keys/update")
async def update_key(request: Request):
    """Update an existing API key"""
    require_admin(request)
    try:
        data = await request.json()
    except:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    
    target_key = data.get("key")
    if not target_key:
        return JSONResponse(status_code=400, content={"error": "key field required"})
    
    fields = []
    values = []
    for field in ["name", "token_limit", "notes", "is_active"]:
        if field in data:
            fields.append(f"{field} = ?")
            values.append(data[field])
    
    if not fields:
        return JSONResponse(status_code=400, content={"error": "No fields to update"})
    
    values.append(target_key)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute(f"UPDATE api_keys SET {', '.join(fields)} WHERE key = ?", values)
    updated = c.rowcount
    conn.commit()
    conn.close()
    return {"success": True, "updated": updated > 0}

@app.delete("/admin/keys/{key_to_delete}")
async def delete_key(key_to_delete: str, request: Request):
    """Delete an API key"""
    require_admin(request)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("DELETE FROM api_keys WHERE key = ?", (key_to_delete,))
    deleted = c.rowcount
    conn.commit()
    conn.close()
    return {"success": True, "deleted": deleted > 0}

@app.post("/admin/keys/reset-tokens")
async def reset_tokens(request: Request):
    """Reset token usage counter for a key"""
    require_admin(request)
    try:
        data = await request.json()
    except:
        return JSONResponse(status_code=400, content={"error": "Invalid JSON"})
    target_key = data.get("key")
    if not target_key:
        return JSONResponse(status_code=400, content={"error": "key field required"})
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("UPDATE api_keys SET tokens_used = 0, requests_count = 0 WHERE key = ?", (target_key,))
    conn.commit()
    conn.close()
    return {"success": True}

@app.get("/admin/logs")
async def get_logs(request: Request, limit: int = 100):
    """Get recent usage logs"""
    require_admin(request)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT * FROM usage_logs ORDER BY id DESC LIMIT ?", (limit,))
    rows = c.fetchall()
    conn.close()
    columns = ["id","api_key","endpoint","prompt_tokens","completion_tokens","total_tokens","timestamp","status"]
    return {"logs": [dict(zip(columns, row)) for row in rows]}

@app.get("/admin/stats")
async def get_stats(request: Request):
    """Get overall statistics"""
    require_admin(request)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT COUNT(*), SUM(tokens_used), SUM(requests_count) FROM api_keys")
    total_keys, total_tokens, total_requests = c.fetchone()
    c.execute("SELECT COUNT(*) FROM api_keys WHERE is_active = 1")
    active_keys = c.fetchone()[0]
    conn.close()
    return {
        "total_keys": total_keys,
        "active_keys": active_keys,
        "total_tokens_used": total_tokens or 0,
        "total_requests": total_requests or 0
    }

@app.get("/key/info")
async def key_info(request: Request):
    """Get info about the current API key (for users)"""
    api_key = extract_api_key(request)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT name, token_limit, tokens_used, requests_count, created_at, last_used FROM api_keys WHERE key=? AND is_active=1", (api_key,))
    row = c.fetchone()
    conn.close()
    if not row:
        return JSONResponse(status_code=401, content={"error": "Invalid API Key"})
    name, token_limit, tokens_used, requests_count, created_at, last_used = row
    remaining = "unlimited" if token_limit == -1 else max(0, token_limit - tokens_used)
    return {
        "name": name,
        "tokens_used": tokens_used,
        "token_limit": "unlimited" if token_limit == -1 else token_limit,
        "tokens_remaining": remaining,
        "requests_count": requests_count,
        "created_at": created_at,
        "last_used": last_used
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=7777)
