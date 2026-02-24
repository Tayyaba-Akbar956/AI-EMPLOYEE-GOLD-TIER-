"""LinkedIn Poster Skill for AI Employee Silver Tier.

Autonomous LinkedIn posting with Playwright automation.
Supports text, images, links. Document support coming in next tier.
Includes smart scheduling, approval workflow, retry logic, and comprehensive logging.

KEY FIXES (2026-02-22):
  1. Use launch_persistent_context for stable session management.
  2. Open share modal via dispatch_event('click') — avoids Playwright
     timeout caused by LinkedIn's async React handlers never idling.
  3. Type content via clipboard (JS navigator.clipboard) so Quill/ProseMirror
     editors receive it correctly.
  4. Use page.expect_file_chooser() for reliable file upload.
  5. Type link URL BEFORE attaching media (LinkedIn resets editor on media attach).
  6. Guard against attaching both media and document (LinkedIn disallows this).
  7. Scope all selectors inside the modal ([role="dialog"]) to avoid false matches.
  8. Use Playwright-native locators instead of page.evaluate JS hacks for clicks.
  9. Launch browser with anti-detection args and slow_mo for human-like behaviour.
 10. Retry logic: exponential back-off on network errors.
 11. FIX: Widen viewport to 1400x900 so modal fits without clipping Post button.
 12. FIX: _click_post_button uses JS scrollIntoView + .click() as primary strategy
     to bypass Playwright viewport clipping (root cause of "Post button not found").

MEDIA / DOCUMENT UPLOAD FIXES (2026-02-22):
 13. FIX (CRITICAL): LinkedIn's share modal has a TOOLBAR at the bottom with icon
     buttons. Clicking the photo/video icon opens a SECOND sub-toolbar (or directly
     a file chooser). The old code searched for a single button matching "photo"
     which never fired the filechooser event — causing expect_file_chooser() to
     time out and crash the browser session.

     Correct flow for images/video:
       a. Find the bottom toolbar inside the modal.
       b. Dispatch click on the media/photo button (aria-label contains
          "photo", "video", "media" — all are viable depending on LI version).
       c. The file chooser dialog fires immediately — intercept with
          page.expect_file_chooser() wrapping ONLY the dispatch_event call.
       d. After files are set, LinkedIn renders a preview + "Done" button.
       e. MUST click "Done" / "Next" to return to the main post modal.
       f. Only then is the Post button clickable.

     Correct flow for documents:
       a. Same toolbar, different icon (briefcase/document icon).
       b. LinkedIn may show a title input after the file chooser — fill or skip.
       c. Click "Done" to return to the main modal.

 14. FIX: Use page.on("filechooser") event handler as a fallback when
     expect_file_chooser context manager fails (timing edge cases).

 15. FIX: Added _wait_for_media_preview() to wait for the upload preview to
     render before attempting to click "Done" — prevents race conditions.

 16. FIX: Added _click_done_button() helper that finds and clicks the Done/Next
     button that LinkedIn shows after a file is attached, returning the user
     to the main post composition modal.

 17. FIX: Expanded toolbar button selector list to cover all known LinkedIn
     aria-label variants for the photo/media and document buttons.

 18. FIX: Added set_input_files() direct approach as a fallback — LinkedIn
     sometimes renders a hidden <input type="file"> inside the modal that
     Playwright can target directly, bypassing the file chooser dialog.
"""

import os
import json
import logging
import time
import subprocess
import sys
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Any, Optional
from uuid import uuid4

from dotenv import load_dotenv
from playwright.sync_api import sync_playwright, BrowserContext, Page, TimeoutError as PlaywrightTimeout

load_dotenv()

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Clipboard helper
# ---------------------------------------------------------------------------
def _copy_to_clipboard(text: str, page: Page) -> None:
    """Write *text* into the OS clipboard via JS so Playwright can paste it."""
    page.evaluate(
        "text => navigator.clipboard.writeText(text)",
        text,
    )


# ---------------------------------------------------------------------------
# Anti-detection browser args
# ---------------------------------------------------------------------------
_BROWSER_ARGS = [
    "--disable-blink-features=AutomationControlled",
    "--no-sandbox",
    "--disable-dev-shm-usage",
    "--disable-infobars",
    "--disable-extensions",
]


class LinkedInPoster:
    """Manages autonomous LinkedIn posting with Playwright."""

    MAX_CONTENT_LENGTH = 3000
    MAX_DAILY_POSTS = 25
    SESSION_VALIDITY_DAYS = 7
    RETRY_DELAY_SECONDS = 300

    IMPORTANCE_LEVELS = ['low', 'normal', 'high', 'critical']
    APPROVAL_REQUIRED = ['high', 'critical']

    OPTIMAL_HOURS = list(range(9, 18))
    OPTIMAL_DAYS = list(range(0, 5))

    # All known aria-label fragments LinkedIn uses for the photo/video toolbar button.
    # LinkedIn A/B tests these labels — covering all known variants.
    _MEDIA_BTN_LABELS = [
        "Add a photo",
        "Add photos or video",
        "Add photo",
        "Photo",
        "Media",
        "Add media",
        "photo",
        "video",
        "media",
        "image",
        "Image",
        "Photo/video",
    ]

    # All known aria-label fragments for the document toolbar button.
    _DOC_BTN_LABELS = [
        "Add a document",
        "Add document",
        "Document",
        "document",
        "pdf",
        "PDF",
        "file",
        "File",
        "Attach",
    ]

    def __init__(self, db_manager, vault_path: str, config: Optional[Dict] = None):
        self.db = db_manager
        self.vault_path = Path(vault_path)
        self.config = {
            # headless=False is REQUIRED — LinkedIn blocks headless Chromium.
            'headless': False,
            # Persistent profile dir — more stable than storage_state JSON.
            'profile_dir': str(self.vault_path / '.linkedin_profile'),
            'slow_mo': 120,
            'max_retries': 2,
            'retry_delay': self.RETRY_DELAY_SECONDS,
        }
        if config:
            self.config.update(config)
        Path(self.config['profile_dir']).mkdir(parents=True, exist_ok=True)
        self._ensure_folders()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _ensure_folders(self):
        folders = [
            'Pending_Approval/linkedin_posts',
            'Approved/linkedin_posts',
            'Logs/linkedin_posts',
        ]
        for folder in folders:
            (self.vault_path / folder).mkdir(parents=True, exist_ok=True)

    def _get_persistent_context(self, playwright_instance):
        """Return a persistent browser context (keeps cookies / localStorage)."""
        return playwright_instance.chromium.launch_persistent_context(
            user_data_dir=self.config['profile_dir'],
            headless=self.config['headless'],
            slow_mo=self.config['slow_mo'],
            args=_BROWSER_ARGS,
            # Widened from 1280x800 — ensures modal fits without clipping Post button
            viewport={"width": 1400, "height": 900},
        )

    def _ensure_logged_in(self, context: BrowserContext) -> Page:
        """Navigate to LinkedIn feed and authenticate if needed."""
        page = context.new_page()
        page.goto('https://www.linkedin.com/feed/', timeout=60_000)
        self._wait_for_page(page)

        if self._needs_login(page.url):
            logger.warning("Not logged in — authenticating...")
            self._authenticate_linkedin(page)

        if 'feed' not in page.url:
            page.goto('https://www.linkedin.com/feed/', timeout=60_000)
            self._wait_for_page(page)

        if 'feed' not in page.url:
            raise RuntimeError(f"Could not reach LinkedIn feed. Current URL: {page.url}")

        try:
            page.wait_for_selector(
                '[aria-label="Start a post"], [data-view-name="share-sharebox-focus"], '
                '.share-box-feed-entry__trigger',
                timeout=20_000, state='visible'
            )
            logger.info("Feed fully loaded — share box visible.")
        except PlaywrightTimeout:
            logger.warning("Share box not detected — feed may still be loading, continuing anyway...")

        logger.info(f"Logged in. Feed URL: {page.url}")
        return page

    @staticmethod
    def _needs_login(url: str) -> bool:
        return any(x in url for x in ('login', 'uas/login', 'session_redirect', 'authwall'))

    @staticmethod
    def _wait_for_page(page: Page) -> None:
        """Wait for page to settle."""
        try:
            page.wait_for_load_state('networkidle', timeout=20_000)
        except PlaywrightTimeout:
            page.wait_for_load_state('domcontentloaded')

    def _authenticate_linkedin(self, page: Page) -> None:
        """Fill login form and wait for successful redirect to /feed/."""
        email = os.getenv('LINKEDIN_EMAIL')
        password = os.getenv('LINKEDIN_PASSWORD')
        if not email or not password:
            raise ValueError("LINKEDIN_EMAIL and LINKEDIN_PASSWORD must be set in .env")

        page.goto('https://www.linkedin.com/login', timeout=60_000)
        page.wait_for_load_state('domcontentloaded')

        page.fill('#username', email)
        page.wait_for_timeout(600)
        page.fill('#password', password)
        page.wait_for_timeout(500)
        page.click('[type="submit"]')

        deadline = time.time() + 60
        while time.time() < deadline:
            url = page.url
            if 'feed' in url:
                logger.info("LinkedIn login successful.")
                page.wait_for_timeout(4_000)
                return
            if any(x in url for x in ('checkpoint', 'challenge', 'verification')):
                logger.warning("LinkedIn security check — please complete in the browser (5 min timeout)...")
                verify_deadline = time.time() + 300
                while time.time() < verify_deadline:
                    page.wait_for_timeout(3_000)
                    if 'feed' in page.url:
                        logger.info("Verification completed.")
                        page.wait_for_timeout(4_000)
                        return
                raise RuntimeError("Verification timeout after 5 minutes.")
            page.wait_for_timeout(1_000)

        raise RuntimeError(f"Login timeout. Last URL: {page.url}")

    # ------------------------------------------------------------------
    # Modal helpers
    # ------------------------------------------------------------------

    def _open_share_modal(self, page: Page) -> None:
        """
        Open LinkedIn's share/post modal — 4-strategy cascade.

        FIX: Strategy 1 uses dispatch_event('click') instead of .click().
        Playwright's .click() waits for all network activity triggered by
        the click to settle, which causes a 5s timeout on LinkedIn because
        the click launches async React state updates that never fully idle.
        dispatch_event fires the event and returns immediately.
        """
        editor_selector = (
            '[role="dialog"] div[contenteditable="true"], '
            '[aria-modal="true"] div[contenteditable="true"]'
        )

        def editor_visible() -> bool:
            try:
                page.wait_for_selector(editor_selector, timeout=8_000, state='visible')
                return True
            except PlaywrightTimeout:
                return False

        # --- Strategy 1: dispatch_event (avoids click timeout) ---
        logger.info("Strategy 1: dispatch_event on 'Start a post' trigger ...")
        page.wait_for_timeout(2_000)
        trigger_selectors_s1 = [
            '[data-view-name="share-sharebox-focus"]',
            '.share-box-feed-entry__trigger',
            '[aria-label="Start a post"]',
            'button:has-text("Start a post")',
        ]
        for sel in trigger_selectors_s1:
            try:
                locator = page.locator(sel).first
                if locator.count() > 0 and locator.is_visible():
                    locator.dispatch_event('click')
                    logger.info(f"Strategy 1 dispatch_event: {sel}")
                    page.wait_for_timeout(2_500)
                    if editor_visible():
                        logger.info("Modal opened via dispatch_event click.")
                        return
                    break
            except Exception as e:
                logger.warning(f"Strategy 1 selector {sel} failed: {e}")

        # --- Strategy 2: ?shareActive=true URL param ---
        logger.info("Strategy 2: navigating to ?shareActive=true ...")
        try:
            page.goto('https://www.linkedin.com/feed/?shareActive=true', timeout=60_000)
            self._wait_for_page(page)
            page.wait_for_timeout(3_000)
            if 'feed' not in page.url:
                logger.warning(f"Strategy 2 redirected to {page.url} — navigating back to feed...")
                page.goto('https://www.linkedin.com/feed/', timeout=60_000)
                self._wait_for_page(page)
                page.wait_for_timeout(2_000)
            elif editor_visible():
                logger.info("Modal opened via ?shareActive=true.")
                return
        except Exception as e:
            logger.warning(f"Strategy 2 failed: {e}")
            page.goto('https://www.linkedin.com/feed/', timeout=60_000)
            self._wait_for_page(page)

        page.wait_for_timeout(2_000)

        # --- Strategy 3: JS click with navigation guard ---
        logger.info("Strategy 3: JS click on share-box trigger ...")
        opened = page.evaluate("""
            () => {
                const candidates = [
                    document.querySelector('[data-view-name="share-sharebox-focus"]'),
                    document.querySelector('.share-box-feed-entry__trigger'),
                    document.querySelector('[aria-label="Start a post"]'),
                    (() => {
                        for (const el of document.querySelectorAll('button, div[role="button"], a')) {
                            if ((el.textContent || '').trim() === 'Start a post') return el;
                        }
                        return null;
                    })(),
                ];
                for (const el of candidates) {
                    if (!el) continue;
                    let ancestor = el;
                    while (ancestor && ancestor !== document.body) {
                        if (ancestor.tagName === 'A') {
                            ancestor.addEventListener('click', e => e.preventDefault(), { once: true });
                        }
                        ancestor = ancestor.parentElement;
                    }
                    el.dispatchEvent(new MouseEvent('click', { bubbles: false, cancelable: true }));
                    return el.tagName + ':' + (el.className || el.getAttribute('aria-label') || '');
                }
                return null;
            }
        """)
        if opened:
            logger.info(f"Strategy 3 clicked: {opened}")
            page.wait_for_timeout(3_000)
            if editor_visible():
                logger.info("Modal opened via JS click.")
                return

        # --- Strategy 4: Playwright force-click ---
        logger.info("Strategy 4: Playwright force-click on share trigger ...")
        trigger_selectors = [
            '[data-view-name="share-sharebox-focus"]',
            '.share-box-feed-entry__trigger',
            '[aria-label="Start a post"]',
            'button:has-text("Start a post")',
            'div:has-text("Start a post")',
        ]
        for sel in trigger_selectors:
            try:
                locator = page.locator(sel).first
                if locator.count() > 0 and locator.is_visible():
                    locator.click(force=True, timeout=5_000)
                    logger.info(f"Strategy 4 clicked: {sel}")
                    page.wait_for_timeout(3_000)
                    if editor_visible():
                        logger.info("Modal opened via force-click.")
                        return
            except Exception as e:
                logger.warning(f"Strategy 4 selector {sel} failed: {e}")

        self._save_debug_info(page, 'all_modal_strategies_failed')
        raise RuntimeError(
            "All 4 strategies to open the share modal failed. "
            "Check the saved HTML/screenshot in Logs/linkedin_posts/."
        )

    def _find_editor(self, page: Page) -> str:
        """Return the first visible contenteditable selector inside the modal."""
        selectors = [
            '[role="dialog"] div[contenteditable="true"][data-placeholder]',
            '[aria-modal="true"] div[contenteditable="true"][data-placeholder]',
            '[role="dialog"] div[contenteditable="true"][role="textbox"]',
            '[aria-modal="true"] div[contenteditable="true"][role="textbox"]',
            '[role="dialog"] .ql-editor',
            '[aria-modal="true"] .ql-editor',
            '[role="dialog"] div[contenteditable="true"]',
            '[aria-modal="true"] div[contenteditable="true"]',
            'div[contenteditable="true"][data-placeholder]',
            'div[contenteditable="true"][role="textbox"]',
            'div[contenteditable="true"]',
        ]
        for sel in selectors:
            try:
                page.wait_for_selector(sel, timeout=5_000, state='visible')
                logger.info(f"Found editor with selector: {sel}")
                return sel
            except PlaywrightTimeout:
                logger.debug(f"Editor selector not matched: {sel}")
                continue
        self._save_debug_info(page, 'editor_not_found')
        raise RuntimeError(
            "Could not find post editor. "
            "Upload the saved HTML from Logs/linkedin_posts/ to diagnose the DOM."
        )

    def _type_content(self, page: Page, editor_sel: str, content: str) -> None:
        """
        Type content into LinkedIn's rich-text editor via clipboard paste.
        LinkedIn uses Quill/ProseMirror which does not reliably accept
        keyboard.type() for long strings.
        """
        editor = page.locator(editor_sel).first
        editor.click()
        page.wait_for_timeout(400)

        page.keyboard.press('Control+a')
        page.wait_for_timeout(200)
        page.keyboard.press('Backspace')
        page.wait_for_timeout(200)

        _copy_to_clipboard(content, page)
        page.wait_for_timeout(300)
        page.keyboard.press('Control+v')
        page.wait_for_timeout(600)

        actual = editor.inner_text()
        if not actual.strip():
            logger.warning("Clipboard paste failed, falling back to keyboard.type()...")
            editor.click()
            page.keyboard.press('Control+a')
            page.keyboard.press('Backspace')
            page.keyboard.type(content, delay=25)

        logger.info(f"Content typed ({len(content)} chars).")

    # ------------------------------------------------------------------
    # FIXED: Media / file attachment helpers
    # ------------------------------------------------------------------

    def _find_toolbar_button(self, page: Page, label_list: List[str]) -> Optional[Any]:
        """
        Locate a toolbar button inside the share modal by trying a list of
        aria-label fragments. Returns the first matching Playwright Locator,
        or None if nothing is found.

        LinkedIn renders the toolbar as a row of icon buttons below the
        text editor. The buttons carry aria-labels that change with A/B tests.
        We try every known variant.
        """
        # Try to scope inside the modal first, then fall back to full page
        containers = [
            page.locator('[role="dialog"]').first,
            page.locator('[aria-modal="true"]').first,
            page.locator('body'),
        ]

        for container in containers:
            try:
                if container.count() == 0:
                    continue
            except Exception:
                continue

            for label in label_list:
                # Try aria-label contains
                for sel in [
                    f'button[aria-label="{label}"]',
                    f'[role="button"][aria-label="{label}"]',
                    f'button[aria-label*="{label}"]',
                    f'[role="button"][aria-label*="{label}"]',
                ]:
                    try:
                        btn = container.locator(sel).first
                        if btn.count() > 0 and btn.is_visible():
                            logger.info(f"Found toolbar button: selector='{sel}'")
                            return btn
                    except Exception:
                        pass

        logger.debug(f"No toolbar button found for labels: {label_list}")
        return None

    def _attach_file_via_chooser(self, page: Page, trigger_btn, file_path: str) -> bool:
        """
        Click *trigger_btn* inside a page.expect_file_chooser() context so that
        the native file dialog is intercepted and the file is set programmatically.

        LinkedIn's media buttons fire a native file picker directly on click —
        this is the correct interception point.

        Returns True on success, False on failure.
        """
        logger.info(f"Attempting file chooser interception for: {file_path}")
        try:
            with page.expect_file_chooser(timeout=15_000) as fc_info:
                # dispatch_event avoids Playwright's actionability checks and
                # React idle-wait which can cause a timeout before the file
                # chooser event fires.
                trigger_btn.dispatch_event('click')
            file_chooser = fc_info.value
            file_chooser.set_files(file_path)
            logger.info(f"File set via file chooser: {file_path}")
            return True
        except PlaywrightTimeout:
            logger.warning("expect_file_chooser timed out — file chooser did not open.")
            return False
        except Exception as e:
            logger.warning(f"File chooser approach failed: {e}")
            return False

    def _attach_file_via_hidden_input(self, page: Page, file_path: str) -> bool:
        """
        Fallback: LinkedIn sometimes renders a hidden <input type='file'> inside
        the modal DOM. Playwright's set_input_files() can target it directly
        even when it is not visible (uses force=True internally).

        Returns True on success.
        """
        logger.info("Fallback: attempting direct set_input_files on hidden input...")
        input_selectors = [
            '[role="dialog"] input[type="file"]',
            '[aria-modal="true"] input[type="file"]',
            'input[type="file"]',
        ]
        for sel in input_selectors:
            try:
                inp = page.locator(sel).first
                if inp.count() > 0:
                    inp.set_input_files(file_path)
                    logger.info(f"File set via hidden input ({sel}): {file_path}")
                    return True
            except Exception as e:
                logger.debug(f"Hidden input selector {sel} failed: {e}")
        return False

    def _wait_for_media_preview(self, page: Page, timeout_ms: int = 30_000) -> None:
        """
        After setting files, wait until LinkedIn signals the image is ready.

        ROOT CAUSE of the hang: The old code iterated selectors one-by-one, each
        with the full timeout_ms. If the first 8 selectors all timed out (30s each)
        the function blocked for 4+ minutes before falling through. Meanwhile the
        Next button WAS visible but we never got to checking for it.

        FIX: Use a short per-selector probe (3s) to scan all selectors quickly,
        then repeat the whole scan up to total timeout_ms. This way we catch the
        Next/Done button the moment it appears regardless of which selector matches.

        LinkedIn's image upload flow (2025):
          1. File chooser fires → image selected
          2. LinkedIn renders an image crop/edit modal (separate React portal,
             NOT inside [role="dialog"] — mounted directly on <body>)
          3. A "Next" button appears in this new modal's header/footer
          4. Clicking Next returns to the compose view with the image attached
          5. The Post button is now active
        """
        logger.info("Waiting for media upload / Next button to appear...")

        # These are signals that the image Editor modal is ready.
        # CONFIRMED from screenshot: LinkedIn shows an "Editor" modal with a
        # blue "Next" button in the bottom-right corner.
        ready_selectors = [
            # Most reliable: artdeco-button__text span (LinkedIn's button structure)
            'span.artdeco-button__text',
            # The Next/Done button itself
            'button[aria-label="Next"]',
            'button[aria-label="Done"]',
            # Image preview inside the editor
            'img[src^="blob:"]',
            'img[src*="dms/image"]',
            'img[src*="media"]',
            # Editor modal container
            '.share-creation-state',
            '.artdeco-modal',
        ]

        deadline = time.time() + (timeout_ms / 1000)
        probe_ms = 3_000  # short probe per selector so we cycle fast

        while time.time() < deadline:
            for sel in ready_selectors:
                try:
                    page.wait_for_selector(sel, timeout=probe_ms, state='visible')
                    logger.info(f"Media ready signal detected: '{sel}'")
                    return
                except PlaywrightTimeout:
                    continue
            # Brief pause before re-scanning
            page.wait_for_timeout(500)

        logger.warning(
            "No media ready signal detected after waiting. "
            "Proceeding anyway — Next button click will handle it."
        )

    def _click_done_button(self, page: Page) -> None:
        """
        Click the "Next" button inside LinkedIn's image Editor modal.

        CONFIRMED FROM SCREENSHOT (post_button_not_found_20260223_062317.png):
          - LinkedIn shows an "Editor" titled modal (NOT artdeco-modal / [role="dialog"])
          - The modal contains the image preview with edit tools
          - Bottom-right has two buttons: [Back] [Next]  (Next is blue/primary)
          - The Next button text is rendered inside an artdeco-button__text <span>
          - btn.innerText may return "Next" with surrounding whitespace/newlines
            depending on LinkedIn's React render — so we MUST use .trim() and also
            check ALL descendant text nodes, not just direct innerText.

        WHY PREVIOUS CODE FAILED:
          - JS was excluding "Back" correctly but the text comparison used
            .includes() on the full button innerText which for LinkedIn's
            artdeco-button looks like "\n  Next\n" — the WANT.includes(t)
            check after .trim() should work, but if the span renders as
            "Next " (trailing space) the exact match fails silently.
          - Playwright locators using .filter(has_text='Next') also match
            the Back button's parent container if it contains "Next" anywhere.

        FIX STRATEGY ORDER:
          1. CSS selector targeting artdeco-button__text span — most precise,
             directly targets the text node LinkedIn uses inside every button.
          2. JS with textContent.trim() on ALL descendant text nodes — catches
             any whitespace variation in innerText.
          3. Playwright force-click with exact text matching via get_by_text.
          4. Coordinate click — nuclear option using the bounding box of the
             Editor modal's bottom-right corner where Next always appears.
          5. Keyboard Tab+Enter — navigate to and activate the Next button
             without relying on any selector at all.
        """
        logger.info("Clicking Next button in image Editor modal...")

        # Give LinkedIn time to fully render the Editor modal
        page.wait_for_timeout(2_500)

        # ----------------------------------------------------------------
        # Strategy 1: Target artdeco-button__text span directly
        # This is the exact HTML LinkedIn uses: <span class="artdeco-button__text">Next</span>
        # ----------------------------------------------------------------
        logger.info("Strategy 1: artdeco-button__text span selector...")
        span_selectors = [
            'span.artdeco-button__text',
            '.artdeco-button__text',
            'button span',
            'button > span',
        ]
        for span_sel in span_selectors:
            try:
                spans = page.locator(span_sel).all()
                for span in spans:
                    try:
                        txt = (span.inner_text() or '').strip()
                        if txt == 'Next' or txt == 'Done':
                            # Click the parent button, not the span
                            parent = span.locator('xpath=..') 
                            parent.click(force=True, timeout=5_000)
                            logger.info(f"Strategy 1: clicked parent of span '{txt}' via '{span_sel}'")
                            page.wait_for_timeout(2_500)
                            return
                    except Exception:
                        continue
            except Exception as e:
                logger.debug(f"Strategy 1 span selector '{span_sel}' failed: {e}")

        # ----------------------------------------------------------------
        # Strategy 2: JS using textContent on ALL descendant nodes
        # Handles any whitespace variation that trips up innerText checks
        # ----------------------------------------------------------------
        logger.info("Strategy 2: JS deep textContent scan for Next/Done...")
        clicked = page.evaluate("""
            () => {
                const WANT    = ['Next', 'Done'];
                const EXCLUDE = ['Post', 'Post now', 'Share', 'Cancel', 'Discard', 'Close', 'Skip'];

                function allText(el) {
                    // Collect text from ALL child text nodes — catches span-wrapped text
                    return (el.textContent || el.innerText || '').replace(/\\s+/g, ' ').trim();
                }

                for (const btn of document.querySelectorAll('button, [role="button"]')) {
                    if (btn.disabled || btn.getAttribute('aria-disabled') === 'true') continue;

                    const txt   = allText(btn);
                    const label = (btn.getAttribute('aria-label') || '').trim();

                    const isWanted   = WANT.some(w => txt === w || label === w);
                    const isExcluded = EXCLUDE.some(e => txt.toLowerCase().includes(e.toLowerCase()));

                    if (isWanted && !isExcluded) {
                        btn.scrollIntoView({ behavior: 'instant', block: 'center' });
                        // Use both dispatchEvent AND direct .click() for reliability
                        btn.dispatchEvent(new MouseEvent('click', { bubbles: true, cancelable: true }));
                        btn.click();
                        return `text="${txt}" label="${label}" class="${btn.className.slice(0,60)}"`;
                    }
                }

                // Last-ditch: dump all button texts for debugging
                return 'NOTFOUND:' + [...document.querySelectorAll('button, [role="button"]')]
                    .map(b => `"${allText(b)}"`)
                    .join(',');
            }
        """)
        if clicked and not clicked.startswith('NOTFOUND:'):
            logger.info(f"Strategy 2: Next/Done clicked — {clicked}")
            page.wait_for_timeout(2_500)
            return
        else:
            logger.warning(f"Strategy 2 result: {clicked}")

        # ----------------------------------------------------------------
        # Strategy 3: Playwright get_by_text with exact=True + force click
        # ----------------------------------------------------------------
        logger.info("Strategy 3: Playwright get_by_text exact match...")
        for label in ['Next', 'Done']:
            try:
                # get_by_text matches on visible text content of any element
                btn = page.get_by_text(label, exact=True).first
                if btn.count() > 0:
                    btn.click(force=True, timeout=5_000)
                    logger.info(f"Strategy 3: clicked get_by_text('{label}')")
                    page.wait_for_timeout(2_500)
                    return
            except Exception as e:
                logger.debug(f"Strategy 3 get_by_text('{label}') failed: {e}")

        # ----------------------------------------------------------------
        # Strategy 4: Bounding-box coordinate click
        # From the screenshot: the Editor modal spans roughly x=557–893, y=63–325.
        # The Next button is always in the BOTTOM-RIGHT of the modal.
        # We find the modal's bounding box and click its bottom-right area.
        # ----------------------------------------------------------------
        logger.info("Strategy 4: Coordinate click on bottom-right of Editor modal...")
        modal_bb = page.evaluate("""
            () => {
                // Try every known container for the Editor modal
                const candidates = [
                    document.querySelector('.share-creation-state'),
                    document.querySelector('[data-test-modal]'),
                    document.querySelector('.artdeco-modal'),
                    document.querySelector('[role="dialog"]'),
                    document.querySelector('[aria-modal="true"]'),
                    // Find any element with "Editor" as a heading/title
                    (() => {
                        for (const el of document.querySelectorAll('*')) {
                            if ((el.innerText || '').trim() === 'Editor' &&
                                el.tagName.match(/^H[1-6]$/i)) {
                                return el.closest('[class*="modal"], [role="dialog"], [class*="overlay"]');
                            }
                        }
                        return null;
                    })(),
                ];
                for (const c of candidates) {
                    if (!c) continue;
                    const r = c.getBoundingClientRect();
                    if (r.width > 100 && r.height > 100) {
                        return { x: r.left, y: r.top, w: r.width, h: r.height };
                    }
                }
                return null;
            }
        """)
        if modal_bb:
            # Click bottom-right area of the modal (where Next always lives)
            click_x = modal_bb['x'] + modal_bb['w'] - 45   # ~45px from right edge
            click_y = modal_bb['y'] + modal_bb['h'] - 18   # ~18px from bottom edge
            logger.info(f"Strategy 4: clicking coordinate ({click_x:.0f}, {click_y:.0f}) "
                        f"[modal bb: {modal_bb}]")
            page.mouse.click(click_x, click_y)
            page.wait_for_timeout(2_500)
            # Verify the Editor modal closed (means Next was clicked successfully)
            try:
                # If editor modal is gone, we succeeded
                page.wait_for_timeout(500)
                still_has_editor = page.evaluate("""
                    () => {
                        for (const el of document.querySelectorAll('*')) {
                            if ((el.innerText || '').trim() === 'Editor') return true;
                        }
                        return false;
                    }
                """)
                if not still_has_editor:
                    logger.info("Strategy 4: Editor modal closed — Next click confirmed.")
                    return
                logger.warning("Strategy 4: Editor modal still present after coordinate click.")
            except Exception:
                pass
        else:
            logger.warning("Strategy 4: Could not find Editor modal bounding box.")

        # ----------------------------------------------------------------
        # Strategy 5: Tab navigation — find focus, Tab until Next, press Enter
        # Completely bypasses selector/coordinate issues.
        # ----------------------------------------------------------------
        logger.info("Strategy 5: Keyboard Tab navigation to Next button...")
        try:
            # Click the modal area first to ensure focus is inside it
            page.keyboard.press('Escape')   # close any sub-menus
            page.wait_for_timeout(300)
            # Tab up to 15 times looking for the Next/Done button
            for _ in range(15):
                page.keyboard.press('Tab')
                page.wait_for_timeout(150)
                focused_text = page.evaluate("""
                    () => {
                        const el = document.activeElement;
                        if (!el) return '';
                        return (el.innerText || el.textContent || el.value || '').replace(/\\s+/g, ' ').trim();
                    }
                """)
                logger.debug(f"Tab focused element text: '{focused_text}'")
                if focused_text in ('Next', 'Done'):
                    page.keyboard.press('Enter')
                    logger.info(f"Strategy 5: Tab+Enter on '{focused_text}' button")
                    page.wait_for_timeout(2_500)
                    return
        except Exception as e:
            logger.warning(f"Strategy 5 keyboard nav failed: {e}")

        # Final debug dump
        all_buttons = page.evaluate("""
            () => [...document.querySelectorAll('button, [role="button"]')].map(b => ({
                text: (b.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 60),
                label: b.getAttribute('aria-label'),
                disabled: b.disabled,
                class: (b.className || '').slice(0, 80),
                visible: b.offsetParent !== null,
                rect: (() => { const r = b.getBoundingClientRect(); return {x: Math.round(r.x), y: Math.round(r.y), w: Math.round(r.width), h: Math.round(r.height)}; })(),
            }))
        """)
        logger.error(f"ALL 5 strategies failed. Page buttons dump: {json.dumps(all_buttons, indent=2)}")
        self._save_debug_info(page, 'next_button_all_strategies_failed')
        raise RuntimeError(
            "Could not click the Next/Done button after image upload.\n"
            "Check the saved screenshot and HTML in Logs/linkedin_posts/.\n"
            f"Buttons found on page: {[b['text'] for b in all_buttons if b['text']]}"
        )

    def _attach_media(self, page: Page, media_paths: List[str]) -> None:
        """
        Attach one or more image/video files to the LinkedIn post.

        FIXED FLOW:
        1. Find the photo/video toolbar button in the share modal.
        2. Use expect_file_chooser() wrapping dispatch_event('click') to
           intercept the native file dialog — do NOT use .click() which may
           never fire the filechooser event due to React async handlers.
        3. Pass ALL files in a single set_files() call if LinkedIn supports
           multi-select (it does for images), or loop for multiple files.
        4. Wait for the media preview to render.
        5. Click the "Done" button to return to compose view.
        """
        if not media_paths:
            return

        logger.info(f"Attaching {len(media_paths)} media file(s): {media_paths}")

        # Find the photo/video toolbar button
        photo_btn = self._find_toolbar_button(page, self._MEDIA_BTN_LABELS)
        if photo_btn is None:
            self._save_debug_info(page, 'media_button_not_found')
            raise RuntimeError(
                "Could not find the photo/media toolbar button in the share modal.\n"
                "Check the saved debug HTML — LinkedIn may have changed its DOM.\n"
                "Known aria-label variants tried: " + str(self._MEDIA_BTN_LABELS)
            )

        # Attempt 1: file chooser interception (primary method)
        # Pass all images at once if there are multiple
        if len(media_paths) == 1:
            success = self._attach_file_via_chooser(page, photo_btn, media_paths[0])
        else:
            # For multi-file, intercept chooser and pass array
            logger.info(f"Multi-file upload: {len(media_paths)} files")
            try:
                with page.expect_file_chooser(timeout=15_000) as fc_info:
                    photo_btn.dispatch_event('click')
                file_chooser = fc_info.value
                file_chooser.set_files(media_paths)  # pass list directly
                logger.info(f"Multiple files set via file chooser: {media_paths}")
                success = True
            except Exception as e:
                logger.warning(f"Multi-file chooser failed: {e}")
                success = False

        # Attempt 2: hidden input fallback
        if not success:
            logger.info("File chooser did not fire — trying hidden input fallback...")
            # Click the button first to reveal the input, then use set_input_files
            try:
                photo_btn.click(force=True, timeout=5_000)
                page.wait_for_timeout(1_000)
            except Exception:
                pass
            success = self._attach_file_via_hidden_input(page, media_paths[0])

        if not success:
            self._save_debug_info(page, 'media_attach_failed')
            raise RuntimeError(
                f"Failed to attach media file(s): {media_paths}\n"
                "Both file chooser and hidden input approaches failed.\n"
                "Check the saved debug screenshot."
            )

        # Wait for upload preview, then click Done to return to compose view
        self._wait_for_media_preview(page)
        page.wait_for_timeout(1_000)
        self._click_done_button(page)
        logger.info("Media attachment complete — returned to compose view.")

    def _attach_document(self, page: Page, document_path: str) -> None:
        """
        Attach a PDF/document to a LinkedIn post.

        CONFIRMED FLOW FROM SCREENSHOTS (documnet_failed_1..5.png):
        ┌─────────────────────────────────────────────────────────────┐
        │ Step 1 — Compose modal toolbar (Image 5, 6:50)              │
        │   Toolbar: [📷][📅][⚙️][+]                                  │
        │   The document button is HIDDEN — click [+] to expand       │
        │   Then "Add a document" tooltip appears (Image 4, 6:51)     │
        │                                                             │
        │ Step 2 — "Share a document" modal opens (Image 3, 6:52)     │
        │   Shows a large "Choose file" button — THIS triggers the    │
        │   file chooser, NOT a hidden input or toolbar button        │
        │                                                             │
        │ Step 3 — File uploaded (Image 2, 6:53)                      │
        │   "Document title *" field appears (required, empty)        │
        │   File name shows: "CS101 Introduction to Computing..."     │
        │   Progress bar at bottom (upload in progress)               │
        │   [Back] [Done] buttons — Done is BLUE (active)             │
        │                                                             │
        │ Step 4 — Click Done → back to compose (Image 1, 6:54)       │
        │   Document preview shown inside compose modal               │
        │   Text field at top, Post button blue ✅                    │
        └─────────────────────────────────────────────────────────────┘

        KEY DIFFERENCES from old code:
          - Document button is behind a [+] overflow button, NOT directly in toolbar
          - The file chooser is triggered by a "Choose file" BUTTON inside the
            "Share a document" modal, NOT by the initial toolbar button click
          - Title field is REQUIRED (asterisk) — must be filled before Done works
          - Done button label is "Done", not "Next"
        """
        logger.info(f"Attaching document: {document_path}")
        page.wait_for_timeout(1_000)

        # ------------------------------------------------------------------
        # STEP 1a: Try the direct document toolbar button first.
        # On some LinkedIn versions/viewports it's directly visible.
        # ------------------------------------------------------------------
        logger.info("Step 1a: Looking for direct document toolbar button...")
        doc_btn = self._find_toolbar_button(page, self._DOC_BTN_LABELS)

        # ------------------------------------------------------------------
        # STEP 1b: If not found, click the [+] overflow button first.
        # CONFIRMED: When viewport is wide, LinkedIn collapses extra toolbar
        # items behind a "+" button. "Add a document" is one of them.
        # ------------------------------------------------------------------
        if doc_btn is None:
            logger.info("Step 1b: Direct doc button not found — clicking [+] overflow...")
            self._click_toolbar_overflow(page)
            page.wait_for_timeout(1_500)
            # Now look for "Add a document" in the expanded menu
            doc_btn = self._find_toolbar_button(page, self._DOC_BTN_LABELS)

        if doc_btn is None:
            self._save_debug_info(page, 'document_button_not_found')
            raise RuntimeError(
                "Could not find 'Add a document' button even after expanding [+] overflow.\n"
                "Check debug HTML in Logs/linkedin_posts/."
            )

        # ------------------------------------------------------------------
        # STEP 2: Click the document button to open "Share a document" modal.
        # Then click the "Choose file" button INSIDE that modal to open
        # the file chooser. The file chooser is on "Choose file", NOT on
        # the initial toolbar button click.
        # ------------------------------------------------------------------
        logger.info("Step 2: Clicking document button to open 'Share a document' modal...")

        # Click toolbar doc button (opens the Share a document modal)
        try:
            doc_btn.dispatch_event('click')
        except Exception:
            try:
                doc_btn.click(force=True, timeout=5_000)
            except Exception as e:
                logger.warning(f"Doc button click failed: {e}")

        # Wait for "Share a document" modal to appear
        logger.info("Waiting for 'Share a document' modal...")
        try:
            page.wait_for_selector(
                'text="Share a document", text="Choose file"',
                timeout=10_000, state='visible'
            )
        except PlaywrightTimeout:
            pass
        page.wait_for_timeout(1_500)

        # ------------------------------------------------------------------
        # STEP 3: Find and click "Choose file" button to trigger file chooser.
        # CONFIRMED from Image 3: There is a large "Choose file" button
        # (full-width, outlined style) inside the "Share a document" modal.
        # ------------------------------------------------------------------
        logger.info("Step 3: Finding 'Choose file' button in Share a document modal...")
        choose_file_btn = None
        choose_selectors = [
            'button:has-text("Choose file")',
            'button[aria-label="Choose file"]',
            'button:text-is("Choose file")',
            '[role="button"]:has-text("Choose file")',
            # Hidden file input that "Choose file" button wraps
            'input[type="file"]',
        ]
        for sel in choose_selectors:
            try:
                loc = page.locator(sel).first
                if loc.count() > 0:
                    choose_file_btn = loc
                    logger.info(f"Found 'Choose file' element: '{sel}'")
                    break
            except Exception:
                continue

        if choose_file_btn is None:
            self._save_debug_info(page, 'choose_file_button_not_found')
            raise RuntimeError(
                "Could not find 'Choose file' button in the 'Share a document' modal.\n"
                "Check debug screenshot."
            )

        # Intercept the file chooser triggered by "Choose file" button
        success = self._attach_file_via_chooser(page, choose_file_btn, document_path)

        if not success:
            # Fallback: directly set files on a hidden input
            logger.info("File chooser fallback: set_input_files on hidden input...")
            success = self._attach_file_via_hidden_input(page, document_path)

        if not success:
            self._save_debug_info(page, 'document_attach_failed')
            raise RuntimeError(
                f"Failed to attach document '{document_path}' — "
                "both file chooser and hidden input approaches failed."
            )

        # ------------------------------------------------------------------
        # STEP 4: Wait for upload to complete, then fill the REQUIRED title.
        # CONFIRMED from Image 2: "Document title *" is a required field.
        # The Done button won't work without a title.
        # ------------------------------------------------------------------
        logger.info("Step 4: Waiting for upload + filling required document title...")
        page.wait_for_timeout(2_500)  # let upload start rendering

        # Wait for title input to appear (signals upload is done / in progress)
        title_appeared = False
        for sel in [
            'input[placeholder*="descriptive title"]',
            'input[placeholder*="title" i]',
            'input[aria-label*="title" i]',
            'input[aria-label="Document title"]',
            'input[type="text"]',
        ]:
            try:
                page.wait_for_selector(sel, timeout=15_000, state='visible')
                logger.info(f"Title input appeared: '{sel}'")
                title_appeared = True

                # Fill the title with the filename (cleaned up)
                title = Path(document_path).stem.replace('_', ' ').replace('-', ' ').title()
                page.locator(sel).first.fill(title)
                logger.info(f"Filled document title: '{title}'")
                page.wait_for_timeout(500)
                break
            except PlaywrightTimeout:
                continue

        if not title_appeared:
            logger.warning("Title input not found — Done button may be disabled.")

        # ------------------------------------------------------------------
        # STEP 5: Wait for upload progress bar to finish, then click Done.
        # CONFIRMED from Image 2: Blue progress bar at bottom of file card.
        # Done button label is "Done" (not "Next").
        # ------------------------------------------------------------------
        logger.info("Step 5: Waiting for upload to finish then clicking Done...")
        # Wait for progress bar to disappear (upload complete)
        try:
            page.wait_for_selector(
                '[class*="progress"], [role="progressbar"]',
                state='hidden', timeout=60_000
            )
            logger.info("Upload progress bar gone — upload complete.")
        except PlaywrightTimeout:
            logger.warning("Progress bar timeout — proceeding to Done anyway.")

        page.wait_for_timeout(1_000)

        # Click Done button
        self._click_document_done_button(page)
        logger.info("Document attachment complete — returned to compose view.")

    def _click_toolbar_overflow(self, page: Page) -> None:
        """
        Click the [+] overflow button in the compose modal toolbar.

        CONFIRMED from screenshots: When the compose modal is at certain widths,
        LinkedIn hides extra toolbar items (including 'Add a document') behind
        a [+] button at the right end of the toolbar row.
        """
        logger.info("Clicking [+] toolbar overflow button...")
        overflow_selectors = [
            # The + button at the end of the toolbar
            'button[aria-label="More options"]',
            'button[aria-label="More"]',
            'button[aria-label="Show more options"]',
            # The + icon itself
            'button:has-text("+")',
            '[role="button"]:has-text("+")',
            # Generic overflow pattern
            '.share-creation-state__additional-toolbar button',
            'button[aria-label*="more" i]',
        ]
        for sel in overflow_selectors:
            try:
                btn = page.locator(sel).first
                if btn.count() > 0 and btn.is_visible():
                    btn.dispatch_event('click')
                    logger.info(f"Overflow [+] clicked: '{sel}'")
                    return
            except Exception:
                continue

        # JS fallback — find the + button by its visible text
        clicked = page.evaluate("""
            () => {
                for (const btn of document.querySelectorAll('button, [role="button"]')) {
                    const txt = (btn.innerText || btn.textContent || '').trim();
                    const label = btn.getAttribute('aria-label') || '';
                    if (txt === '+' || label.toLowerCase().includes('more')) {
                        btn.click();
                        return txt || label;
                    }
                }
                return null;
            }
        """)
        if clicked:
            logger.info(f"Overflow [+] clicked via JS: '{clicked}'")
        else:
            logger.warning("Could not find [+] overflow button — document button may already be visible.")

    def _wait_for_document_upload_complete(self, page: Page, timeout_s: int = 120) -> None:
        """
        Block until the document has fully uploaded and Done button is enabled.

        CONFIRMED FROM SCREENSHOT (document_done_all_attempts_failed_20260223_073905.png):
          The modal shows:
            - Document preview carousel fully loaded (67 pages shown)
            - Title field filled ("Pre Exam Practice")
            - Done button is BLUE and enabled
            - [Back] [Done] both visible at bottom

          BUT the old code was STUCK because:
            LinkedIn's document preview carousel has elements with "progress"
            in their class names (e.g. the page-count bar "67 pages" at the
            top of the preview image). The check for [class*="progress"] was
            matching these non-upload elements and blocking forever.

        FIX:
          ONLY check the Done button enabled state — that is the single
          reliable signal. When Done is blue and not disabled, upload is done.
          Do NOT check for progress bars — they cause false positives.
        """
        logger.info(f"Waiting up to {timeout_s}s for Done button to become enabled...")
        deadline = time.time() + timeout_s

        while time.time() < deadline:
            state = page.evaluate("""
                () => {
                    let doneEnabled = false;
                    let doneFound   = false;
                    for (const btn of document.querySelectorAll('button')) {
                        const txt = (btn.textContent || '').replace(/\\s+/g, ' ').trim();
                        const lbl = (btn.getAttribute('aria-label') || '').trim();
                        if (txt === 'Done' || lbl === 'Done') {
                            doneFound = true;
                            const isDisabled =
                                btn.disabled ||
                                btn.getAttribute('aria-disabled') === 'true' ||
                                btn.classList.contains('artdeco-button--disabled') ||
                                btn.classList.contains('artdeco-button--muted');
                            if (!isDisabled) doneEnabled = true;
                            break;
                        }
                    }
                    return { doneEnabled, doneFound };
                }
            """)

            de = state.get('doneEnabled', False)
            df = state.get('doneFound', False)

            logger.debug(f"Upload state — doneFound:{df} doneEnabled:{de}")

            if de:
                logger.info("Done button is enabled — waiting for full document preview to render...")
                # LinkedIn enables the Done button slightly before the full document
                # carousel has finished rendering all pages. Wait for the page-count
                # indicator (e.g. "67 pages") to appear — that confirms the complete
                # preview is loaded and it is safe to click Done.
                preview_ready = False
                for _ in range(15):  # up to 15 more seconds
                    ready = page.evaluate("""
                        () => {
                            // Page count label like "67 pages" appears when fully rendered
                            const allText = document.body.innerText || '';
                            const hasPageCount = /\\d+\\s+pages?/i.test(allText);

                            // Also check the preview image/canvas is visible
                            const previewImgs = document.querySelectorAll(
                                '.share-document-preview img, '  +
                                '[class*="document"] img, '      +
                                '[class*="document"] canvas'
                            );
                            const hasPreview = [...previewImgs].some(el => {
                                const r = el.getBoundingClientRect();
                                return r.width > 50 && r.height > 50;
                            });

                            return { hasPageCount, hasPreview };
                        }
                    """)
                    hp = ready.get('hasPageCount', False)
                    hprev = ready.get('hasPreview', False)
                    logger.debug(f"Preview ready check — pageCount:{hp} previewImg:{hprev}")
                    if hp or hprev:
                        logger.info("Document preview fully rendered — safe to click Done.")
                        preview_ready = True
                        break
                    page.wait_for_timeout(1_000)

                if not preview_ready:
                    logger.warning("Preview render check timed out — clicking Done anyway.")

                # One final small buffer for React to settle
                page.wait_for_timeout(1_500)
                return

            if not df:
                logger.debug("Done button not in DOM yet — waiting...")
            else:
                logger.debug("Done button found but still disabled — upload in progress...")

            page.wait_for_timeout(1_000)

        logger.warning(
            f"Document upload wait timed out after {timeout_s}s. "
            "Attempting Done click anyway."
        )

    def _click_document_done_button(self, page: Page) -> None:
        """
        Click the Done button in the 'Share a document' modal.

        CONFIRMED from screenshots (Image 2):
          - Modal title: "Share a document"
          - Bottom row: [Back] [Done]  — Done is blue/primary
          - Done button is at the BOTTOM-RIGHT of the modal
          - isTrusted=true required — use page.mouse.click() with real coords

        ROOT CAUSE of navigation bug:
          dispatchEvent produces isTrusted=false → LinkedIn ignores Done click
          → code falls through all strategies → times out or misclicks
          → browser interprets something as a link/navigation → feed scrolls

        FIX: page.mouse.click() at exact Done button coordinates is PRIMARY.
        Success is confirmed by checking the "Share a document" modal closes.
        If modal is still open after click → title may be empty or upload
        still running → wait and retry.
        """
        # ── WAIT FOR UPLOAD TO FULLY COMPLETE BEFORE DOING ANYTHING ──────────
        # The progress bar at the bottom of the file card must disappear AND
        # the Done button must become enabled (blue, not greyed out).
        # Clicking too early = Done is disabled = click is silently ignored.
        logger.info("Waiting for document upload to complete before clicking Done...")
        self._wait_for_document_upload_complete(page)
        # ─────────────────────────────────────────────────────────────────────

        logger.info("Clicking Done in 'Share a document' modal (real mouse click)...")
        page.wait_for_timeout(500)

        def share_modal_open() -> bool:
            """True if the Share a document modal is still visible."""
            try:
                page.wait_for_selector(
                    'text="Share a document"', timeout=2_000, state='visible'
                )
                return True
            except PlaywrightTimeout:
                return False

        def get_done_coords():
            """Return pixel coords of enabled Done button, or None."""
            return page.evaluate("""
                () => {
                    // Only match exact 'Done' — not 'Back', 'Cancel', etc.
                    for (const btn of document.querySelectorAll('button')) {
                        if (btn.disabled || btn.getAttribute('aria-disabled') === 'true')
                            continue;
                        const txt = (btn.textContent || '').replace(/\\s+/g, ' ').trim();
                        const lbl = (btn.getAttribute('aria-label') || '').trim();
                        if (txt === 'Done' || lbl === 'Done') {
                            const r = btn.getBoundingClientRect();
                            if (r.width > 0 && r.height > 0)
                                return { x: r.left + r.width/2, y: r.top + r.height/2,
                                         w: r.width, h: r.height };
                        }
                    }
                    return null;
                }
            """)

        # Retry loop: try up to 10 times over 30s
        # Needed because Done may be greyed out while upload is still in progress
        for attempt in range(10):
            coords = get_done_coords()
            if not coords:
                logger.warning(f"Attempt {attempt+1}: Done button not found in DOM.")
                page.wait_for_timeout(2_000)
                continue

            x, y = coords['x'], coords['y']
            logger.info(f"Attempt {attempt+1}: Real mouse.click on Done at ({x:.0f},{y:.0f})")

            # Move then click — more human-like, avoids some bot detection
            page.mouse.move(x, y)
            page.wait_for_timeout(150)
            page.mouse.click(x, y)
            page.wait_for_timeout(2_000)

            # Confirm the Share a document modal closed
            if not share_modal_open():
                logger.info("Done confirmed — 'Share a document' modal closed.")
                page.wait_for_timeout(1_500)  # let compose modal re-render
                return

            logger.warning(f"Attempt {attempt+1}: Modal still open after Done click — "
                           "may be upload still running or title empty. Waiting 3s...")
            page.wait_for_timeout(3_000)

        # All attempts failed — take debug screenshot
        self._save_debug_info(page, 'document_done_all_attempts_failed')
        raise RuntimeError(
            "Done button in 'Share a document' modal could not be confirmed after 10 attempts.\n"
            "Possible causes:\n"
            "  - Document title field is empty (it is REQUIRED — marked with *)\n"
            "  - Upload/processing still in progress\n"
            "  - Done button not found in DOM\n"
            "Check debug screenshot in Logs/linkedin_posts/."
        )
    def _fill_document_title_if_present(self, page: Page, document_path: str) -> None:
        """Legacy helper — kept for backward compat. Logic moved into _attach_document."""
        pass

    def _append_link_url(self, page: Page, editor_sel: str, link_url: str) -> None:
        """
        Append a link URL to the post text.
        MUST happen BEFORE any media is attached — LinkedIn resets the
        text editor once media is added.
        """
        logger.info(f"Appending link URL: {link_url}")
        editor = page.locator(editor_sel).first
        editor.click()
        page.keyboard.press('End')
        page.wait_for_timeout(200)
        page.keyboard.type(f"\n\n{link_url}", delay=30)
        page.wait_for_timeout(4_000)

    def _click_post_button(self, page: Page) -> None:
        """
        Click the final Post submit button and VERIFY the post was actually submitted.

        ROOT CAUSE OF SILENT FAILURE:
          LinkedIn's React onClick handler for the Post button IGNORES synthetic
          events (dispatchEvent, btn.click() from JS). It only responds to a real
          trusted mouse event (isTrusted=true) which only page.mouse.click() at
          real viewport coordinates produces. All previous strategies used
          dispatchEvent/force-click which LinkedIn silently drops — the button
          is "clicked" in the DOM but nothing happens on LinkedIn's side.

        STRATEGY ORDER (primary = coordinate click, others = fallbacks):
          0. Wait for all overlays/backdrops to clear
          1. PRIMARY: Get exact button coordinates → page.mouse.click(x, y)
             This produces isTrusted=true events that LinkedIn accepts
          2. Playwright .click() without force — normal trusted click
          3. Playwright .click() with force=True — bypasses visibility check
          4. Tab+Enter keyboard navigation — keyboard events are trusted too

        SUCCESS VALIDATION:
          After each attempt, wait for the compose modal to disappear.
          The modal closing is the only reliable confirmation that LinkedIn
          accepted the post submission. If it doesn't close → try next strategy.
          After all strategies, if modal still open → raise RuntimeError.
          Never mark a post as 'posted' if modal is still visible.
        """
        logger.info("Preparing to click Post button...")

        # ----------------------------------------------------------------
        # Step 0: Wait for ALL overlays to fully clear.
        # After document/image Done button, LinkedIn animates modals out.
        # Clicking Post while backdrop is still present causes silent failure.
        # ----------------------------------------------------------------
        logger.info("Step 0: Waiting for all overlays to clear...")
        for overlay_sel in [
            '.artdeco-modal:not([aria-label="Share a post"])',
            '.artdeco-modal-overlay',
            '[class*="share-creation"][class*="overlay"]',
        ]:
            try:
                page.wait_for_selector(overlay_sel, state='hidden', timeout=6_000)
            except PlaywrightTimeout:
                pass
        page.wait_for_timeout(2_000)  # React animation buffer

        MATCH_TEXT  = {'Post', 'Post now', 'Share now'}
        EXCLUDE_SUB = {'hide post', 'repost', 'copy link', 'report', 'edit',
                       'delete', 'remove', 'undo', 'anyone', 'connections',
                       'back', 'cancel', 'done', 'next'}

        def modal_still_open() -> bool:
            """Return True if the compose modal is still on screen."""
            try:
                page.wait_for_selector(
                    '[role="dialog"], [aria-modal="true"]',
                    state='visible', timeout=2_000
                )
                return True
            except PlaywrightTimeout:
                return False

        def wait_for_modal_close(timeout_ms: int = 10_000) -> bool:
            """Return True if compose modal closes within timeout."""
            try:
                page.wait_for_selector(
                    '[role="dialog"], [aria-modal="true"]',
                    state='hidden', timeout=timeout_ms
                )
                return True
            except PlaywrightTimeout:
                return False

        def find_post_btn_coords() -> Optional[Dict]:
            """Return {x, y, w, h, text, label} for the enabled Post button, or None."""
            return page.evaluate("""
                () => {
                    const MATCH   = ['Post', 'Post now', 'Share now'];
                    const EXCLUDE = ['hide post', 'repost', 'copy link', 'report',
                                     'edit', 'delete', 'remove', 'undo', 'anyone',
                                     'connections', 'back', 'cancel', 'done', 'next'];
                    // Search compose modal first, then full page
                    const scopes = [
                        document.querySelector('[role="dialog"]'),
                        document.querySelector('[aria-modal="true"]'),
                        document.body,
                    ];
                    for (const scope of scopes) {
                        if (!scope) continue;
                        for (const btn of scope.querySelectorAll('button, [role="button"]')) {
                            if (btn.disabled || btn.getAttribute('aria-disabled') === 'true')
                                continue;
                            const text  = (btn.textContent || '').replace(/\\s+/g, ' ').trim();
                            const label = (btn.getAttribute('aria-label') || '').trim();
                            const tl    = text.toLowerCase();
                            if (EXCLUDE.some(e => tl.includes(e))) continue;
                            if (!MATCH.includes(text) && !MATCH.includes(label)) continue;
                            const r = btn.getBoundingClientRect();
                            if (r.width < 1 || r.height < 1) continue;
                            return {
                                x: r.left + r.width  / 2,
                                y: r.top  + r.height / 2,
                                w: r.width, h: r.height,
                                text: text, label: label,
                            };
                        }
                    }
                    return null;
                }
            """)

        # ----------------------------------------------------------------
        # Strategy 1 (PRIMARY): page.mouse.click() at real coordinates.
        # Produces isTrusted=true events — LinkedIn React handler accepts these.
        # dispatchEvent/btn.click() produce isTrusted=false → silently ignored.
        # ----------------------------------------------------------------
        logger.info("Strategy 1 (PRIMARY): Real mouse coordinate click on Post button...")
        coords = find_post_btn_coords()
        if coords:
            x, y = coords['x'], coords['y']
            logger.info(f"Post button found at ({x:.0f}, {y:.0f}) "
                        f"text='{coords['text']}' size={coords['w']:.0f}x{coords['h']:.0f}")
            # Move mouse to button first (more human-like, avoids some bot detection)
            page.mouse.move(x, y)
            page.wait_for_timeout(200)
            page.mouse.click(x, y)
            logger.info("Strategy 1: mouse.click() fired.")
            page.wait_for_timeout(2_000)
            if wait_for_modal_close(10_000):
                logger.info("SUCCESS: Modal closed after Strategy 1 coordinate click.")
                return
            logger.warning("Strategy 1: modal still open — Post button click not accepted.")
        else:
            logger.warning("Strategy 1: Post button not found in DOM.")

        # ----------------------------------------------------------------
        # Strategy 2: Playwright locator .click() (normal, not force).
        # Playwright's built-in .click() is trusted — it uses CDP input events.
        # ----------------------------------------------------------------
        logger.info("Strategy 2: Playwright locator .click() (trusted CDP events)...")
        locator_candidates = [
            page.locator('button[aria-label="Post"]'),
            page.locator('button[aria-label="Post now"]'),
            page.locator('button[data-control-name="share.post"]'),
            page.get_by_role('button', name='Post', exact=True),
            page.get_by_role('button', name='Post now', exact=True),
            page.locator('button:has(span.artdeco-button__text:text-is("Post"))'),
            page.locator('button:has(span.artdeco-button__text:text-is("Post now"))'),
            page.locator('button:has(span:text-is("Post"))'),
        ]
        EXCLUDE_SET = {'hide post', 'repost', 'copy link to post', 'report post',
                       'edit post', 'delete post', 'undo', 'back', 'done', 'next'}
        for candidate in locator_candidates:
            try:
                if candidate.count() == 0:
                    continue
                btn = candidate.first
                btn_text = (btn.inner_text() or '').strip().lower()
                if any(ex in btn_text for ex in EXCLUDE_SET):
                    continue
                # Normal click first (trusted)
                btn.click(timeout=5_000)
                logger.info(f"Strategy 2: .click() on '{btn_text}'")
                page.wait_for_timeout(2_000)
                if wait_for_modal_close(10_000):
                    logger.info("SUCCESS: Modal closed after Strategy 2.")
                    return
            except Exception as e:
                logger.debug(f"Strategy 2 candidate failed: {e}")

        # ----------------------------------------------------------------
        # Strategy 3: force=True click — bypasses Playwright visibility check.
        # Use when button is technically off-screen or clipped.
        # ----------------------------------------------------------------
        logger.info("Strategy 3: Playwright force=True click...")
        for candidate in locator_candidates:
            try:
                if candidate.count() == 0:
                    continue
                btn = candidate.first
                btn_text = (btn.inner_text() or '').strip().lower()
                if any(ex in btn_text for ex in EXCLUDE_SET):
                    continue
                btn.click(force=True, timeout=5_000)
                logger.info(f"Strategy 3: force .click() on '{btn_text}'")
                page.wait_for_timeout(2_000)
                if wait_for_modal_close(10_000):
                    logger.info("SUCCESS: Modal closed after Strategy 3 force click.")
                    return
            except Exception as e:
                logger.debug(f"Strategy 3 candidate failed: {e}")

        # ----------------------------------------------------------------
        # Strategy 4: Tab+Enter keyboard navigation.
        # Keyboard events are trusted (isTrusted=true).
        # Click the compose modal area first to ensure focus is inside it.
        # ----------------------------------------------------------------
        logger.info("Strategy 4: Tab+Enter keyboard navigation to Post button...")
        try:
            # Click in the middle of the compose modal to focus it
            modal_center = page.evaluate("""
                () => {
                    const m = document.querySelector('[role="dialog"]') ||
                              document.querySelector('[aria-modal="true"]');
                    if (!m) return null;
                    const r = m.getBoundingClientRect();
                    return { x: r.left + r.width/2, y: r.top + r.height/2 };
                }
            """)
            if modal_center:
                page.mouse.click(modal_center['x'], modal_center['y'])
                page.wait_for_timeout(300)

            for _ in range(25):
                page.keyboard.press('Tab')
                page.wait_for_timeout(120)
                focused = page.evaluate("""
                    () => {
                        const el = document.activeElement;
                        if (!el) return '';
                        return (el.textContent || el.getAttribute('aria-label') || '')
                               .replace(/\\s+/g, ' ').trim();
                    }
                """)
                logger.debug(f"Tab focused: '{focused}'")
                if focused in ('Post', 'Post now', 'Share now'):
                    page.keyboard.press('Enter')
                    logger.info(f"Strategy 4: Tab+Enter on '{focused}'")
                    page.wait_for_timeout(2_000)
                    if wait_for_modal_close(10_000):
                        logger.info("SUCCESS: Modal closed after Strategy 4 Tab+Enter.")
                        return
        except Exception as e:
            logger.warning(f"Strategy 4 failed: {e}")

        # ----------------------------------------------------------------
        # All strategies exhausted — take debug screenshot and RAISE.
        # The caller (post_to_linkedin) must NOT mark this as 'posted'.
        # ----------------------------------------------------------------
        all_buttons = page.evaluate("""
            () => [...document.querySelectorAll('button, [role="button"]')].map(b => ({
                text:     (b.textContent || '').replace(/\\s+/g, ' ').trim().slice(0, 60),
                label:    b.getAttribute('aria-label'),
                disabled: b.disabled,
                ariaDisabled: b.getAttribute('aria-disabled'),
                rect: (() => {
                    const r = b.getBoundingClientRect();
                    return {x:Math.round(r.x), y:Math.round(r.y),
                            w:Math.round(r.width), h:Math.round(r.height)};
                })(),
            }))
        """)
        logger.error(f"All Post strategies failed. Buttons on page:\n"
                     f"{json.dumps(all_buttons, indent=2)}")
        self._save_debug_info(page, 'post_button_all_strategies_failed')
        raise RuntimeError(
            "Post button was not accepted by LinkedIn after 4 strategies.\n"
            "The compose modal is still open — post was NOT submitted.\n"
            f"Buttons found: {[b['text'] for b in all_buttons if b['text']]}\n"
            "Check screenshot in Logs/linkedin_posts/."
        )


    # ------------------------------------------------------------------
    # Debug helpers
    # ------------------------------------------------------------------

    def _wait_for_post_processing(
        self, page: Page, has_document: bool = False, has_media: bool = False
    ) -> None:
        """
        After clicking Post, keep the browser open on the LinkedIn feed until
        the post has fully processed.

        WHY THIS MATTERS FOR DOCUMENTS:
          After the Post button is clicked, LinkedIn returns to the feed and
          shows a toast notification with a progress bar while it:
            - Converts the PDF pages to images
            - Generates the document carousel preview
            - Indexes the content
          Closing the browser before this finishes can leave the post in a
          broken state (missing preview, draft-only, or silently discarded).

        OBSERVED BEHAVIOUR (from user screenshots):
          - Compose modal closes → feed is visible
          - A toast/snackbar appears at the bottom of the feed showing
            "Your document post is being processed" or similar
          - Progress bar fills, then the toast disappears
          - Post then appears in the feed normally

        WAIT STRATEGY:
          1. Short base wait (all post types) — let LinkedIn navigate back to feed
          2. Wait for any processing toast/snackbar to appear (document/media)
          3. Wait for the toast to disappear (processing complete)
          4. Extra buffer for document posts (they take longer than images)
          5. Hard maximum of 120s for documents, 30s for media, 10s for text
        """
        # Base wait — let modal animation finish and feed load
        page.wait_for_timeout(2_000)

        # Maximum processing times by post type
        max_wait = 120_000 if has_document else (30_000 if has_media else 10_000)
        logger.info(
            f"Waiting up to {max_wait//1000}s for post processing "
            f"(document={has_document}, media={has_media})..."
        )

        if not has_document and not has_media:
            # Text-only posts — just a short buffer, no processing needed
            page.wait_for_timeout(3_000)
            logger.info("Text post — no processing wait needed.")
            return

        # Selectors that indicate LinkedIn is actively processing the post
        processing_selectors = [
            # Toast / snackbar notifications LinkedIn shows during processing
            '.artdeco-toast-item',
            '.artdeco-snackbar',
            '[data-test-toast]',
            '[class*="toast"]',
            '[class*="snackbar"]',
            '[class*="notification"][class*="post"]',
            # Progress indicators
            '[role="progressbar"]',
            '[class*="progress"]',
            # LinkedIn's specific document processing message
            'text="Your post is being processed"',
            'text="Processing"',
            'text="Uploading"',
        ]

        # Step 1: Wait for a processing toast to appear (up to 15s)
        toast_appeared = False
        logger.info("Watching for processing toast/progress indicator...")
        toast_deadline = time.time() + 15
        while time.time() < toast_deadline:
            for sel in processing_selectors:
                try:
                    page.wait_for_selector(sel, timeout=1_000, state='visible')
                    logger.info(f"Processing toast detected: '{sel}'")
                    toast_appeared = True
                    break
                except PlaywrightTimeout:
                    continue
            if toast_appeared:
                break
            page.wait_for_timeout(500)

        if not toast_appeared:
            logger.info("No processing toast appeared — post may have processed instantly.")
            # Still wait a minimum buffer
            min_wait = 8_000 if has_document else 4_000
            page.wait_for_timeout(min_wait)
            return

        # Step 2: Wait for the toast to disappear (processing done)
        logger.info("Waiting for processing toast to disappear (= processing complete)...")
        processing_done = False
        done_deadline = time.time() + (max_wait / 1000)
        while time.time() < done_deadline:
            any_visible = False
            for sel in processing_selectors:
                try:
                    page.wait_for_selector(sel, timeout=1_000, state='visible')
                    any_visible = True
                    break
                except PlaywrightTimeout:
                    continue
            if not any_visible:
                processing_done = True
                logger.info("Processing toast gone — post processing complete.")
                break
            page.wait_for_timeout(1_000)

        if not processing_done:
            logger.warning(
                f"Processing toast still visible after {max_wait//1000}s. "
                "LinkedIn may still be processing — post was submitted but "
                "processing may complete after browser closes."
            )

        # Step 3: Final buffer — give LinkedIn servers time to commit
        final_buffer = 5_000 if has_document else 2_000
        logger.info(f"Final processing buffer: {final_buffer}ms")
        page.wait_for_timeout(final_buffer)
        logger.info("Post processing wait complete.")

    def _save_debug_info(self, page: Page, prefix: str) -> None:
        try:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            log_dir = self.vault_path / 'Logs' / 'linkedin_posts'
            html_path = log_dir / f'{prefix}_{timestamp}.html'
            html_path.write_text(page.content(), encoding='utf-8')
            logger.error(f"Debug HTML saved: {html_path}")
            try:
                ss_path = log_dir / f'{prefix}_{timestamp}.png'
                page.screenshot(path=str(ss_path), timeout=5_000)
                logger.error(f"Screenshot saved: {ss_path}")
            except Exception as e:
                logger.error(f"Screenshot failed: {e}")
        except Exception as e:
            logger.error(f"Could not save debug info: {e}")

    def _handle_post_failure(self, post_id: str, error_message: str) -> None:
        try:
            post = self.db.get_linkedin_post(post_id)
            status = 'failed'
            msg = error_message
            if post and post['retry_count'] >= post['max_retries']:
                msg = f'{error_message} (max retries exceeded)'
            self.db.update_linkedin_post(post_id, {'status': status, 'error_message': msg})
            self.db.log_activity({
                'level': 'ERROR',
                'component': 'linkedin-poster',
                'action': f'Post failed: {post_id}',
                'details': msg,
            })
        except Exception as e:
            logger.error(f"Error handling post failure: {e}")

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def create_post(self, content, importance_level='normal', media_paths=None,
                    link_url=None, document_path=None, scheduled_time=None, smart_schedule=False):
        if not content or not content.strip():
            raise ValueError("Content cannot be empty")
        if len(content) > self.MAX_CONTENT_LENGTH:
            raise ValueError(f"Content exceeds {self.MAX_CONTENT_LENGTH} characters")
        if importance_level not in self.IMPORTANCE_LEVELS:
            raise ValueError(f"Invalid importance level: {importance_level}")
        if media_paths and document_path:
            raise ValueError("LinkedIn does not allow both images and a document in the same post.")
        if media_paths:
            for path in media_paths:
                if not Path(path).exists():
                    raise ValueError(f"Media file not found: {path}")
        if document_path and not Path(document_path).exists():
            raise ValueError(f"Document file not found: {document_path}")

        post_id = str(uuid4())
        if smart_schedule:
            scheduled_time = self._calculate_optimal_time()
        elif scheduled_time is None:
            scheduled_time = datetime.now()

        needs_approval = importance_level in self.APPROVAL_REQUIRED
        status = 'pending' if needs_approval else 'approved'
        approval_id = None
        if needs_approval:
            approval_id = self._create_approval_request(post_id, content, importance_level)

        post_data = {
            'id': post_id,
            'content': content,
            'media_paths': json.dumps(media_paths) if media_paths else None,
            'link_url': link_url,
            'document_path': document_path,
            'scheduled_time': scheduled_time.isoformat(),
            'status': status,
            'importance_level': importance_level,
            'approval_id': approval_id,
            'retry_count': 0,
            'max_retries': self.config['max_retries'],
        }

        if not self.db.create_linkedin_post(post_data):
            raise RuntimeError("Failed to create post in database")

        self.db.log_activity({
            'level': 'INFO',
            'component': 'linkedin-poster',
            'action': f'Post created: {post_id}',
            'details': f'Importance: {importance_level}, Status: {status}',
        })
        logger.info(f"Created LinkedIn post {post_id} with status {status}")
        return post_id

    def _calculate_optimal_time(self):
        now = datetime.now()
        target = now
        if target.weekday() in self.OPTIMAL_DAYS and target.hour in self.OPTIMAL_HOURS:
            return target + timedelta(minutes=5)
        if target.weekday() in self.OPTIMAL_DAYS and target.hour < 9:
            return target.replace(hour=9, minute=0, second=0, microsecond=0)
        target = (target + timedelta(days=1)).replace(hour=9, minute=0, second=0, microsecond=0)
        while target.weekday() >= 5:
            target += timedelta(days=1)
        return target

    def _create_approval_request(self, post_id, content, importance_level):
        approval_id = str(uuid4())
        deadline = datetime.now() + timedelta(hours=24)
        self.db.create_approval({
            'id': approval_id,
            'item_id': post_id,
            'requested_at': datetime.now().isoformat(),
            'deadline': deadline.isoformat(),
            'reason': f'LinkedIn post with {importance_level} importance requires approval',
        })
        self._generate_approval_card(post_id, approval_id, content, importance_level, deadline)
        logger.info(f"Created approval request {approval_id} for post {post_id}")
        return approval_id

    def _generate_approval_card(self, post_id, approval_id, content, importance_level, deadline):
        card = f"""# LINKEDIN POST APPROVAL REQUIRED

**Approval ID:** {approval_id}
**Post ID:** {post_id}
**Importance Level:** {importance_level.upper()}
**Created:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
**Deadline:** {deadline.strftime('%Y-%m-%d %H:%M:%S')}

---

## Post Content

{content}

---

## How to Approve

### Option 1: Via CLI
```bash
python -m src.skills.linkedin_poster approve {post_id}
python -m src.skills.linkedin_poster reject {post_id} --reason "Your reason here"
```

### Option 2: Via Obsidian
- **Approve:** Move this file to `Approved/linkedin_posts/` folder
- **Reject:** Delete this file

*Generated by LinkedIn Poster Skill*
"""
        filename = f"{datetime.now().strftime('%Y-%m-%d-%H%M')}_{approval_id}_linkedin_post.md"
        (self.vault_path / 'Pending_Approval' / 'linkedin_posts' / filename).write_text(card)

    def approve_post(self, post_id):
        try:
            post = self.db.get_linkedin_post(post_id)
            if not post:
                return {'success': False, 'error': f'Post not found: {post_id}'}
            if post['status'] != 'pending':
                return {'success': False, 'error': f'Post not pending (status: {post["status"]})'}
            self.db.update_linkedin_post(post_id, {'status': 'approved'})
            if post['approval_id']:
                self.db.update_approval(post['approval_id'], {
                    'decision': 'approved',
                    'decided_at': datetime.now().isoformat(),
                })
            self.db.log_activity({
                'level': 'INFO', 'component': 'linkedin-poster',
                'action': f'Post approved: {post_id}',
                'details': f'Importance: {post["importance_level"]}',
            })
            return {'success': True, 'post_id': post_id}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def reject_post(self, post_id, reason="No reason provided"):
        try:
            post = self.db.get_linkedin_post(post_id)
            if not post:
                return {'success': False, 'error': f'Post not found: {post_id}'}
            if post['status'] != 'pending':
                return {'success': False, 'error': f'Post not pending (status: {post["status"]})'}
            self.db.update_linkedin_post(post_id, {'status': 'rejected', 'error_message': f'Rejected: {reason}'})
            if post['approval_id']:
                self.db.update_approval(post['approval_id'], {
                    'decision': 'rejected',
                    'decided_at': datetime.now().isoformat(),
                    'reason': reason,
                })
            self.db.log_activity({
                'level': 'INFO', 'component': 'linkedin-poster',
                'action': f'Post rejected: {post_id}',
                'details': reason,
            })
            return {'success': True, 'post_id': post_id}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    def check_rate_limit(self):
        try:
            with self.db._get_connection() as conn:
                cursor = conn.execute("""
                    SELECT COUNT(*) FROM linkedin_posts
                    WHERE status IN ('posted', 'posting')
                    AND posted_time IS NOT NULL
                    AND date(posted_time) = date('now')
                """)
                count = cursor.fetchone()[0]
            return count < self.MAX_DAILY_POSTS
        except Exception as e:
            logger.error(f"Error checking rate limit: {e}")
            return False

    def retry_post(self, post_id):
        try:
            post = self.db.get_linkedin_post(post_id)
            if not post:
                return {'success': False, 'error': f'Post not found: {post_id}'}
            if post['status'] != 'failed':
                return {'success': False, 'error': f'Post is not failed (status: {post["status"]})'}
            if post['retry_count'] >= post['max_retries']:
                return {'success': False, 'error': f'Max retries ({post["max_retries"]}) exceeded'}
            self.db.update_linkedin_post(post_id, {
                'status': 'approved',
                'retry_count': post['retry_count'] + 1,
                'error_message': None,
            })
            return {'success': True, 'post_id': post_id, 'retry_count': post['retry_count'] + 1}
        except Exception as e:
            return {'success': False, 'error': str(e)}

    # ------------------------------------------------------------------
    # Core posting method
    # ------------------------------------------------------------------

    def post_to_linkedin(self, post_id: str) -> Dict[str, Any]:
        """
        Execute a LinkedIn post end-to-end using Playwright.

        Operation order (do not reorder):
          1. Open share modal
          2. Find editor
          3. Type text content
          4. Append link URL (must be BEFORE media — LinkedIn resets editor on media attach)
          5. Attach media images (if any) — includes Done button click after upload
          6. Attach document (if any, mutually exclusive with media) — includes Done button click
          7. Click Post button
        """
        try:
            post = self.db.get_linkedin_post(post_id)
            if not post:
                return {'success': False, 'error': f'Post not found: {post_id}'}
            if post['status'] != 'approved':
                return {'success': False, 'error': f'Post not approved (status: {post["status"]})'}
            if not self.check_rate_limit():
                return {'success': False, 'error': f'Daily rate limit ({self.MAX_DAILY_POSTS}) exceeded'}

            media_paths = json.loads(post['media_paths']) if post['media_paths'] else []

            with sync_playwright() as p:
                context = self._get_persistent_context(p)
                try:
                    page = self._ensure_logged_in(context)

                    # STEP 1: Open share modal
                    self._open_share_modal(page)

                    # STEP 2: Find editor
                    editor_sel = self._find_editor(page)

                    # STEP 3: Type content
                    logger.info("Typing content...")
                    self._type_content(page, editor_sel, post['content'])

                    # STEP 4: Append link URL BEFORE any media attachment
                    if post['link_url']:
                        self._append_link_url(page, editor_sel, post['link_url'])

                    # STEP 5: Attach images (includes wait for preview + Done click)
                    if media_paths:
                        self._attach_media(page, media_paths)

                    # STEP 6: Attach document — mutually exclusive with media
                    if post['document_path'] and not media_paths:
                        self._attach_document(page, post['document_path'])

                    # STEP 7: Click Post — raises RuntimeError if all strategies fail
                    logger.info("Submitting post...")
                    self._click_post_button(page)

                    # STEP 8: Keep browser open and wait for LinkedIn to finish
                    # processing. Documents especially show a toast/progress on
                    # the feed while LinkedIn converts pages — closing early = broken post.
                    logger.info("Post submitted — waiting for processing to complete...")
                    self._wait_for_post_processing(
                        page,
                        has_document=bool(post['document_path']),
                        has_media=bool(media_paths),
                    )

                    self.db.update_linkedin_post(post_id, {
                        'status': 'posted',
                        'posted_time': datetime.now().isoformat(),
                    })
                    self.db.log_activity({
                        'level': 'INFO',
                        'component': 'linkedin-poster',
                        'action': f'Post published: {post_id}',
                        'details': f'Content length: {len(post["content"])} chars',
                    })
                    logger.info(f"Successfully posted to LinkedIn: {post_id}")
                    return {'success': True, 'post_id': post_id}

                finally:
                    context.close()

        except PlaywrightTimeout as e:
            error_msg = f'Timeout while posting: {e}'
            logger.error(error_msg)
            self._handle_post_failure(post_id, error_msg)
            return {'success': False, 'error': error_msg}
        except Exception as e:
            error_msg = f'Error posting to LinkedIn: {e}'
            logger.error(error_msg)
            self._handle_post_failure(post_id, error_msg)
            return {'success': False, 'error': error_msg}

    # ------------------------------------------------------------------
    # Session helpers (kept for backward compat)
    # ------------------------------------------------------------------

    def is_session_valid(self):
        """Always True when using persistent context — Chromium manages expiry."""
        return True

    def save_session(self): return True
    def load_session(self): return True
    def authenticate(self): return True