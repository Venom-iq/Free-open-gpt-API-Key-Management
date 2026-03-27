# 🔥 open-gpt — Admin Dashboard & API Key Management

A self-hosted admin dashboard for managing API keys, user authentication, and usage tracking with OpenAI-compatible API endpoints.

## 📋 Features

- ✅ Admin Dashboard with web UI
- ✅ API Key Management (create, update, delete, toggle)
- ✅ User Authentication & Session Management
- ✅ Usage Statistics & Tracking
- ✅ Token Limit Management
- ✅ User Portal for API key holders
- ✅ Docker-ready with persistent database
- ✅ OpenAI-compatible API endpoints

---

## 🚀 Quick Start

### Prerequisites
- Docker & Docker Compose
- Port 7777 available

### Installation & Running

```bash
# Clone the repository
git clone <your-repo>
cd mse_ai_api-main

# Start the application
docker-compose up --build -d

# Check if running
docker-compose ps
```

The application will be available at: **http://localhost:7777/**

---

## 🔐 Default Credentials

| Field | Value |
|-------|-------|
| **Admin Username** | `admin` |
| **Admin Password** | `admin-password-2026` |
| **Default API Key** | `admin-password-2026` |

> ⚠️ **Important**: Change these credentials in production!

---

## 📊 Database Schema

The application uses SQLite with the following tables:

### `admin_users`
```sql
CREATE TABLE admin_users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    username TEXT UNIQUE NOT NULL,
    password_hash TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

### `user_sessions`
```sql
CREATE TABLE user_sessions (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    token TEXT UNIQUE NOT NULL,
    user_type TEXT NOT NULL,
    user_id TEXT NOT NULL,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP,
    expires_at TEXT NOT NULL
);
```

### `api_keys`
```sql
CREATE TABLE api_keys (
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
```

### `usage_logs`
```sql
CREATE TABLE usage_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    api_key TEXT NOT NULL,
    endpoint TEXT NOT NULL,
    prompt_tokens INTEGER DEFAULT 0,
    completion_tokens INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    timestamp TEXT DEFAULT CURRENT_TIMESTAMP,
    status TEXT DEFAULT 'success'
);
```

---

## 🌐 API Endpoints

### Authentication

#### Admin Login
```bash
POST /auth/admin/login
Content-Type: application/json

{
  "username": "admin",
  "password": "admin-password-2026"
}
```

#### User Login (with API Key)
```bash
POST /auth/user/login
Content-Type: application/json

{
  "api_key": "your-api-key"
}
```

#### Logout
```bash
POST /auth/logout
Authorization: Bearer <session-token>
```

---

### Admin Endpoints (Protected)

All admin endpoints require a valid session token in the `Authorization` header.

#### List All API Keys
```bash
GET /admin/keys
Authorization: Bearer <session-token>
```

**Response:**
```json
{
  "keys": [
    {
      "id": 1,
      "key": "ogpt-abc123...",
      "name": "My Client",
      "token_limit": 100000,
      "tokens_used": 5000,
      "requests_count": 150,
      "is_active": 1,
      "created_at": "2026-03-22T00:00:00",
      "last_used": "2026-03-22T02:00:00",
      "notes": "Production key"
    }
  ]
}
```

#### Create New API Key
```bash
POST /admin/keys/create
Authorization: Bearer <session-token>
Content-Type: application/json

{
  "name": "My Client",
  "token_limit": 100000,
  "notes": "Optional notes"
}
```

#### Update API Key
```bash
POST /admin/keys/update
Authorization: Bearer <session-token>
Content-Type: application/json

{
  "key": "ogpt-abc123...",
  "is_active": 1,
  "token_limit": 50000
}
```

#### Delete API Key
```bash
DELETE /admin/keys/{key}
Authorization: Bearer <session-token>
```

#### Get Statistics
```bash
GET /admin/stats
Authorization: Bearer <session-token>
```

**Response:**
```json
{
  "total_keys": 5,
  "active_keys": 4,
  "total_tokens_used": 50000,
  "total_requests": 1200
}
```

---

### Chat API Endpoints

#### Chat Completions (OpenAI Compatible)
```bash
POST /v1/chat/completions
Authorization: Bearer <api-key>
Content-Type: application/json

{
  "model": "gpt-4o-mini",
  "messages": [
    {
      "role": "user",
      "content": "Hello, how are you?"
    }
  ]
}
```

#### List Models
```bash
GET /v1/models
Authorization: Bearer <api-key>
```

---

## 🔧 Configuration

### Environment Variables

Create a `.env` file or set these in `docker-compose.yml`:

```bash
# Database path (inside container)
DB_PATH=/data/open_gpt_keys.db

# Admin password
ADMIN_PASSWORD=admin-password-2026

# Default API key
API_SECRET_KEY=admin-password-2026

# Master admin key (for API management)
MASTER_ADMIN_KEY=admin-master-key-2026

# Python output buffering
PYTHONUNBUFFERED=1
```

-


1. **Get your machine IP:**
   ```bash
   ipconfig  # Windows
   ifconfig  # Linux/Mac
   ```

2. **In n8n, create HTTP request:**
   - **URL:** `http://<your-ip>:7777/v1`
   - **Method:** POST
   - **Headers:**
     ```
     Authorization: Bearer <your-api-key>
     Content-Type: application/json
     ```
   - **Body:**
     ```json
     {
       "model": "gpt-4o-mini",
       "messages": [{"role": "user", "content": "Your prompt"}]
     }
     ```

### From Docker Container

If n8n is in Docker on the same network:
- **URL:** `http://<your-machine-ip>:7777/`
- Same headers and body as above

---

## 📱 Admin Dashboard

Access the web interface at: **http://<your-machine-ip>:7777/**

### Features:
- 📊 View statistics (total keys, active keys, tokens used, requests)
- 🔑 Create new API keys with custom names and limits
- ✏️ Update existing keys (toggle active/inactive, change limits)
- 🗑️ Delete keys
- 📈 View usage logs
- 🚪 Logout button

---

## 🛠️ Troubleshooting

### Container won't start
```bash
# Check logs
docker-compose logs open-gpt

# Rebuild
docker-compose down -v
docker-compose up --build -d
```

### Can't connect from n8n
- If n8n is external: Use your machine IP (e.g., `192.168.x.x`)
- If n8n is in Docker: Use service name `open-gpt:7777`
- Check firewall allows port 7777

### Database issues
```bash
# Reset database (WARNING: deletes all data)
docker-compose down -v
docker-compose up -d
```

---

## 📦 Docker Compose

```yaml
version: "3.8"

services:
  open-gpt:
    build: .
    container_name: open-gpt
    restart: unless-stopped
    ports:
      - "7777:7777"
    environment:
      - API_SECRET_KEY=admin-password-2026
      - MASTER_ADMIN_KEY=admin-master-key-2026
      - DB_PATH=/data/open_gpt_keys.db
      - PYTHONUNBUFFERED=1
    volumes:
      - open_gpt_data:/data

volumes:
  open_gpt_data:
```

---

## 🔒 Security Notes

- ✅ Passwords are hashed with SHA256
- ✅ Session tokens expire after 24 hours (admin) or 7 days (user)
- ✅ API keys are stored in database
- ⚠️ Change default credentials before production
- ⚠️ Use HTTPS in production
- ⚠️ Keep database backups## 🧹 Maintenance

### Clean Database

To reset the database and remove all data:

```bash
# Stop containers and remove volumes
docker-compose down -v

# Restart with fresh database
docker-compose up -d
```

### Clear Usage Logs

To delete all usage logs while keeping API keys and users:

```bash
# Connect to container
docker exec -it open-gpt python

# Run in Python shell
import sqlite3
conn = sqlite3.connect('/data/open_gpt_keys.db')
c = conn.cursor()
c.execute("DELETE FROM usage_logs")
conn.commit()
conn.close()
print("Usage logs cleared")
exit()
```

### Reset Specific API Key Tokens

```bash
docker exec -it open-gpt python

import sqlite3
conn = sqlite3.connect('/data/open_gpt_keys.db')
c = conn.cursor()
c.execute("UPDATE api_keys SET tokens_used = 0 WHERE key = 'your-api-key'")
conn.commit()
conn.close()
print("Tokens reset")
exit()
```

### Backup Database

```bash
# Copy database from container
docker cp open-gpt:/data/open_gpt_keys.db ./backup_$(date +%Y%m%d_%H%M%S).db
```

### Restore Database

```bash
# Copy backup back to container
docker cp ./backup_20260322_021500.db open-gpt:/data/open_gpt_keys.db

# Restart container
docker-compose restart open-gpt
```

---

## 🔒 Security & Privacy

- Database is stored in Docker volume at `/data/open_gpt_keys.db`
- All passwords are hashed with SHA256
- Session tokens are cryptographically secure
- No personal data is logged by default
- Use `docker-compose down -v` to completely remove all data

---
#
------------------------------
☕ الدعم والتطوير (Support & Development)
إذا وجدت هذا المشروع مفيداً وترغب في دعم استمرار تطويره وإضافة ميزات جديدة، يمكنك المساهمة عبر إرسال دعمك إلى العناوين التالية:
💰 حسابات التبرع (Donation Addresses)

| العملة (Asset) | الشبكة (Network) | العنوان (Address) |
|---|---|---|
| USDT | TRC20 (TRX) | TXtEUEHTvpjxjqNzjzQnQiHtTky7DNHFqM |
| BTC | BEP20 (BSC) | 0xc8630d0645b87c03c3144ed6b96a3197416322d7 |
| ETC | BEP20 (BSC) | 0xc8630d0645b87c03c3144ed6b96a3197416322d7 |

ملاحظة: تأكد من اختيار الشبكة الصحيحة عند الإرسال لتجنب فقدان الأموال. شكراً لدعمكم المستمر! 🚀



------------------------------






Note: Make sure to select the correct network when sending to avoid losing funds. Thank you for your continued support! 🚀

------------------------------

🛠️ Upcoming Features

* Support for additional models (Claude, Gemini).

* Token usage alert system.

* More interactive graphical interface.


🛠️ الميزات القادمة




* دعم نماذج إضافية (Claude, Gemini).
* نظام تنبيهات لاستهلاك التوكينز.
* واجهة رسومية أكثر تفاعلية.




