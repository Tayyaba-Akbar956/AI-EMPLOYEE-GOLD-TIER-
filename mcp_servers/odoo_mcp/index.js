#!/usr/bin/env node

/**
 * Odoo MCP Server - Gold Tier Feature 3
 * Exposes Odoo accounting tools via Model Context Protocol
 */

import { Server } from '@modelcontextprotocol/sdk/server/index.js';
import { StdioServerTransport } from '@modelcontextprotocol/sdk/server/stdio.js';
import { CallToolRequestSchema, ListToolsRequestSchema } from '@modelcontextprotocol/sdk/types.js';
import { spawn } from 'child_process';
import { fileURLToPath } from 'url';
import { dirname, join } from 'path';

const __filename = fileURLToPath(import.meta.url);
const __dirname = dirname(__filename);

// Create MCP server
const server = new Server(
  {
    name: 'odoo-mcp',
    version: '1.0.0',
  },
  {
    capabilities: {
      tools: {},
    },
  }
);

// Tool definitions
const TOOLS = [
  {
    name: 'get_invoices',
    description: 'List customer invoices by date range and status',
    inputSchema: {
      type: 'object',
      properties: {
        start_date: {
          type: 'string',
          description: 'Start date (YYYY-MM-DD)',
        },
        end_date: {
          type: 'string',
          description: 'End date (YYYY-MM-DD)',
        },
        status: {
          type: 'string',
          description: 'Invoice status (draft, posted, paid, all)',
          enum: ['draft', 'posted', 'paid', 'all'],
        },
      },
    },
  },
  {
    name: 'get_expenses',
    description: 'List business expenses by category and date range',
    inputSchema: {
      type: 'object',
      properties: {
        start_date: {
          type: 'string',
          description: 'Start date (YYYY-MM-DD)',
        },
        end_date: {
          type: 'string',
          description: 'End date (YYYY-MM-DD)',
        },
        category: {
          type: 'string',
          description: 'Expense category (optional)',
        },
      },
    },
  },
  {
    name: 'get_account_balance',
    description: 'Get current account balance from chart of accounts',
    inputSchema: {
      type: 'object',
      properties: {
        account_code: {
          type: 'string',
          description: 'Account code (e.g., 100000 for Bank)',
        },
      },
    },
  },
  {
    name: 'get_overdue_invoices',
    description: 'List all overdue customer invoices',
    inputSchema: {
      type: 'object',
      properties: {},
    },
  },
  {
    name: 'create_invoice',
    description: 'Create a new customer invoice (REQUIRES APPROVAL)',
    inputSchema: {
      type: 'object',
      properties: {
        partner_id: {
          type: 'number',
          description: 'Customer ID',
        },
        invoice_lines: {
          type: 'array',
          description: 'Invoice line items',
          items: {
            type: 'object',
            properties: {
              product_id: { type: 'number' },
              quantity: { type: 'number' },
              price_unit: { type: 'number' },
            },
          },
        },
      },
      required: ['partner_id', 'invoice_lines'],
    },
  },
  {
    name: 'create_expense',
    description: 'Log a business expense (no approval needed for draft)',
    inputSchema: {
      type: 'object',
      properties: {
        product_id: {
          type: 'number',
          description: 'Expense product/category ID',
        },
        amount: {
          type: 'number',
          description: 'Expense amount',
        },
        description: {
          type: 'string',
          description: 'Expense description',
        },
      },
      required: ['product_id', 'amount', 'description'],
    },
  },
  {
    name: 'post_journal_entry',
    description: 'Post an accounting journal entry (REQUIRES APPROVAL)',
    inputSchema: {
      type: 'object',
      properties: {
        journal_id: {
          type: 'number',
          description: 'Journal ID',
        },
        line_ids: {
          type: 'array',
          description: 'Journal entry lines',
          items: {
            type: 'object',
            properties: {
              account_id: { type: 'number' },
              debit: { type: 'number' },
              credit: { type: 'number' },
            },
          },
        },
      },
      required: ['journal_id', 'line_ids'],
    },
  },
];

// List tools handler
server.setRequestHandler(ListToolsRequestSchema, async () => {
  return {
    tools: TOOLS,
  };
});

// Call tool handler - delegates to Python odoo_client.py
server.setRequestHandler(CallToolRequestSchema, async (request) => {
  const { name, arguments: args } = request.params;

  try {
    // Call Python odoo_client.py via subprocess
    const pythonScript = join(__dirname, 'odoo_client.py');
    const result = await callPythonClient(pythonScript, name, args || {});

    return {
      content: [
        {
          type: 'text',
          text: result,
        },
      ],
    };
  } catch (error) {
    return {
      content: [
        {
          type: 'text',
          text: `Error calling Odoo: ${error.message}`,
        },
      ],
      isError: true,
    };
  }
});

/**
 * Call Python odoo_client.py via subprocess
 */
function callPythonClient(scriptPath, toolName, args) {
  return new Promise((resolve, reject) => {
    const python = spawn('python', [scriptPath, toolName, JSON.stringify(args)]);

    let stdout = '';
    let stderr = '';

    python.stdout.on('data', (data) => {
      stdout += data.toString();
    });

    python.stderr.on('data', (data) => {
      stderr += data.toString();
    });

    python.on('close', (code) => {
      if (code !== 0) {
        reject(new Error(`Python script exited with code ${code}: ${stderr}`));
      } else {
        resolve(stdout.trim());
      }
    });

    python.on('error', (err) => {
      reject(new Error(`Failed to start Python script: ${err.message}`));
    });
  });
}

// Start server
async function main() {
  const transport = new StdioServerTransport();
  await server.connect(transport);
  console.error('Odoo MCP server running on stdio');
}

main().catch((error) => {
  console.error('Server error:', error);
  process.exit(1);
});
