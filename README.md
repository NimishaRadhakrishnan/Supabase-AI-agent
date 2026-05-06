# 🤖 Supabase Telegram Agent
### *Talk to your database in plain English — right from Telegram.*

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![Telegram](https://img.shields.io/badge/Telegram_Bot-2CA5E0?style=for-the-badge&logo=telegram&logoColor=white)](https://core.telegram.org/bots)
[![Supabase](https://img.shields.io/badge/Supabase-3ECF8E?style=for-the-badge&logo=supabase&logoColor=white)](https://supabase.com)
[![Groq](https://img.shields.io/badge/Groq_AI-FF6B35?style=for-the-badge&logo=data:image/svg+xml;base64,PHN2ZyB4bWxucz0iaHR0cDovL3d3dy53My5vcmcvMjAwMC9zdmciIHZpZXdCb3g9IjAgMCAyNCAyNCI+PHBhdGggZmlsbD0id2hpdGUiIGQ9Ik0xMiAyQzYuNDggMiAyIDYuNDggMiAxMnM0LjQ4IDEwIDEwIDEwIDEwLTQuNDggMTAtMTBTMTcuNTIgMiAxMiAyem0tMSAxNHYtNGgtMlY5aDZ2M2gtMnY0aC0yeiIvPjwvc3ZnPg==&logoColor=white)](https://groq.com)
[![License](https://img.shields.io/badge/License-MIT-green?style=for-the-badge)](LICENSE)
[![Version](https://img.shields.io/badge/Version-2.1-blue?style=for-the-badge)](CHANGELOG.md)
[![Status](https://img.shields.io/badge/Status-Active-brightgreen?style=for-the-badge)]()

</div>

<div align="center">

*Type `"Show me all pending orders"` in Telegram. Get your database results instantly.*
*No SQL client. No dashboard. No switching tools.*

</div>

---

## 📖 Table of Contents

- [Overview](#-overview)
- [Real-World Problem](#-real-world-problem)
- [Who Is This For?](#-who-is-this-for)
- [System Architecture](#-system-architecture)
- [Feature Walkthrough](#-feature-walkthrough)
- [Database Schema](#-database-schema-mock-data)
- [Project Workflow](#-project-workflow)
- [Key Technical Decisions](#-key-technical-decisions)
- [Project Structure](#-project-structure)
- [Environment Variables](#-environment-variables)
- [Installation & Setup](#-installation--setup)
- [Running the Agent](#-running-the-agent)
- [Command Reference](#-command-reference)
- [Natural Language Examples](#-natural-language-examples)
- [The Delete Approval Flow](#-the-delete-approval-flow-safety-first)
- [Challenges & Learnings](#-challenges--learnings)
- [Future Improvements](#-future-improvements)
- [Learning Outcomes](#-learning-outcomes-for-students)
- [FAQ](#-faq)
- [Common Mistakes](#-common-mistakes-beginners-make)
- [Author](#-author)

---

## 🌟 Overview

**Supabase Telegram Agent** is an AI-powered database management chatbot that lives inside Telegram. It connects your Supabase (PostgreSQL) database to a conversational interface powered by **Groq's LLaMA 3.3-70B model**, letting you query, insert, update, and delete data using plain English — or precise slash commands if you prefer.

Think of it as giving your database a voice. Instead of opening a SQL client or navigating a web dashboard, you send a message on your phone and your database responds.

```
You:  "How many orders are still pending?"
Bot:  📊 orders has 3 pending row(s).

You:  "Add a new product called Widget Pro with price 49.99"
Bot:  ✅ Inserted into products:
        • id: 11
        • name: Widget Pro
        • price: 49.99
        • stock_quantity: 0
```

---

## 🚩 Real-World Problem

Database management has an accessibility problem.

Most tools — pgAdmin, Supabase Dashboard, TablePlus — require:
- A laptop open with the right software
- Knowledge of SQL syntax
- Browser access, often with VPN
- Mental context-switching away from your current workflow

For small teams, solo founders, and non-technical managers, this friction means they simply don't monitor their database. They rely on developers who may not be immediately available, creating bottlenecks.

**This project solves that** by making database operations as easy as sending a WhatsApp message — with safety guardrails (email-based approval for destructive operations) built in from day one.

---

## 👥 Who Is This For?

| Persona | Use Case |
|---|---|
| 🧑‍💻 **Solo Developer** | Monitor production data from your phone without opening a laptop |
| 📊 **Non-technical Manager** | Ask "how many new signups today?" without learning SQL |
| 🏗️ **Small Team** | Shared Telegram group with bot → everyone sees database changes |
| 🎓 **CS/DS Student** | Learn LLM tool-calling, async Python, and API integration in one project |
| 🤖 **Bot Developer** | Template for building AI agents with real-world data backends |

---

## 🏗️ System Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│                        USER (Telegram)                          │
│              Types a message or slash command                   │
└─────────────────────────┬───────────────────────────────────────┘
                          │ HTTPS (Telegram API)
┌─────────────────────────▼───────────────────────────────────────┐
│                    bot.py — Command Router                      │
│                                                                 │
│   /tables  /schema  /query  /insert  /update  /delete  /sql    │
│                           │                                     │
│                  Text (no command)?                             │
│                           │                                     │
│               services/agent.py ◄──── Groq LLaMA 3.3-70B      │
│                (NLP → SQL intent)                               │
└────────┬────────────────────────────┬───────────────────────────┘
         │                            │
         ▼                            ▼
┌────────────────┐          ┌──────────────────────┐
│  services/     │          │  services/           │
│  supabase_     │          │  report_service.py   │
│  service.py    │          │  (AI summary report) │
│                │          └──────────────────────┘
│  CRUD + SQL    │
│  via Supabase  │
│  Python SDK    │
└────────┬───────┘
         │
         ▼
┌─────────────────────────────────────────────────────────────────┐
│                  Supabase (PostgreSQL)                          │
│          users · products · orders (your tables)               │
└─────────────────────────────────────────────────────────────────┘
         │
         │  DELETE operations trigger:
         ▼
┌─────────────────────────────────────────────────────────────────┐
│              services/email_service.py                         │
│        SMTP → Manager receives HTML email with                  │
│        [✅ Approve Delete] [❌ Cancel] buttons                   │
└─────────────────────────┬───────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────────┐
│              services/approval_server.py                       │
│    Local HTTP server (port 8080) receives button click         │
│    → Executes or cancels delete → Notifies user in Telegram    │
└─────────────────────────────────────────────────────────────────┘
```

### Service Layer Map

```
main.py
├── config.py               → All env vars, validation
├── bot.py                  → Telegram handlers, command routing
└── services/
    ├── agent.py            → Groq LLaMA NLP → DB action translation
    ├── supabase_service.py → All database CRUD operations
    ├── report_service.py   → AI-generated manager summary report
    ├── email_service.py    → SMTP email notifications
    ├── approval_server.py  → HTTP server for delete approval links
    └── realtime_service.py → Supabase realtime change listener
```

---

## ✨ Feature Walkthrough

### 🗣️ Natural Language Queries
Type anything in plain English. The Groq LLaMA 3.3-70B model understands your intent, identifies the correct table, and executes the right database operation.

### ⌨️ Slash Commands (Precise Control)
For power users who want deterministic, exact operations without AI interpretation.

### 🔒 Access Control
Restrict bot usage to specific Telegram user IDs via `ALLOWED_USER_IDS`. Without this, the bot is open to anyone who finds it.

### 📧 Email-Based Delete Approval
The most important safety feature: **deletes never happen automatically.** Every delete request triggers an HTML email to the manager with a preview of the affected rows and clickable Approve/Cancel buttons.

### 📊 AI Manager Report
`/report` generates an AI-written summary of your entire database — table counts, data quality notes, business insights — formatted as a management briefing.

### 🔔 Realtime Change Notifications
`realtime_service.py` listens to Supabase's realtime WebSocket and pushes notifications to the manager's Telegram when database records change.

### 📤 Email Audit Trail
Every INSERT, UPDATE, and DELETE sends an email notification, creating a full audit trail of all data changes.

---

## 🗄️ Database Schema (Mock Data)

The project includes `mock_data.sql` — a ready-to-use test dataset. Here's what it creates:

### Table: `users`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | SERIAL | PRIMARY KEY | Auto-increment unique identifier |
| `name` | TEXT | NOT NULL | Full name of the user |
| `email` | TEXT | UNIQUE, NOT NULL | Email address (unique constraint) |
| `role` | TEXT | DEFAULT 'customer' | Role: admin / customer / manager |
| `created_at` | TIMESTAMPTZ | DEFAULT now() | UTC timestamp of account creation |

### Table: `products`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | SERIAL | PRIMARY KEY | Auto-increment unique identifier |
| `name` | TEXT | NOT NULL | Product display name |
| `category` | TEXT | NOT NULL | Category: Electronics / Home / Furniture / Office |
| `price` | DECIMAL(10,2) | NOT NULL | Price in USD (2 decimal places) |
| `stock_quantity` | INTEGER | DEFAULT 0 | Units currently in stock |
| `is_active` | BOOLEAN | DEFAULT true | Whether product is listed/active |

### Table: `orders`

| Column | Type | Constraints | Description |
|---|---|---|---|
| `id` | SERIAL | PRIMARY KEY | Auto-increment unique identifier |
| `user_id` | INTEGER | FK → users(id) CASCADE | Which user placed the order |
| `total_amount` | DECIMAL(10,2) | NOT NULL | Order total in USD |
| `status` | TEXT | DEFAULT 'pending' | pending / processing / completed / cancelled |
| `order_date` | TIMESTAMPTZ | DEFAULT now() | When the order was placed |

### Sample Questions This Dataset Answers
- *"How many orders are still pending?"* → 2
- *"What's the most expensive product?"* → Standing Desk at $499.00
- *"Show me all admin users"* → Alice Smith, Ian Malcolm
- *"What's the total value of completed orders?"* → Sum of completed order amounts
- *"Which products have low stock?"* → Ergonomic Chair (10), Standing Desk (5)

---

## 🔄 Project Workflow

Every request follows this pipeline, whether it's a typed command or plain English:

```
Step 1 ── Receive Input
         │
         ├─ Slash command → Direct handler (deterministic)
         └─ Plain text → AI agent (interpreted)
         
Step 2 ── Authenticate
         │
         └─ Check user_id against ALLOWED_USER_IDS
            (skip if empty → open access)

Step 3 ── Parse Intent (NLP path only)
         │
         └─ Send message + table list to Groq LLaMA 3.3-70B
            Model identifies: action, table, filters, data

Step 4 ── Execute Database Operation
         │
         ├─ SELECT → supabase_service.query_table()
         ├─ INSERT → supabase_service.insert_row()
         ├─ UPDATE → supabase_service.update_row()
         └─ DELETE → Approval flow (see below)

Step 5 ── Safety Gate (DELETE only)
         │
         ├─ Preview matching rows
         ├─ Store pending request with UUID
         ├─ Send approval email with HTML buttons
         └─ Wait... (no action until manager clicks)

Step 6 ── Approval Resolution
         │
         ├─ Manager clicks ✅ → approval_server receives GET
         │   → Executes delete → Notifies user in Telegram
         └─ Manager clicks ❌ → Cancels → Notifies user in Telegram

Step 7 ── Notify & Log
         │
         ├─ Send formatted result back to Telegram
         └─ Email audit trail for INSERT/UPDATE/DELETE
```

### Why Each Step Matters

**Step 1 — Dual input modes:** Slash commands are predictable and testable. Natural language is flexible and human. Supporting both means technical and non-technical users get the best experience for their style.

**Step 2 — Access control first:** Authentication is checked before any computation happens. This is a principle of secure software design — fail fast, fail safely.

**Step 3 — Context-aware NLP:** The AI agent receives the actual list of tables in your database before answering. This prevents hallucination — the model knows exactly which tables exist and can't invent one.

**Step 4/5 — Approval gate for deletes:** Reads are safe. Writes can be undone. Deletes cannot. A single wrong delete in production can be catastrophic. The email approval flow ensures a human reviews every delete before it executes, with a full preview of affected rows.

**Step 7 — Email audit trail:** Every change is logged via email. This is not optional in any serious production system — it's how you answer "who changed what and when?"

---

## 🧠 Key Technical Decisions

### Why Groq + LLaMA 3.3-70B?

| Factor | Detail |
|---|---|
| **Speed** | Groq's LPU hardware delivers sub-second inference — critical for a chatbot |
| **Capability** | LLaMA 3.3-70B understands nuanced requests with high accuracy |
| **Cost** | Groq's free tier is generous for personal/small team use |
| **Open weights** | Model is open source; not locked to a single provider |

Alternative considered: OpenAI GPT-4o — rejected for cost and latency at scale.

### Why Supabase over plain PostgreSQL?

Supabase adds three things that matter here:
1. **Realtime WebSocket subscriptions** — database change events pushed instantly
2. **Auto-generated REST API** — the Python SDK wraps CRUD without raw SQL for most operations
3. **SQL Helper Functions** — the `execute_sql`, `get_tables`, `get_table_schema` functions in `supabase_setup.sql` expose schema introspection safely via `SECURITY DEFINER`

### Why Email Approval (not Telegram buttons) for Deletes?

Telegram inline keyboard buttons expire and can be accidentally tapped. Email provides:
- **Persistence** — the approval link works even if you close Telegram
- **A paper trail** — your email client logs when the manager acted
- **Deliberateness** — opening an email to click a button forces a pause before a destructive action

### Why `asyncio.run_coroutine_threadsafe`?

The approval server runs in a background thread (HTTP server), but Telegram's bot application runs in an async event loop. Bridging the two requires `run_coroutine_threadsafe` — which submits a coroutine to the event loop from a different thread. This is the correct, safe pattern for async/sync boundary crossing in Python.

---

## 📁 Project Structure

```
supabase-telegram-agent/
│
├── main.py                      # Entry point — starts bot, realtime, approval server
├── bot.py                       # All Telegram command & message handlers
├── config.py                    # Environment variable loading & validation
│
├── services/
│   ├── __init__.py
│   ├── agent.py                 # Groq LLaMA NLP → database action agent
│   ├── supabase_service.py      # All Supabase CRUD operations (async)
│   ├── report_service.py        # AI-generated manager report generator
│   ├── email_service.py         # SMTP email sending (notifications + approvals)
│   ├── approval_server.py       # HTTP server for delete approval link handling
│   └── realtime_service.py      # Supabase realtime change listener
│
├── supabase_setup.sql           # ⚠️ Run this first in Supabase SQL Editor
├── mock_data.sql                # Sample tables + data for testing
├── test_email.py                # SMTP configuration test script
│
├── requirements.txt             # Python dependencies (4 packages)
├── .env.example                 # Template for environment variables
├── .env                         # Your actual credentials (git-ignored)
└── README.md                    # This file
```

### What Each File Does

**`main.py`** — The conductor. Validates config, starts the realtime listener and approval HTTP server in background threads, then starts the Telegram polling loop. Only 30 lines — keeps startup clean.

**`bot.py`** — The largest file. Contains every Telegram command handler, the natural language catch-all, the delete approval email builder, and the cross-thread approval callback. All handlers follow the same pattern: authorize → parse → execute → reply.

**`config.py`** — Single source of truth for all configuration. The `validate()` method fails loudly at startup if required vars are missing — better to crash on boot than fail silently mid-operation.

**`services/agent.py`** — The AI brain. Receives the user's message and the current table list, sends it to Groq, and returns a structured action dict (`{action, table, match, data, text}`). This is where "show me pending orders" becomes `SELECT * FROM orders WHERE status='pending'`.

**`services/supabase_service.py`** — All database operations. Uses the Supabase Python SDK for standard CRUD and falls back to the `execute_sql` SQL helper function for raw queries.

**`services/approval_server.py`** — A minimal `http.server`-based HTTP server that listens for GET requests on `/approve?id=X&action=approve` and `/approve?id=X&action=cancel`. When triggered, calls back into the bot's async loop.

**`supabase_setup.sql`** — **Must be run before starting the bot.** Creates three PostgreSQL functions: `get_tables()`, `get_table_schema(table)`, and `execute_sql(query)`. These are called via Supabase's `rpc()` method.

---

## 🔑 Environment Variables

Create a `.env` file in the project root. All variables:

```env
# ── Telegram ──────────────────────────────────────────
TELEGRAM_BOT_TOKEN=your_bot_token_from_botfather

# ── Supabase ──────────────────────────────────────────
SUPABASE_URL=https://your-project-id.supabase.co
SUPABASE_SERVICE_ROLE_KEY=your_service_role_key  # NOT the anon key

# ── Groq AI ───────────────────────────────────────────
GROQ_API_KEY=gsk_your_groq_api_key

# ── Access Control ────────────────────────────────────
ALLOWED_USER_IDS=123456789,987654321  # Comma-separated Telegram user IDs
                                      # Leave empty for open access
MANAGER_TELEGRAM_ID=123456789         # Who receives realtime alerts

# ── SMTP Email ────────────────────────────────────────
SMTP_SERVER=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=yourbot@gmail.com
SMTP_PASSWORD=your_app_password       # Gmail: use App Passwords, not account password
SENDER_EMAIL=yourbot@gmail.com
MANAGER_EMAIL=manager@yourcompany.com

# ── Approval Server ───────────────────────────────────
APPROVAL_PORT=8080
APPROVAL_BASE_URL=http://localhost:8080  # Change to your public URL if deployed
```

> **Security note:** The `SUPABASE_SERVICE_ROLE_KEY` bypasses Row Level Security. Never expose it publicly. Never commit `.env` to Git.

> **Gmail App Passwords:** Go to Google Account → Security → 2-Step Verification → App Passwords. Generate one for "Mail". Use that 16-character code as `SMTP_PASSWORD`.

> **Finding your Telegram user ID:** Message [@userinfobot](https://t.me/userinfobot) on Telegram.

---

## ⚙️ Installation & Setup

### Prerequisites

- Python 3.10 or higher
- A [Supabase](https://supabase.com) account and project (free tier works)
- A Telegram bot token from [@BotFather](https://t.me/botfather)
- A [Groq](https://console.groq.com) API key (free tier available)
- Gmail (or any SMTP provider) for email notifications

### Step 1 — Clone the Repository

```bash
git clone https://github.com/your-username/supabase-telegram-agent.git
cd supabase-telegram-agent
```

### Step 2 — Create Virtual Environment

```bash
python3 -m venv venv

# macOS / Linux
source venv/bin/activate

# Windows
venv\Scripts\activate
```

### Step 3 — Install Dependencies

```bash
pip install -r requirements.txt
```

Dependencies explained:

```
python-telegram-bot==21.10   # Async Telegram bot framework (v21+ uses asyncio natively)
supabase==2.13.0             # Official Supabase Python SDK
groq==0.9.0                  # Groq API client for LLaMA inference
python-dotenv==1.1.0         # Loads .env file into environment
```

> **Why so few dependencies?** The project deliberately avoids heavy ML libraries. Intelligence comes from Groq's API, not local models. This keeps the install fast and memory footprint tiny.

### Step 4 — Configure Environment Variables

```bash
cp .env.example .env
# Edit .env with your actual credentials
```

### Step 5 — Set Up Supabase Database

1. Open your [Supabase Dashboard](https://supabase.com/dashboard)
2. Go to **SQL Editor**
3. Paste and run `supabase_setup.sql` — creates the 3 required helper functions
4. *(Optional)* Paste and run `mock_data.sql` — creates sample users/products/orders tables

### Step 6 — Test Email Configuration

```bash
python test_email.py
```

If successful, you'll see `✅ Email sent successfully!` and receive a test email. Fix any SMTP errors before proceeding.

---

## ▶️ Running the Agent

```bash
# Ensure virtual environment is active
source venv/bin/activate

python main.py
```

Expected startup output:

```
──────────────────────────────────────────
  🤖 Supabase Telegram Agent
──────────────────────────────────────────
  📡 Supabase: https://your-project.supabase.co
  🧠 AI Model: llama-3.3-70b-versatile
  🔒 Access: Restricted to 2 user(s)
──────────────────────────────────────────

  ✅ Bot is starting... (press Ctrl+C to stop)
```

Now open Telegram, find your bot, and send `/start`.

---

## 📋 Command Reference

| Command | Syntax | Example | What It Does |
|---|---|---|---|
| `/start` | `/start` | `/start` | Shows welcome message & command list |
| `/help` | `/help` | `/help` | Detailed usage guide |
| `/tables` | `/tables` | `/tables` | Lists all tables in the database |
| `/schema` | `/schema <table>` | `/schema orders` | Shows columns, types, constraints |
| `/query` | `/query <table>` | `/query products` | Returns first 20 rows |
| `/count` | `/count <table>` | `/count users` | Returns total row count |
| `/insert` | `/insert <table> key=value ...` | `/insert users name=John email=j@x.com` | Inserts a new row |
| `/update` | `/update <table> match \| data` | `/update users id=1 \| name=Jane` | Updates matching rows |
| `/delete` | `/delete <table> key=value` | `/delete orders id=5` | Triggers approval flow |
| `/sql` | `/sql <query>` | `/sql SELECT COUNT(*) FROM orders` | Executes raw SQL |
| `/report` | `/report` | `/report` | Generates AI manager report |

### Key=Value Parsing Rules

The `/insert` and `/update` commands use smart type inference:

```
name=John           → string  "John"
price=29.99         → float   29.99
stock=100           → int     100
is_active=true      → bool    True
deleted_at=null     → None    NULL
bio="Hello World"   → string  "Hello World"  (quotes for spaces)
```

---

## 💬 Natural Language Examples

The AI agent handles a wide range of natural language. Here are real examples:

```
📊 Read Operations
──────────────────────────────────────────────────────────────
"Show me all users"
"List products in the Electronics category"
"How many orders were placed this month?"
"Which orders are still pending?"
"Find the user with email alice@example.com"
"What's our best-selling category?"
"Show me orders over $100"

✏️ Write Operations
──────────────────────────────────────────────────────────────
"Add a new product called Widget Pro with price 49.99 in category Electronics"
"Update Bob's email to bob.new@example.com"
"Mark order 3 as completed"
"Set all Electronics products as inactive"

🗑️ Delete Operations (triggers approval email)
──────────────────────────────────────────────────────────────
"Delete the user with id 5"
"Remove cancelled orders"
"Delete product number 8"

📈 Analytical Questions
──────────────────────────────────────────────────────────────
"What's the total revenue from completed orders?"
"Which products are low in stock?"
"How many customers vs admins do we have?"
```

---

## 🔐 The Delete Approval Flow (Safety First)

This is the most architecturally interesting feature. Here's exactly what happens when you type `/delete users id=5`:

```
1. Bot queries the database for matching rows
   └─ "Here's what will be deleted: [preview of row(s)]"

2. A UUID (e.g. "a3f7b2c1") is generated for this request
   └─ Stored in approval_server.pending_deletes dict

3. Approval email sent to MANAGER_EMAIL containing:
   ├─ HTML table showing the matching rows
   ├─ [✅ Approve Delete] button → http://localhost:8080/approve?id=a3f7b2c1&action=approve
   └─ [❌ Cancel] button → http://localhost:8080/approve?id=a3f7b2c1&action=cancel

4. Bot replies: "📧 Approval buttons have been sent to your email!"

5. Manager opens email, reviews rows, clicks a button

6. approval_server.py receives the GET request:
   ├─ Looks up pending_deletes["a3f7b2c1"]
   ├─ Calls _handle_approval_from_server() callback
   └─ Uses asyncio.run_coroutine_threadsafe() to bridge into async event loop

7. If approved:
   ├─ db.delete_row() executes
   ├─ Email audit trail sent
   └─ Telegram: "🗑️ Deleted 1 row(s) from users (Approved via email)"

8. If cancelled:
   └─ Telegram: "🚫 Delete Cancelled — The request was rejected via email."
```

> **Why not just ask "are you sure?" in Telegram?** Because the person typing the delete *is* the person confirming it. Email routes the approval to a *different* person (the manager), creating a genuine two-person authorization system for destructive operations.

---

## 🧩 Challenges & Learnings

### 1. Bridging Async and Threaded Code
**Challenge:** The approval HTTP server runs in a `threading.Thread`, but all Telegram operations require `async/await` in the event loop. You can't simply call an async function from a thread.

**Solution:** Store references to `_bot_app` and `_main_loop` at startup, then use `asyncio.run_coroutine_threadsafe(coroutine, loop)` from the thread. This safely submits the coroutine to the running event loop from outside it.

**Learning:** In Python, async code and threaded code live in different worlds. `run_coroutine_threadsafe` is the correct bridge — not `asyncio.run()` (which creates a new loop) or `loop.call_soon()` (which doesn't handle coroutines).

### 2. Preventing AI Hallucination on Table Names
**Challenge:** If the AI doesn't know what tables exist, it might try to query `customers` when the actual table is `users`, causing database errors that confuse the user.

**Solution:** Before every AI call, `get_table_list_for_context()` fetches the real table names from the database and includes them in the system prompt. The AI can only reference tables that actually exist.

**Learning:** Grounding LLM prompts with real, current system state is the difference between a reliable agent and an unreliable one. RAG (Retrieval-Augmented Generation) applies not just to documents but to live system metadata.

### 3. Safe SQL Function Design in Supabase
**Challenge:** The `execute_sql` function runs arbitrary SQL — necessary for flexibility but dangerous if exposed incorrectly.

**Solution:** All three SQL helper functions use `SECURITY DEFINER` (runs as the function owner, not the caller) and are only accessible via `SUPABASE_SERVICE_ROLE_KEY`, which is never exposed to the frontend. The bot itself is the only caller.

**Learning:** Defense in depth — the key restriction isn't in the function itself but in who holds the credentials to call it.

### 4. Telegram's 4096 Character Limit
**Challenge:** SQL results can be long. Telegram silently truncates messages over 4096 characters, causing data loss.

**Solution:** `_send_long_message()` splits text at newline boundaries and sends multiple messages. It prefers splitting at `\n` (keeping rows intact) and only hard-splits at the character limit as a last resort.

**Learning:** Always handle the constraints of your output channel explicitly. "It'll probably fit" is not an engineering solution.

### 5. Smart Type Inference in Key=Value Parsing
**Challenge:** Everything from a chat message is a string. `/insert products price=29.99` needs `price` to be a float, not the string `"29.99"`, for the database to accept it.

**Solution:** `_parse_key_value_pairs()` tries `int()` then `float()` then checks for `"true"/"false"/"null"`, falling back to string if nothing else matches. It uses `shlex.split()` to handle quoted strings with spaces correctly.

**Learning:** User input parsing is deceptively complex. `shlex.split()` is a Python stdlib gem that handles quoted strings, escapes, and whitespace exactly like a Unix shell does.

---

## 🚀 Future Improvements

### Near-Term
- [ ] **Conversation memory** — Store the last N messages per user so follow-up questions like "now filter those by status=completed" work correctly
- [ ] **Multi-step transactions** — Let the AI plan multi-table operations and execute them atomically
- [ ] **Inline keyboard query builder** — Offer button menus for table selection instead of requiring typed table names
- [ ] **Rate limiting** — Prevent accidental or malicious flooding of the bot

### Medium-Term
- [ ] **Web-based approval UI** — Replace the local HTTP server with a small Flask/FastAPI app so approval links work when the bot is deployed to a server
- [ ] **Scheduled reports** — Cron-style daily/weekly summary reports pushed automatically to the manager
- [ ] **Data export** — `/export users` sends a CSV file directly in Telegram
- [ ] **Row-level edit UI** — Inline buttons after `/query` to edit or delete individual rows without typing commands
- [ ] **Support multiple databases** — MySQL, MongoDB, Firebase via a pluggable backend interface

### Long-Term
- [ ] **Docker deployment** — `docker-compose up` for one-command production deployment
- [ ] **Multi-tenant** — Each user has their own Supabase connection string
- [ ] **Web dashboard** — A Next.js companion app showing query history, change logs, and analytics
- [ ] **Voice queries** — Telegram voice messages → Whisper transcription → existing NLP pipeline

---

## 🎓 Learning Outcomes (For Students)

This project is a goldmine of real-world engineering patterns. By studying and extending it, you'll learn:

### Python & Async
- `asyncio` event loops, `async/await` syntax, and `run_coroutine_threadsafe`
- `python-telegram-bot` v21's fully async handler system
- Threading vs async — when to use which, and how to bridge them
- `shlex.split()` for robust string parsing
- `dotenv` and `os.getenv` for config management

### LLM / AI Engineering
- Prompt engineering: how to give an LLM system context that prevents hallucination
- Tool-calling patterns: LLM identifies *what* to do, Python code *does* it
- The difference between generative AI (creates) and agentic AI (acts)
- Groq API integration and LLaMA model capabilities

### Database & Backend
- Supabase Python SDK: CRUD, RPC function calls, realtime subscriptions
- PostgreSQL `SECURITY DEFINER` functions and why they matter
- Foreign key relationships and cascade deletes
- Safe dynamic SQL execution patterns

### System Design
- Multi-service architecture: bot + database + email + HTTP server all running together
- Two-person authorization for destructive operations (industry standard)
- Audit logging: every change creates a paper trail
- Graceful degradation: missing optional config (email) doesn't crash the bot

### Software Engineering Practices
- Environment variable management and secrets handling
- Config validation at startup (fail fast)
- Long message splitting for platform-specific constraints
- UUID-based pending request tracking

---

## ❓ FAQ

**Q: Can I use this with a different database? (MySQL, MongoDB, etc.)**
A: Currently Supabase/PostgreSQL only. Adding MySQL would require replacing `supabase_service.py` with a MySQL connector, but the bot layer (`bot.py`, `agent.py`) would stay the same.

**Q: What if someone gets my bot token and spams the bot?**
A: Set `ALLOWED_USER_IDS` in your `.env`. The bot will reject all messages from unauthorized users before doing any processing.

**Q: The approval link says "localhost" — it doesn't work from my phone!**
A: Set `APPROVAL_BASE_URL` to your server's public IP or use [ngrok](https://ngrok.com) to expose port 8080 temporarily. The local HTTP server is designed for development; production deployment needs a reachable URL.

**Q: Does this work with Supabase's free tier?**
A: Yes. The free tier includes 500MB database, unlimited API requests, and realtime — more than enough for development and small teams.

**Q: Why does the bot take a few seconds to respond to natural language?**
A: Groq inference takes 0.5–2 seconds, plus network round-trips. Slash commands (`/query`, `/count`) skip the AI and respond near-instantly.

**Q: Can I deploy this to a server so I don't need to keep my laptop on?**
A: Yes — any Linux VPS works. Run `python main.py` in a `screen` or `tmux` session, or configure it as a `systemd` service. Change `APPROVAL_BASE_URL` to your server's public IP.

---

## ⚠️ Common Mistakes Beginners Make

| Mistake | Consequence | Fix |
|---|---|---|
| Using `SUPABASE_ANON_KEY` instead of `SERVICE_ROLE_KEY` | RPC functions fail with permission errors | Use the service role key — it's in Supabase → Settings → API |
| Forgetting to run `supabase_setup.sql` | Bot crashes on every request ("function get_tables() does not exist") | Always run the SQL setup file first |
| Using Gmail account password instead of App Password | SMTP authentication fails | Enable 2FA on Gmail, then generate an App Password |
| Committing `.env` to GitHub | Credentials exposed publicly | Add `.env` to `.gitignore` immediately |
| Not setting `ALLOWED_USER_IDS` in production | Anyone who finds your bot can read/write your database | Always restrict access in production |
| Running `python main.py` without activating `venv` | Wrong Python/packages used | Always `source venv/bin/activate` first |
| Keeping `APPROVAL_BASE_URL=localhost` on a deployed server | Approval email links don't work | Set to your server's public IP or domain |

---

## 💡 Tips for Improving the Project

- **Add conversation context:** Store the last 3–5 messages per user in a dict and include them in the Groq prompt. This makes follow-up questions work naturally.
- **Log queries to Supabase:** Write every NLP query and its result back to a `bot_logs` table. Instant analytics on how the bot is being used.
- **Stream long responses:** `python-telegram-bot` supports `send_chat_action(ChatAction.TYPING)` — use it while waiting for Groq to show a "typing..." indicator.
- **Add `/undo`:** After any INSERT/UPDATE, store the previous state. A `/undo` command restores it — powerful safety net for accidental writes.
- **Input sanitization:** The current SQL helper uses string concatenation inside `execute_sql`. For production, add input validation or switch to parameterized queries via the Supabase SDK wherever possible.

---

## 👤 Author

**[Your Name]**
*Software Developer | AI & Systems Enthusiast*

This project was built to explore the intersection of conversational AI, real-time databases, and practical system design — going beyond tutorials to build something genuinely useful for day-to-day database management.

It demonstrates applied skills in async Python, LLM agent design, multi-service architecture, and security-conscious engineering (two-person delete authorization, audit trails, access control).

- 🔗 [LinkedIn](https://linkedin.com/in/your-profile)
- 💻 [GitHub](https://github.com/your-username)
- 📧 [your.email@example.com](mailto:your.email@example.com)
- 🌐 [Portfolio](https://your-portfolio.com)

---

## 📄 License

MIT License — see [LICENSE](LICENSE) for details.

---

<div align="center">

Built with 🤖 Groq LLaMA · 📦 Supabase · 📱 Telegram · 🐍 Python asyncio

*Query your database from anywhere. Approve deletes from your inbox. Sleep soundly.*

**[Report a Bug](https://github.com/your-username/supabase-telegram-agent/issues) · [Request a Feature](https://github.com/your-username/supabase-telegram-agent/issues)**

</div>
