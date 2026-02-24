# 📱 WhatsApp & 🔗 LinkedIn Setup Guide

This guide covers the one-time setup required for WhatsApp and LinkedIn integration in the AI Employee Silver Tier.

---

## 📱 WhatsApp Setup

The WhatsApp watcher uses `whatsapp-web.js` to monitor messages in real-time.

### 1. Install Node.js Dependencies
Navigate to the WhatsApp watcher directory and install the required packages:
```bash
cd src/watchers/whatsapp
npm install
```

### 2. Authentication
Start the watcher to trigger the QR code authentication:
```bash
npm start
```
1. Open WhatsApp on your phone.
2. Tap **Settings** > **Linked Devices**.
3. Tap **Link a Device** and scan the QR code shown in your terminal.

**Note:** The session is saved locally in `.wwebjs_auth/`. You won't need to scan the QR code again unless you log out.

---

## 🔗 LinkedIn Setup

The LinkedIn integration includes both a **Watcher** (for incoming opportunities) and a **Poster** (for autonomous sharing of text, images, and links. Document support coming in next tier).

### 1. Install Dependencies
Ensure Playwright and its browser binaries are installed:
```bash
pip install playwright
playwright install chromium
```

### 2. Configure Credentials
Add the following to your `.env` file in the project root:
```env
# LinkedIn Watcher (API Polling)
LINKEDIN_CLIENT_ID=your_client_id
LINKEDIN_CLIENT_SECRET=your_client_secret

# LinkedIn Poster (Browser Automation)
LINKEDIN_EMAIL=your.email@example.com
LINKEDIN_PASSWORD=your_secure_password
```

### 3. Initialize Poster Session
Trigger the first-time browser authentication by creating a test post:
```bash
python -m src.cli.linkedin_cli create "Initializing automation..." --importance low
```
A browser window will open (visible mode). Log in manually if prompted. The session will be saved in `AI_Employee_Vault/.linkedin_session/`.

---

## 🚀 Running the Watchers

### Using Shell Scripts (Recommended)
You can start both watchers (and others) using the provided scripts:
```bash
# Start all watchers
./scripts/start_all_watchers.sh

# Check watcher status
./scripts/check_watchers.sh
```

### Manual Start
```bash
# WhatsApp
cd src/watchers/whatsapp && npm start

# LinkedIn
python -m src.watchers.linkedin_watcher
```

---

## 🔧 Troubleshooting

- **WhatsApp QR missing:** Delete `src/watchers/whatsapp/.wwebjs_auth/` and restart.
- **LinkedIn Auth Failure:** Verify credentials in `.env` and delete `AI_Employee_Vault/.linkedin_session/` to reset.
- **Playwright Error:** Run `playwright install chromium` to ensure binaries are present.

*Detailed guides available in `docs/WATCHERS_GUIDE.md`, `linkedin/LINKEDIN_SETUP.md`, and `src/watchers/whatsapp/README.md`.*
