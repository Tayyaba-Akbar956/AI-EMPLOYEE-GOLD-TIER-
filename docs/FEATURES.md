# FEATURES.md — Gold Tier Features (Priority Order)

> Work through this list strictly in order.
> Complete + test each feature before starting the next.
> TDD is mandatory — see CHECKLIST.md before implementing anything.

---

## FEATURE 0 — Silver Audit (Before anything else)

**What**: Verify every Silver component works end-to-end.
**Output**: `/Needs_Action/SILVER_AUDIT_REPORT.md`
**Rule**: If anything is broken → STOP → report → wait for human go-ahead.
**Full instructions**: See CLAUDE.md Step 0.

---

## FEATURE 1 — Orchestrator

**Location**: `src/orchestrator/orchestrator.py`
**Skill**: `.claude/skills/planning_skill/SKILL.md` (Silver, existing)
**Tests**: `tests/gold/unit/test_orchestrator.py`, `tests/gold/integration/test_orchestrator_integration.py`

**What it does**:
- Polls `/Needs_Action/` every 30 seconds
- Claims tasks via claim-by-move to `/In_Progress/`
- Detects task type from frontmatter `type:` field
- Loads matching SKILL.md, triggers Claude Code with it
- Watches `/Approved/` → executes approved MCP actions
- Watches `/Rejected/` → logs and moves to `/Done/`
- Appends every action to `/Logs/YYYY-MM-DD.json` AND Silver SQLite
- Updates `Dashboard.md` after every cycle
- On startup: recovers stale `/In_Progress/` files older than 1 hour
- Integrates Silver's 7 workflows as sub-processes — does not replace them

**How to run**:
```powershell
uv run python src/orchestrator/orchestrator.py
uv run python src/orchestrator/orchestrator.py --verbose
uv run python src/orchestrator/orchestrator.py --dry-run
uv run python src/orchestrator/orchestrator.py --task briefing
uv run python src/orchestrator/orchestrator.py --task audit
uv run python src/orchestrator/orchestrator.py --task social
```

**Keep alive**:
```powershell
pm2 start src/orchestrator/orchestrator.py --interpreter python3 --name orchestrator
```

**TDD sequence**:
1. Write `test_orchestrator.py` — test claim-by-move, task detection, lifecycle
2. Red: all tests fail
3. Implement orchestrator.py
4. Green: all tests pass
5. Refactor: clean up, add logging
6. Write integration tests: full task cycle end-to-end

---

## FEATURE 2 — Ralph Wiggum Stop Hook

**Location**: `src/ralph_wiggum/stop_hook.py`
**Skill**: `.claude/skills/ralph-wiggum/SKILL.md` (NEW — write this first)
**Tests**: `tests/gold/unit/test_ralph_wiggum.py`

**What it does**:
- Intercepts Claude Code's exit signal
- Checks if current task file is in `/Done/`
- If NOT in `/Done/` → blocks exit, re-injects original prompt with previous output context
- If in `/Done/` → allows exit
- Tracks iteration count — stops at `RALPH_MAX_ITERATIONS` (default: 10)
- On max iterations: moves task to `/Needs_Action/FAILED_<task>.md`, writes `SYSTEM_ALERT_*.md`

**State file** (Orchestrator creates this):
```json
{
  "task_id": "TASK_abc123",
  "original_prompt": "...",
  "task_file": "/In_Progress/EMAIL_xyz.md",
  "done_file": "/Done/EMAIL_xyz.md",
  "iteration": 1,
  "max_iterations": 10,
  "started": "2026-01-07T10:00:00Z"
}
```

**TDD sequence**:
1. Write SKILL.md first
2. Write unit tests for stop hook logic
3. Red → Implement → Green → Refactor

---

## FEATURE 3 — Odoo Community + MCP Server

**Part A — Odoo Setup**:
- Docker install on Windows (see TECH_STACK.md)
- Database: `ai_employee`
- Modules needed: Accounting, Invoicing

**Part B — Odoo MCP Server**:
**Location**: `mcp_servers/odoo_mcp/index.js`
**Skill**: `.claude/skills/odoo-integration/SKILL.md` (NEW — write this first)
**Tests**: `tests/gold/unit/test_odoo_mcp.py`, `tests/gold/integration/test_odoo_integration.py`

**Tools to expose**:
| Tool | Description | Approval Required |
|---|---|---|
| `get_invoices` | List invoices by date/status | No |
| `get_expenses` | List expenses by category/date | No |
| `get_account_balance` | Current balance from chart of accounts | No |
| `get_overdue_invoices` | List overdue invoices | No |
| `create_invoice` | Create customer invoice | YES — always |
| `create_expense` | Log business expense | No |
| `post_journal_entry` | Post accounting entry | YES — always |

**Protocol**: Odoo JSON-RPC 2.0 at `http://localhost:8069/jsonrpc`

**How to run**:
```powershell
cd mcp_servers/odoo_mcp && npm install
node mcp_servers/odoo_mcp/index.js
node mcp_servers/odoo_mcp/index.js --test   # test connection only
```

**Register in MCP config** (`C:\Users\%USERNAME%\.claude\claude_code_config.json`):
```json
{
  "mcpServers": {
    "filesystem": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-filesystem",
               "C:\\Users\\%USERNAME%\\AI_Employee_Vault"]
    },
    "fetch": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-fetch"]
    },
    "github": {
      "command": "npx",
      "args": ["-y", "@modelcontextprotocol/server-github"],
      "env": { "GITHUB_PERSONAL_ACCESS_TOKEN": "${GITHUB_TOKEN}" }
    },
    "odoo": {
      "command": "node",
      "args": ["C:\\Users\\%USERNAME%\\AI_Employee_Vault\\mcp_servers\\odoo_mcp\\index.js"],
      "env": {
        "ODOO_URL": "http://localhost:8069",
        "ODOO_DB": "ai_employee",
        "ODOO_USERNAME": "${ODOO_USERNAME}",
        "ODOO_PASSWORD": "${ODOO_PASSWORD}",
        "DRY_RUN": "false"
      }
    }
  }
}
```

**TDD sequence**:
1. Write SKILL.md first
2. Write unit tests with mocked Odoo JSON-RPC responses
3. Red → Implement → Green → Refactor
4. Write integration tests against real local Odoo instance

---

## FEATURE 4 — Browser MCP Setup (Quick win)

**No code to write.** Just add to MCP config and verify it works.

**Location**: `C:\Users\%USERNAME%\.claude\claude_code_config.json`

```json
{
  "mcpServers": {
    "odoo": {
      "command": "node",
      "args": ["C:\\Users\\%USERNAME%\\AI_Employee_Vault_Gold\\mcp_servers\\odoo_mcp\\index.js"],
      "env": {
        "ODOO_URL": "http://localhost:8069",
        "ODOO_DB": "ai_employee",
        "ODOO_USERNAME": "${ODOO_USERNAME}",
        "ODOO_PASSWORD": "${ODOO_PASSWORD}",
        "DRY_RUN": "false"
      }
    },
    "browser": {
      "command": "npx",
      "args": ["-y", "@anthropic-ai/browser-mcp"],
      "env": {
        "HEADLESS": "true"
      }
    }
  }
}
```

**Why only these two:**
- Filesystem → already handled by Python file I/O in Silver. No MCP needed.
- Fetch → no web research feature in Gold scope. Remove.
- GitHub → not a Gold requirement. Remove.
- Browser MCP → needed for payment portal interactions (explicitly in Gold spec)
- Odoo MCP → core Gold requirement

**Verify Browser MCP works:**
```powershell
npx -y @anthropic-ai/browser-mcp --version
```

**Tests**: `tests/gold/integration/test_browser_mcp.py`
- Verify browser MCP can navigate to a test URL
- Verify headless mode works on Windows

---

## FEATURE 5 — Facebook + Instagram Integration

**Location**: `src/social/facebook_poster.py`, `src/social/instagram_poster.py`
**Skill**: `AI_Employee_Vault/.claude/skills/social-media-manager/SKILL.md` (NEW — write this first, covers all 3 platforms)
**Tests**: `tests/gold/unit/test_facebook_poster.py`, `tests/gold/unit/test_instagram_poster.py`
**Method**: Playwright browser automation — same pattern as WhatsApp and LinkedIn in Silver

**Facebook**:
- Auth: Playwright logs in with FACEBOOK_EMAIL + FACEBOOK_PASSWORD from .env
- Session: saved to `.facebook_session/` — same pattern as `.linkedin_session/` in Silver
- Actions: navigate to page → compose post → submit
- Always requires approval before posting

**Instagram**:
- Auth: Playwright logs in with INSTAGRAM_USERNAME + INSTAGRAM_PASSWORD from .env
- Session: saved to `.instagram_session/`
- Actions: navigate to create post → upload image or text → submit
- Always requires approval before posting

**DO NOT use**: Facebook Graph API, Instagram Graph API, any Meta SDK, requests for social posting

**Approval file pattern** (same as Silver LinkedIn):
```
AI_Employee_Vault/Pending_Approval/SOCIAL_FB_<YYYY-MM-DD-HHmm>.md
AI_Employee_Vault/Pending_Approval/SOCIAL_IG_<YYYY-MM-DD-HHmm>.md
```

**How to run**:
```powershell
DRY_RUN=true uv run python src/social/facebook_poster.py --test
DRY_RUN=true uv run python src/social/instagram_poster.py --test
```

**TDD sequence**:
1. Study Silver's LinkedIn Playwright implementation in `src/watchers/linkedin_watcher.py` — use same pattern
2. Write SKILL.md first (covers Facebook + Instagram + Twitter together)
3. Write unit tests with mocked Playwright browser (`pytest-mock`)
4. Red → Implement → Green → Refactor
5. Write E2E test: full flow from Orchestrator trigger → draft → approval file created → approved → posted → logged

---

## FEATURE 6 — Twitter/X Integration

**Location**: `src/social/twitter_poster.py`
**Skill**: `AI_Employee_Vault/.claude/skills/social-media-manager/SKILL.md` (same skill as Feature 5)
**Tests**: `tests/gold/unit/test_twitter_poster.py`
**Method**: Playwright browser automation — same pattern as Facebook and Instagram

**What it does**:
- Auth: Playwright logs in with TWITTER_EMAIL + TWITTER_PASSWORD from .env
- Session: saved to `.twitter_session/`
- Post tweets via browser automation (twitter.com/compose/tweet)
- Enforce 280 char limit — Claude must truncate or split before posting
- Weekly summary: tweets posted this week
- Always requires approval before posting

**DO NOT use**: tweepy, Twitter API v2, any Twitter SDK

**Approval file**:
```
AI_Employee_Vault/Pending_Approval/SOCIAL_TW_<YYYY-MM-DD-HHmm>.md
```

**How to run**:
```powershell
DRY_RUN=true uv run python src/social/twitter_poster.py --test
```

**TDD sequence**:
1. Study Silver's LinkedIn/WhatsApp Playwright pattern — replicate for Twitter
2. Write unit tests mocking Playwright browser (`pytest-mock`)
3. Red → Implement → Green → Refactor

---

## FEATURE 7 — Windows PowerShell Scripts

**Location**: `scripts/`
**Tests**: Manual verification (no unit tests for PS1 scripts)

| Script | What it does |
|---|---|
| `start_all_watchers.ps1` | PM2 start all 5 processes |
| `stop_all_watchers.ps1` | PM2 stop all |
| `check_watchers.ps1` | PM2 status + health summary |
| `setup_task_scheduler.ps1` | Register all 5 Task Scheduler tasks |

**How to run**:
```powershell
powershell -ExecutionPolicy Bypass -File scripts\start_all_watchers.ps1
powershell -ExecutionPolicy Bypass -File scripts\setup_task_scheduler.ps1

# Verify tasks registered
Get-ScheduledTask | Where-Object {$_.TaskName -like "AIEmployee_*"}
```

---

## FEATURE 8 — CEO Briefing Upgrade

**Location**: Extends Silver `report-generator` skill
**New Skill**: `.claude/skills/ceo-briefing/SKILL.md` (NEW)
**Output**: `/Briefings/YYYY-MM-DD_Monday_Briefing.md`
**Trigger**: Monday 7:00 AM via Task Scheduler
**Tests**: `tests/gold/integration/test_ceo_briefing.py`

**Upgrades over Silver**:
- Pulls real invoice data from Odoo (`get_invoices`, `get_overdue_invoices`)
- Pulls real expense data from Odoo (`get_expenses`)
- Pulls account balance from Odoo (`get_account_balance`)
- Adds social media summary (all 4 platforms: LinkedIn + Facebook + Instagram + Twitter)
- Adds subscription waste detection
- Pre-creates approval files for any proactive suggestions
- If Odoo is down: uses SQLite data with `[WARNING: Odoo unavailable — data may be stale]`

**Briefing structure**:
```markdown
# Monday Morning CEO Briefing — <date>

## Executive Summary
## Revenue (from Odoo)
## Expenses (from Odoo)
## Outstanding Invoices (from Odoo)
## Task Completion This Week
## Social Media Activity
## Bottlenecks
## Proactive Suggestions (with pre-created approval files)
## Upcoming Deadlines
```

---

## FEATURE 9 — Error Recovery + Graceful Degradation

**Location**: Add to every watcher, orchestrator, and social poster
**Tests**: `tests/gold/unit/test_error_recovery.py`

**What to add to every external API call**:
```python
@with_retry(max_attempts=3, base_delay=1, max_delay=4)
def call_external_api():
    ...
```

**SYSTEM_ALERT file format**:
```markdown
---
type: system_alert
service: gmail | whatsapp | linkedin | facebook | instagram | twitter | odoo
error: <error message>
timestamp: <ISO 8601>
action_required: true
---

## Alert
<service> is unavailable. Error: <message>
Other services continue running normally.

## What to do
Check <service> credentials and connectivity.
```

---

## FEATURE 10 — JSON Audit Logging

**Location**: Add to Orchestrator and all action handlers
**Tests**: `tests/gold/unit/test_audit_logging.py`

Every action appends to `/Logs/YYYY-MM-DD.json`:
```json
{
  "timestamp": "2026-01-07T10:30:00Z",
  "action_type": "email_send | linkedin_post | facebook_post | instagram_post | twitter_post | odoo_invoice | approval_created | task_completed | error | system_alert",
  "actor": "orchestrator | watcher | skill",
  "target": "recipient or platform",
  "parameters": {},
  "approval_status": "approved | auto | pending | rejected",
  "approved_by": "human | system",
  "result": "success | failure | dry_run",
  "error": null
}
```

Retain minimum 90 days. Never auto-delete log files.