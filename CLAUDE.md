# AI Employee — Gold Tier

## What This Project Is
Autonomous AI employee that monitors Gmail, WhatsApp, LinkedIn, filesystem → reasons → acts.
Built on a complete Silver Tier. Gold adds: Orchestrator, Ralph Wiggum loop, Odoo accounting, Facebook/Instagram/Twitter, CEO briefing, full TDD.

Silver is at `src/`. Vault is at `AI_Employee_Vault/`. Skills at `AI_Employee_Vault/.claude/skills/`.

For full specs see:
- Tech stack, APIs, env vars → see @docs/TECH_STACK.md
- What to build and in what order → see @docs/FEATURES.md
- TDD rules, test types, definition of done → see @docs/CHECKLIST.md
- Starting prompt → see @docs/INITIAL_PROMPT.md

---

## Step 0 — Silver Audit (Always First)

Before any Gold code: audit every Silver component end-to-end. Run it, don't just check if it exists.

If anything is broken → write `AI_Employee_Vault/Needs_Action/SILVER_AUDIT_REPORT.md` → STOP → tell the human → wait for explicit go-ahead. Never self-fix.

Expected baseline: `pytest tests/ -v` → 423/427 pass. The 4 LinkedIn failures are credential-only — do not flag them as broken.

---

## Common Commands

```powershell
# Run Silver tests (do this before and after every change)
pytest tests/ -v

# Run Gold tests
pytest tests/gold/ -v --cov=src --cov-fail-under=100

# Start all watchers
pm2 start src/watchers/gmail_watcher.py --interpreter python3 --name gmail-watcher
pm2 start src/watchers/whatsapp/whatsapp_watcher.js --name whatsapp-watcher
pm2 start src/watchers/linkedin_watcher.py --interpreter python3 --name linkedin-watcher
pm2 start src/watchers/filesystem_watcher.py --interpreter python3 --name file-watcher
pm2 start src/orchestrator/orchestrator.py --interpreter python3 --name orchestrator

# Install deps
uv sync
cd mcp_servers/odoo_mcp && npm install

# Orchestrator modes
uv run python src/orchestrator/orchestrator.py --dry-run
uv run python src/orchestrator/orchestrator.py --task briefing
uv run python src/orchestrator/orchestrator.py --task audit

# Task Scheduler setup
powershell -ExecutionPolicy Bypass -File scripts\setup_task_scheduler.ps1
```

---

## Code Style

- Python 3.13+, UV only — never `pip install` directly
- All paths via `Path.home()` or `os.environ['USERPROFILE']` — never hardcode username
- Every external call wrapped in `@with_retry(max_attempts=3, base_delay=1)`
- `DRY_RUN=false` — real execution always. Follow safe testing rules in docs/CHECKLIST.md
- New Gold files go in: `src/orchestrator/`, `src/social/`, `src/ralph_wiggum/`, `mcp_servers/odoo_mcp/`
- New skills go in: `AI_Employee_Vault/.claude/skills/<skill-name>/SKILL.md`
- Every action logged to both SQLite (`ai_employee.db`) AND `AI_Employee_Vault/Logs/YYYY-MM-DD.json`

---

## Workflow Rules

**TDD is mandatory — no exceptions:**
1. Write SKILL.md first
2. Write failing tests (RED) → commit
3. Write minimum implementation (GREEN) → commit
4. Refactor → commit
5. 100% coverage on all Gold code. Silver must stay at 423/427.

**Task lifecycle — always follow this:**
`Needs_Action` → claim to `In_Progress` → Claude + skill → Plan.md → approval if needed → MCP executes → `Done` → log → Dashboard update

**Approval gate — non-negotiable:**
Send email, post to any social platform, create Odoo invoice, post journal entry, delete file, any payment → ALWAYS write approval file first, NEVER execute directly.

---

## Things Claude Gets Wrong (Anti-Patterns)

- **Rebuilding Silver** — Gmail watcher, 12 skills, SQLite, 7 workflows, approval CLI are DONE. Check `src/` before building anything.
- **Using APIs for social media** — Facebook, Instagram, Twitter ALL use Playwright browser automation. Same pattern as WhatsApp and LinkedIn in Silver. Never use Graph API, tweepy, or any social SDK.
- **Skipping tests** — never write implementation before tests. If you catch yourself doing this, stop and write tests first.
- **Hardcoding paths** — `C:\Users\tayyaba\...` will break. Always use `Path.home()`.
- **Direct execution without approval** — social posts, emails, Odoo writes need approval files first. No exceptions, no matter how small.
- **Crashing on API failure** — each service must fail independently. Gmail down ≠ WhatsApp down. Write `SYSTEM_ALERT_*.md` and continue.
- **Fixing Silver without permission** — if Silver is broken, report it and stop. Do not fix.
- **Using pip** — always `uv add <package>` and `uv sync`. Never `pip install`.
- **Missing the Ralph Wiggum exit check** — the stop hook checks `/Done/`, not just "did Claude finish". Max 10 iterations then FAILED alert.
- **Building Twitter with tweepy** — Twitter uses Playwright, not API. Credentials are TWITTER_EMAIL + TWITTER_PASSWORD in .env.