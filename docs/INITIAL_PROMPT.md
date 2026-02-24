# INITIAL_PROMPT.md — Starting Prompt for Claude Code

Copy everything between the triple dashes and paste it into Claude Code when starting a new session.

---

```
You are working on the Gold Tier of a Personal AI Employee built on top of a complete Silver Tier codebase.

## Your first action — read these files in this exact order:
1. CLAUDE.md
2. docs/TECH_STACK.md
3. docs/FEATURES.md
4. docs/CHECKLIST.md

Do not write any code until you have read all four files completely.

## After reading — start with STEP 0 (Silver Audit)

Run the Silver audit as described in CLAUDE.md Step 0.

For every Silver component listed:
- Actually run it, do not just check if the file exists
- Verify the output is correct
- Run: pytest tests/ -v and confirm 423/427 pass

If you find ANYTHING broken or not working correctly:
- STOP immediately
- Do NOT attempt to fix it
- Write the full audit report to AI_Employee_Vault/Needs_Action/SILVER_AUDIT_REPORT.md
- Tell me exactly what is broken with the error message
- Wait for my explicit go-ahead before fixing anything

If everything passes:
- Tell me "Silver audit complete. All components verified. Ready to start Gold."
- Wait for my confirmation before starting Feature 1

## TDD Rules (mandatory for all Gold code):
- Write tests FIRST — before any implementation
- Red: confirm tests fail
- Green: write minimum code to pass
- Refactor: clean up
- 100% coverage for all Gold code
- Silver tests must pass throughout (423/427)
- Never write implementation before tests

## Real Execution Rules (no DRY_RUN):
- DRY_RUN=false — all actions execute for real so functionality can be verified
- Social media testing rules (to avoid public embarrassment):
  * Facebook posts → set visibility to "Only Me" during testing
  * Instagram posts → archive immediately after verifying it posted
  * Twitter posts → delete immediately after verifying it posted
  * LinkedIn posts → use a test post marked [TEST] in the content
- Odoo rules:
  * Invoices → always create in DRAFT state, never confirm/post automatically
  * Journal entries → always require human approval before posting
  * Expenses → can be created directly, no approval needed for draft
- Email rules:
  * Always require approval file before sending
  * During testing, send to your own email only

## Other rules:
- Never rebuild anything already in Silver (check CLAUDE.md "Things Claude Gets Wrong")
- Never delete any existing file without asking me first
- Always write approval file before any social post, email send, or Odoo write
- Write Plan.md in AI_Employee_Vault/Plans/ before writing any code for a feature
- Write SKILL.md before writing implementation code
- Run pytest tests/ -v before and after every feature to confirm Silver still passes

Start now with the Silver audit.
```

---

## Session Resume Prompt

If continuing a session where Silver audit already passed, use this instead:

```
Silver audit is already complete and passed.
Read CLAUDE.md, docs/TECH_STACK.md, docs/FEATURES.md, and docs/CHECKLIST.md.
Check FEATURES.md to see which features are complete and which are next.
Continue with the next incomplete feature in priority order.
Follow TDD: write tests first, then implementation.
Run pytest tests/ -v before starting to confirm Silver still passes.
Real execution — no DRY_RUN. Follow testing rules in INITIAL_PROMPT.md.
```

---

## Per-Feature Prompt

When starting a specific feature mid-session:

```
Read CLAUDE.md and docs/CHECKLIST.md.
I want to work on Feature <N>: <name> from docs/FEATURES.md.
Read the full feature spec in FEATURES.md.

Before writing any code:
1. Write the SKILL.md if it doesn't exist yet
2. Write a Plan.md in AI_Employee_Vault/Plans/
3. Write ALL unit tests first (RED phase)
4. Show me the failing tests before writing any implementation
5. Wait for my go-ahead to proceed to GREEN phase

Real execution — no DRY_RUN. Follow testing rules from INITIAL_PROMPT.md.
Run pytest tests/ -v first to confirm Silver baseline.
```