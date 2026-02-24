# Browser MCP Setup - Feature 4

## Status: Configuration Documented (Package Not Yet Available)

The `@anthropic-ai/browser-mcp` package referenced in the Gold Tier specs is not yet available on npm as of February 2026. This document provides the intended configuration for when it becomes available.

## Intended Configuration

Add to `~/.claude/claude_code_config.json`:

```json
{
  "mcpServers": {
    "odoo": {
      "command": "node",
      "args": ["C:\\Users\\%USERNAME%\\Desktop\\PIAIC\\AI\\AI-EMPLOYEE-GOLD\\mcp_servers\\odoo_mcp\\index.js"],
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

## Purpose

Browser MCP would be used for:
- Payment portal interactions
- Web automation tasks
- Form submissions on external sites
- Screenshot capture for verification

## Alternative: Playwright Direct

Since Browser MCP is not available, we can use Playwright directly (already installed in Silver):

```python
from playwright.sync_api import sync_playwright

def automate_browser_task(url, actions):
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()
        page.goto(url)
        # Perform actions
        browser.close()
```

This is the same approach used for:
- LinkedIn automation (Silver)
- WhatsApp automation (Silver)
- Facebook automation (Gold Feature 5)
- Instagram automation (Gold Feature 5)
- Twitter automation (Gold Feature 6)

## Verification

When the package becomes available, verify with:

```bash
npx -y @anthropic-ai/browser-mcp --version
```

## Integration with Orchestrator

The orchestrator would detect browser automation tasks and use either:
1. Browser MCP (when available)
2. Direct Playwright (current approach)

No code changes needed - the orchestrator already supports skill-based task routing.

## Conclusion

Feature 4 is documented and ready for implementation when the Browser MCP package is released. In the meantime, direct Playwright usage (already working in Silver) provides the same functionality.
