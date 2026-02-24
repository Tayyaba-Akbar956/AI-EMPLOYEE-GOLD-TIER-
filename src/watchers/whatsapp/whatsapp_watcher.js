/**
 * WhatsApp Watcher for AI Employee Silver Tier
 *
 * Monitors WhatsApp messages and forwards important ones to Python processor.
 * Uses whatsapp-web.js for WhatsApp Web protocol integration.
 */

const { Client, LocalAuth } = require('whatsapp-web.js');
const qrcode = require('qrcode-terminal');
const fs = require('fs');
const path = require('path');
const { spawn } = require('child_process');

// Configuration
const VAULT_PATH = path.join(__dirname, '../../../AI_Employee_Vault');
const INBOX_PATH = path.join(VAULT_PATH, 'Inbox/whatsapp');
const PYTHON_PROCESSOR = path.join(__dirname, '../../processors/whatsapp_processor.py');

// Urgent keywords for filtering
const URGENT_KEYWORDS = [
    'urgent', 'asap', 'emergency', 'immediately', 'critical',
    'invoice', 'payment', 'due', 'overdue', 'deadline'
];

// Business keywords
const BUSINESS_KEYWORDS = [
    'invoice', 'receipt', 'contract', 'payment', 'proposal',
    'quote', 'order', 'delivery', 'meeting', 'project'
];

// Ensure inbox directory exists
if (!fs.existsSync(INBOX_PATH)) {
    fs.mkdirSync(INBOX_PATH, { recursive: true });
}

// Initialize WhatsApp client with Windows-compatible settings
const client = new Client({
    authStrategy: new LocalAuth({
        dataPath: './.wwebjs_auth'
    }),
    puppeteer: {
        headless: true,
        timeout: 60000, // Increase timeout to 60 seconds
        args: [
            '--no-sandbox',
            '--disable-setuid-sandbox',
            '--disable-dev-shm-usage',
            '--disable-accelerated-2d-canvas',
            '--no-first-run',
            '--no-zygote',
            '--disable-gpu',
            '--disable-software-rasterizer',
            '--disable-extensions',
            '--disable-background-networking',
            '--disable-default-apps',
            '--disable-sync',
            '--disable-translate',
            '--hide-scrollbars',
            '--metrics-recording-only',
            '--mute-audio',
            '--no-default-browser-check',
            '--safebrowsing-disable-auto-update',
            '--disable-blink-features=AutomationControlled'
        ]
        // Let puppeteer download and use its own Chromium
        // This is more reliable than trying to find system Chrome
    }
});

// QR Code display (first time only)
client.on('qr', (qr) => {
    console.log('\n' + '='.repeat(60));
    console.log('WHATSAPP QR CODE AUTHENTICATION');
    console.log('='.repeat(60));
    console.log('\n📱 Scan this QR code with your WhatsApp app:\n');
    qrcode.generate(qr, { small: true });
    console.log('\nSteps:');
    console.log('1. Open WhatsApp on your phone');
    console.log('2. Tap Menu (⋮) or Settings');
    console.log('3. Tap "Linked Devices"');
    console.log('4. Tap "Link a Device"');
    console.log('5. Scan the QR code above');
    console.log('\n' + '='.repeat(60) + '\n');
});

// Ready event
client.on('ready', () => {
    console.log('\n' + '='.repeat(60));
    console.log('✅ WhatsApp watcher connected successfully!');
    console.log('👀 Monitoring for new messages...');
    console.log('📍 Inbox: ' + INBOX_PATH);
    console.log('='.repeat(60) + '\n');
});

// Authentication success
client.on('authenticated', () => {
    console.log('✅ WhatsApp authenticated');
});

// Authentication failure
client.on('auth_failure', (msg) => {
    console.error('❌ WhatsApp authentication failed:', msg);
    console.error('Try deleting .wwebjs_auth folder and restart');
});

// Disconnected
client.on('disconnected', (reason) => {
    console.log('⚠️  WhatsApp disconnected:', reason);
    console.log('🔄 Attempting to reconnect...');
});

// New message received
client.on('message', async (message) => {
    try {
        // Get message details
        const chat = await message.getChat();
        const contact = await message.getContact();

        // Filter criteria
        const shouldProcess = await checkIfImportant(message, chat, contact);

        if (shouldProcess) {
            console.log(`\n📱 New WhatsApp message from ${contact.pushname || contact.number}`);
            await processMessage(message, chat, contact);
        }
    } catch (error) {
        console.error('Error processing message:', error.message);
        logError(error, message);
    }
});

/**
 * Check if message is important enough to process
 */
async function checkIfImportant(message, chat, contact) {
    const body = message.body.toLowerCase();

    // Skip if no body
    if (!body || body.trim().length === 0) {
        return message.hasMedia; // Process if has media even without text
    }

    // Check for urgent keywords
    const hasUrgentKeyword = URGENT_KEYWORDS.some(keyword => body.includes(keyword));
    if (hasUrgentKeyword) {
        return true;
    }

    // Check for business keywords
    const hasBusinessKeyword = BUSINESS_KEYWORDS.some(keyword => body.includes(keyword));
    if (hasBusinessKeyword) {
        return true;
    }

    // For group messages, only process if mentioned
    if (chat.isGroup) {
        const isMentioned = message.mentionedIds &&
                           message.mentionedIds.includes(client.info.wid._serialized);
        return isMentioned;
    }

    // Process if has media attachment
    if (message.hasMedia) {
        return true;
    }

    // Skip casual short messages
    if (body.length < 20) {
        const casualPhrases = ['hey', 'hi', 'hello', 'ok', 'yes', 'no', 'thanks'];
        if (casualPhrases.some(phrase => body.includes(phrase))) {
            return false;
        }
    }

    // Default: don't process
    return false;
}

/**
 * Process important message
 */
async function processMessage(message, chat, contact) {
    const timestamp = new Date().toISOString();

    // Prepare message data
    const messageData = {
        from: contact.number,
        name: contact.pushname || contact.number,
        body: message.body,
        timestamp: timestamp,
        chat_type: chat.isGroup ? 'group' : 'direct',
        has_media: message.hasMedia
    };

    // Add group info if applicable
    if (chat.isGroup) {
        messageData.group_name = chat.name;
        messageData.mentioned = message.mentionedIds &&
                               message.mentionedIds.includes(client.info.wid._serialized);
    }

    // Handle media
    const mediaFiles = [];
    if (message.hasMedia) {
        try {
            console.log('  📎 Downloading media...');
            const media = await message.downloadMedia();

            const safeTimestamp = timestamp.replace(/:/g, '-').split('.')[0];
            const filename = media.filename || `media_${safeTimestamp}`;
            const mediaPath = path.join(INBOX_PATH, filename);

            // Save media file
            fs.writeFileSync(mediaPath, media.data, 'base64');

            messageData.media_type = media.mimetype;
            messageData.media_filename = filename;
            mediaFiles.push(filename);

            console.log(`  ✅ Media saved: ${filename}`);
        } catch (error) {
            console.error('  ❌ Error downloading media:', error.message);
        }
    }

    messageData.media_files = mediaFiles;

    // Call Python processor
    try {
        await callPythonProcessor(messageData);
        console.log('  ✅ Message processed successfully');
    } catch (error) {
        console.error('  ❌ Error calling Python processor:', error.message);

        // Fallback: save raw JSON
        const fallbackPath = path.join(INBOX_PATH, `fallback_${Date.now()}.json`);
        fs.writeFileSync(fallbackPath, JSON.stringify(messageData, null, 2));
        console.log(`  💾 Saved fallback data to: ${fallbackPath}`);
    }
}

/**
 * Call Python processor with message data
 */
function callPythonProcessor(messageData) {
    return new Promise((resolve, reject) => {
        // Fix Windows path escaping by using forward slashes
        const vaultPathEscaped = VAULT_PATH.replace(/\\/g, '/');
        const projectRootEscaped = path.join(__dirname, '../../..').replace(/\\/g, '/');

        const python = spawn('python', [
            '-c',
            `
import sys
import json
sys.path.insert(0, r'${projectRootEscaped}')
from src.processors.whatsapp_processor import WhatsAppProcessor

data = json.loads(sys.stdin.read())
processor = WhatsAppProcessor(r'${vaultPathEscaped}')
result = processor.process_message(data)
print(json.dumps(result))
            `
        ]);

        let output = '';
        let error = '';

        python.stdout.on('data', (data) => {
            output += data.toString();
        });

        python.stderr.on('data', (data) => {
            error += data.toString();
        });

        python.on('close', (code) => {
            if (code !== 0) {
                reject(new Error(`Python processor failed: ${error}`));
            } else {
                try {
                    const result = JSON.parse(output);
                    resolve(result);
                } catch (e) {
                    reject(new Error(`Failed to parse Python output: ${output}`));
                }
            }
        });

        // Send message data to Python
        python.stdin.write(JSON.stringify(messageData));
        python.stdin.end();
    });
}

/**
 * Log error to file
 */
function logError(error, message) {
    const logPath = path.join(VAULT_PATH, 'Logs', 'whatsapp_errors.log');
    const logDir = path.dirname(logPath);

    if (!fs.existsSync(logDir)) {
        fs.mkdirSync(logDir, { recursive: true });
    }

    const logEntry = `[${new Date().toISOString()}] ERROR: ${error.message}\n`;
    fs.appendFileSync(logPath, logEntry);
}

// Handle process termination
process.on('SIGINT', async () => {
    console.log('\n\n⚠️  Shutting down WhatsApp watcher...');
    await client.destroy();
    console.log('✅ WhatsApp watcher stopped');
    process.exit(0);
});

// Start the client
console.log('🚀 Starting WhatsApp watcher...');
client.initialize();
