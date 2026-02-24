# TECH_STACK.md — Gold Tier Technology Stack

---

## Core Runtime

| Tool | Version | Purpose | Install |
|---|---|---|---|
| Python | 3.13+ | All watchers, orchestrator, social posters | UV managed |
| UV | Latest | Python package manager (replaces pip/venv) | `pip install uv` |
| Node.js | v24+ LTS | MCP servers, WhatsApp watcher | nodejs.org |
| npm | Bundled with Node | Node package management | — |
| PM2 | Latest | Process manager, keeps watchers alive | `npm install -g pm2` |

---

## Silver (Already Installed — Do Not Change)

```
# From Silver requirements.txt — already installed
google-auth
google-auth-oauthlib
google-api-python-client
playwright          ← ALSO used for Facebook, Instagram, Twitter in Gold
watchdog
python-dotenv
sqlite3 (stdlib)
pytest
pytest-cov
whatsapp-web.js (Node)
```

---

## Social Media Approach — ALL Playwright

All 4 social platforms use Playwright browser automation. No social APIs, no SDK, no OAuth flows.

| Platform | Method | Session Storage | Silver Equivalent |
|---|---|---|---|
| LinkedIn | Playwright | `.linkedin_session/` | ✅ Already in Silver |
| WhatsApp | Playwright (Node.js) | `.wwebjs_auth/` | ✅ Already in Silver |
| Facebook | Playwright | `.facebook_session/` | NEW — same pattern |
| Instagram | Playwright | `.instagram_session/` | NEW — same pattern |
| Twitter/X | Playwright | `.twitter_session/` | NEW — same pattern |

**Why Playwright over API**: No app review, no OAuth complexity, no API credentials to manage. Works immediately with just email/password. Same pattern already proven in Silver for WhatsApp and LinkedIn.

---

## Gold — New Python Dependencies

Add to `pyproject.toml`:

```toml
[project]
dependencies = [
    # Playwright already installed in Silver — no reinstall needed
    "python-dotenv>=1.0.0",

    # Odoo
    # xmlrpc.client is stdlib — no install needed

    # Testing (Gold)
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "pytest-mock>=3.12.0",
    "freezegun>=1.4.0",

    # Utilities
    "pyyaml>=6.0.0",
    "schedule>=1.2.0",
]
```

Install: `uv sync`

---

## Gold — New Node.js Dependencies (Odoo MCP)

```json
{
  "dependencies": {
    "@modelcontextprotocol/sdk": "^1.0.0",
    "axios": "^1.6.0",
    "dotenv": "^16.0.0"
  }
}
```

Install: `cd mcp_servers/odoo_mcp && npm install`

---

## MCP Servers

| Server | Type | Install | Purpose |
|---|---|---|---|
| `odoo` | Custom (Node.js) | `node mcp_servers/odoo_mcp/index.js` | Odoo JSON-RPC — invoices, expenses, balances |
| `browser` | Built-in (npx) | `npx -y @anthropic-ai/browser-mcp` | Payment portal interactions, web automation |

**Why only two**: Filesystem handled by Python file I/O. Fetch not needed — CEO briefing pulls from Odoo + SQLite. GitHub auto-commit not a Gold requirement.

**Gmail MCP**: NOT used. Direct Gmail API already works in Silver. Keep it.

---

## External APIs

### Already Configured (Silver)
| API | Auth Method | Used For |
|---|---|---|
| Gmail API v1 | OAuth 2.0 | Read emails, direct send |

### New for Gold
| API | Auth Method | Used For | Docs |
|---|---|---|---|
| Odoo JSON-RPC | Email + Password | Accounting integration | odoo.com/documentation/19.0/developer/reference/external_api.html |

---

## Infrastructure

### Odoo Community
| Property | Value |
|---|---|
| Version | 19 Community |
| Install method | Docker |
| URL | `http://localhost:8069` |
| Database name | `ai_employee` |
| Docker image | `odoo:19` |
| PostgreSQL | `postgres:15` (separate container) |
| Network | `odoo-network` (Docker bridge) |

```powershell
# Already running — do not re-run
docker ps --filter name=odoo-ai-employee
```

### Process Management (PM2)
```powershell
pm2 start src/watchers/gmail_watcher.py --interpreter python3 --name gmail-watcher
pm2 start src/watchers/filesystem_watcher.py --interpreter python3 --name file-watcher
pm2 start src/watchers/linkedin_watcher.py --interpreter python3 --name linkedin-watcher
pm2 start src/watchers/whatsapp/whatsapp_watcher.js --name whatsapp-watcher
pm2 start src/orchestrator/orchestrator.py --interpreter python3 --name orchestrator
pm2 save
pm2 startup
```

### Windows Task Scheduler Tasks
| Task | Trigger | Script |
|---|---|---|
| `AIEmployee_Orchestrator` | On login | `pm2 resurrect` |
| `AIEmployee_MorningBriefing` | Monday 7:00 AM | `orchestrator.py --task briefing` |
| `AIEmployee_SocialPost` | Friday 10:00 AM | `orchestrator.py --task social` |
| `AIEmployee_WeeklyAudit` | Sunday 11:00 PM | `orchestrator.py --task audit` |
| `AIEmployee_WatcherHealth` | Every 30 min | `pm2 resurrect` |

Setup: `powershell -ExecutionPolicy Bypass -File scripts\setup_task_scheduler.ps1`

---

## Folder Structure (Gold additions only)

```
AI-EMPLOYEE-GOLD\
├── CLAUDE.md
├── .env
├── docs\                              ← Gold + Silver docs
│   ├── TECH_STACK.md
│   ├── FEATURES.md
│   ├── CHECKLIST.md
│   ├── INITIAL_PROMPT.md
│   ├── project_info\                  ← Silver existing
│   └── platforms\                     ← Silver existing
│
├── src\
│   ├── [Silver watchers]              ← DO NOT TOUCH
│   ├── [Silver workflows]             ← DO NOT TOUCH
│   ├── orchestrator\                  ← NEW
│   │   └── orchestrator.py
│   ├── social\                        ← NEW (all Playwright)
│   │   ├── facebook_poster.py
│   │   ├── instagram_poster.py
│   │   └── twitter_poster.py
│   └── ralph_wiggum\                  ← NEW
│       └── stop_hook.py
│
├── mcp_servers\                       ← NEW
│   └── odoo_mcp\
│       ├── index.js
│       └── package.json
│
├── AI_Employee_Vault\
│   ├── .claude\skills\                ← Add new Gold skills here
│   │   ├── [12 Silver skills]         ← DO NOT TOUCH
│   │   ├── odoo-integration\          ← NEW
│   │   ├── social-media-manager\      ← NEW
│   │   ├── ceo-briefing\              ← NEW
│   │   └── ralph-wiggum\             ← NEW
│   ├── In_Progress\                   ← NEW
│   ├── Logs\                          ← NEW JSON logs
│   └── Briefings\                     ← NEW CEO briefings
│
├── tests\
│   ├── [Silver tests]                 ← DO NOT BREAK
│   └── gold\                          ← NEW
│       ├── unit\
│       ├── integration\
│       └── e2e\
│
└── scripts\
    ├── [Silver .sh scripts]           ← Keep
    ├── start_all_watchers.ps1         ← NEW
    ├── stop_all_watchers.ps1          ← NEW
    ├── check_watchers.ps1             ← NEW
    └── setup_task_scheduler.ps1      ← NEW
```

---

## Environment Variables

Silver `.env` already has these:
```
GMAIL_CREDENTIALS_PATH=credentials.json
GMAIL_TOKEN_PATH=token.json
DATABASE_PATH=AI_Employee_Vault/Database/ai_employee.db
APPROVAL_THRESHOLD=1000
MONTHLY_BUDGET=5000
```

Gold additions (already in your .env):
```
# Odoo
ODOO_URL=http://localhost:8069
ODOO_DB=ai_employee
ODOO_USERNAME=falihaarain48@gmail.com
ODOO_PASSWORD=<set>

# Playwright Social Sessions
FACEBOOK_EMAIL=<set>
FACEBOOK_PASSWORD=<set>
INSTAGRAM_USERNAME=<set>
INSTAGRAM_PASSWORD=<set>
TWITTER_EMAIL=<set>
TWITTER_PASSWORD=<set>

# Gold system settings
DRY_RUN=true
ORCHESTRATOR_INTERVAL_SECONDS=30
RALPH_MAX_ITERATIONS=10
LOG_RETENTION_DAYS=90
VAULT_PATH=C:\Users\tayyaba\Desktop\PIAIC\AI\AI-EMPLOYEE-GOLD
```