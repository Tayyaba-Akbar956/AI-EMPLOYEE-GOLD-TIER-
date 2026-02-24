# CHECKLIST.md — Pre-Task Checklist + TDD Rules

> Follow this EVERY time before writing code.
> No exceptions. No skipping steps.

---

## PRE-TASK CHECKLIST

Before writing a single line of code:

- [ ] Read `CLAUDE.md` completely
- [ ] Read `TECH_STACK.md` completely
- [ ] Read `FEATURES.md` — identify which feature you are working on
- [ ] Read the matching `SKILL.md` for this feature (if it doesn't exist, write it first)
- [ ] Check Silver components that might be affected — will your change break anything?
- [ ] Confirm the feature is NOT already built in Silver (check `src/` and `AI_Employee_Vault/.claude/skills/`)
- [ ] Write a `Plan.md` in `/Plans/PLAN_<feature>_<YYYY-MM-DD>.md` before any code
- [ ] Set `DRY_RUN=true` in `.env` until explicitly told otherwise
- [ ] Confirm all Silver tests still pass: `pytest tests/ -v` (expect 423/427)

---

## SAFE REAL EXECUTION RULES

`DRY_RUN=false` always. But follow these rules to avoid accidents during testing:

| Platform | Safe Testing Rule |
|---|---|
| Facebook | Set post visibility to **"Only Me"** |
| Instagram | **Archive** post immediately after verifying it posted |
| Twitter/X | **Delete** tweet immediately after verifying it posted |
| LinkedIn | Add **[TEST]** prefix to post content |
| Email | Send to **your own email only** during testing |
| Odoo Invoice | Always create in **DRAFT** state — never confirm |
| Odoo Journal Entry | Always requires **human approval** file before posting |
| File deletion | Always requires **human approval** — never auto-delete |

---

## TEST-DRIVEN DEVELOPMENT — MANDATORY

Every Gold feature follows Red → Green → Refactor. No exceptions.

### The Rule
**Tests are written BEFORE implementation code.**
If you find yourself writing implementation before tests, stop immediately and write the tests first.

### Red → Green → Refactor Cycle

**RED phase** — Write failing tests first:
1. Write all unit tests for the feature
2. Run them: `pytest tests/gold/ -v`
3. Confirm they ALL fail (if any pass, your test is wrong — fix it)
4. Commit: `git commit -m "test: RED - <feature name> tests written"`

**GREEN phase** — Write minimum code to pass:
1. Write ONLY enough implementation code to make the tests pass
2. Do not over-engineer. Do not add features not tested.
3. Run: `pytest tests/gold/ -v`
4. Confirm ALL tests pass
5. Run Silver tests too: `pytest tests/ -v` — confirm 423/427 still pass
6. Commit: `git commit -m "feat: GREEN - <feature name> implemented"`

**REFACTOR phase** — Clean up:
1. Clean code: remove duplication, improve naming, add docstrings
2. Run tests again: `pytest tests/ -v` — must still pass
3. Add any missing edge case tests discovered during refactor
4. Commit: `git commit -m "refactor: <feature name> cleaned up"`

---

## TEST TYPES — ALL THREE REQUIRED FOR EVERY FEATURE

### Unit Tests (`tests/gold/unit/`)
- Test one function/class in isolation
- ALL external APIs must be mocked — no real API calls in unit tests
- No database, no file system, no network
- Use `pytest-mock`, `responses`, `unittest.mock`
- Must run in < 1 second each
- **Coverage target: 100% for all Gold code**

```python
# Example unit test pattern
def test_facebook_poster_creates_approval_file(tmp_path, mocker):
    mocker.patch('src.social.facebook_poster.requests.post')
    poster = FacebookPoster(vault_path=tmp_path)
    poster.draft_post("Test content")
    approval_files = list((tmp_path / "Pending_Approval").glob("SOCIAL_FB_*.md"))
    assert len(approval_files) == 1
    assert "Test content" in approval_files[0].read_text()
```

### Integration Tests (`tests/gold/integration/`)
- Test two or more components working together
- May use real file system (use `tmp_path` fixture)
- May use real SQLite database (test instance)
- External APIs still mocked
- Must run in < 10 seconds each

```python
# Example integration test pattern
def test_orchestrator_claims_task_and_triggers_skill(tmp_path, mocker):
    # Set up real folder structure in tmp_path
    (tmp_path / "Needs_Action").mkdir()
    task_file = tmp_path / "Needs_Action" / "EMAIL_test.md"
    task_file.write_text("---\ntype: email\n---\nTest email")

    mock_claude = mocker.patch('src.orchestrator.orchestrator.trigger_claude')
    orch = Orchestrator(vault_path=tmp_path)
    orch.process_needs_action()

    assert (tmp_path / "In_Progress" / "EMAIL_test.md").exists()
    assert not task_file.exists()
    mock_claude.assert_called_once()
```

### E2E Tests (`tests/gold/e2e/`)
- Test the complete flow from trigger to completion
- Use real file system (tmp_path)
- Use real SQLite (test instance)
- External APIs mocked at the HTTP level (`responses` library)
- Simulate the full task lifecycle
- Must run in < 30 seconds each

```python
# Example E2E test pattern
@responses.activate
def test_full_email_workflow_end_to_end(tmp_path):
    # Mock Gmail API
    responses.add(responses.GET, 'https://gmail.googleapis.com/...', json={...})

    # Drop a task file
    task = tmp_path / "Needs_Action" / "EMAIL_001.md"
    task.write_text("---\ntype: email\nfrom: client@example.com\n---\nPlease invoice me")

    # Run orchestrator one cycle
    orch = Orchestrator(vault_path=tmp_path)
    orch.run_once()

    # Verify approval file created (email requires approval)
    approvals = list((tmp_path / "Pending_Approval").glob("*.md"))
    assert len(approvals) == 1

    # Simulate human approval
    shutil.move(str(approvals[0]), str(tmp_path / "Approved" / approvals[0].name))

    # Run orchestrator again
    orch.run_once()

    # Verify task completed
    assert (tmp_path / "Done" / "EMAIL_001.md").exists()
    assert (tmp_path / "Logs").glob("*.json")
```

---

## TEST FILE NAMING CONVENTION

```
tests/
└── gold/
    ├── unit/
    │   ├── test_orchestrator.py
    │   ├── test_ralph_wiggum.py
    │   ├── test_odoo_mcp.py
    │   ├── test_facebook_poster.py
    │   ├── test_instagram_poster.py
    │   ├── test_twitter_poster.py
    │   ├── test_error_recovery.py
    │   └── test_audit_logging.py
    ├── integration/
    │   ├── test_orchestrator_integration.py
    │   ├── test_odoo_integration.py
    │   ├── test_mcp_servers.py
    │   └── test_ceo_briefing.py
    └── e2e/
        ├── test_email_flow_e2e.py
        ├── test_social_post_flow_e2e.py
        ├── test_odoo_invoice_flow_e2e.py
        └── test_ceo_briefing_e2e.py
```

---

## RUNNING TESTS

```powershell
# Silver tests (must always pass — run before and after every change)
pytest tests/ -v --ignore=tests/gold
# Expected: 423/427 pass (4 LinkedIn cred failures = known, acceptable)

# All Gold unit tests
pytest tests/gold/unit/ -v

# All Gold integration tests
pytest tests/gold/integration/ -v

# All Gold E2E tests
pytest tests/gold/e2e/ -v

# All tests together with coverage
pytest tests/ -v --cov=src --cov-report=html --cov-fail-under=100

# Run specific feature tests
pytest tests/gold/unit/test_orchestrator.py -v

# Run with verbose output and stop on first failure
pytest tests/gold/ -v -x
```

---

## COVERAGE REQUIREMENTS

| Test Type | Target | Tool |
|---|---|---|
| Unit tests | 100% for all Gold code | `pytest-cov` |
| Integration tests | All component interactions | `pytest-cov` |
| E2E tests | All critical user flows | Manual verification |
| Silver regression | 423/427 pass maintained | `pytest` |

```powershell
# Check coverage report
pytest tests/gold/ --cov=src/orchestrator --cov=src/social --cov=mcp_servers --cov-report=term-missing
```

**If coverage drops below 100% for Gold code → do not merge → write missing tests first.**

---

## SKILL.md FIRST RULE

Before writing any implementation code for a new feature:

1. Check if the SKILL.md already exists in `.claude/skills/`
2. If it does NOT exist → write the SKILL.md first
3. The SKILL.md defines the interface — implementation must match it
4. Only after SKILL.md is complete → write tests → write implementation

---

## COMMIT MESSAGE FORMAT

```
test: RED - <feature> tests written and failing
feat: GREEN - <feature> implemented, all tests pass
refactor: <feature> cleaned up
fix: <component> - <what was broken and how fixed>
docs: <what documentation was added/updated>
```

---

## DEFINITION OF DONE (A feature is complete when)

- [ ] SKILL.md written and reviewed
- [ ] All unit tests written and passing (100% coverage)
- [ ] All integration tests written and passing
- [ ] E2E test written and passing
- [ ] Silver tests still pass (423/427)
- [ ] Tested with real execution following safe testing rules (Only Me visibility, draft state, etc.)
- [ ] Logged to both SQLite and `/Logs/YYYY-MM-DD.json`
- [ ] Dashboard.md updates verified
- [ ] Error cases tested (what happens when API is down)
- [ ] Code committed with correct commit message format
- [ ] `FEATURES.md` checkbox for this feature ticked