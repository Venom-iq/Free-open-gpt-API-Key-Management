-- Initialize open-gpt database with all tables and default data

-- Create api_keys table
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
);

-- Create usage_logs table
CREATE TABLE IF NOT EXISTS usage_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_key TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'success'
);

-- Create admin_users table
CREATE TABLE IF NOT EXISTS admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);

-- Create user_sessions table
CREATE TABLE IF NOT EXISTS user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT UNIQUE NOT NULL,
    user_type TEXT NOT NULL,
    user_id TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT NOT NULL
);

-- Insert default API key
INSERT OR IGNORE INTO api_keys (key, name, token_limit) 
VALUES ('change-secret-key-2026', 'Default Key', -1);

-- Insert default admin user (password: admin-password-2026)
-- SHA256 hash of "admin-password-2026"
INSERT OR IGNORE INTO admin_users (username, password_hash) 
VALUES ('admin', '9131936cce772522cac97942feff046373b68ede256256689a616cee2225b38d');
