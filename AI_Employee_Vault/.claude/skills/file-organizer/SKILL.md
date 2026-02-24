---
name: file-organizer
description: Monitor and organize filesystem items into the vault. Use when Claude needs to detect new files, categorize by type and content (PDF, invoice, receipt, document), extract metadata, and move files to appropriate vault folders with markdown summaries.
---

# File Organizer Skill

Monitor and organize filesystem items. Detect new files in watched directories, categorize by type and content, extract metadata, and move to appropriate vault locations.

## Purpose

Automatically process files from monitored directories (like Downloads), categorize them intelligently, extract relevant metadata, and organize them into the AI_Employee_Vault with structured markdown summaries.

## Core Capabilities

### 1. File Type Detection
Identify file types and categories:
```python
import mimetypes
from pathlib import Path

def detect_file_type(file_path: Path) -> dict:
    """
    Detect file type and category.
    
    Args:
        file_path: Path to file
    
    Returns:
        Dictionary with type and category information
    """
    mime_type, _ = mimetypes.guess_type(str(file_path))
    extension = file_path.suffix.lower()
    
    type_map = {
        '.pdf': {'type': 'document', 'category': 'pdf', 'processable': True},
        '.docx': {'type': 'document', 'category': 'word', 'processable': True},
        '.doc': {'type': 'document', 'category': 'word', 'processable': False},
        '.xlsx': {'type': 'data', 'category': 'excel', 'processable': True},
        '.xls': {'type': 'data', 'category': 'excel', 'processable': False},
        '.csv': {'type': 'data', 'category': 'csv', 'processable': True},
        '.txt': {'type': 'text', 'category': 'plain_text', 'processable': True},
        '.md': {'type': 'text', 'category': 'markdown', 'processable': True},
        '.jpg': {'type': 'image', 'category': 'photo', 'processable': False},
        '.jpeg': {'type': 'image', 'category': 'photo', 'processable': False},
        '.png': {'type': 'image', 'category': 'photo', 'processable': False},
        '.zip': {'type': 'archive', 'category': 'compressed', 'processable': False},
    }
    
    result = type_map.get(extension, {'type': 'unknown', 'category': 'other', 'processable': False})
    result['mime_type'] = mime_type
    result['extension'] = extension
    
    return result
```

### 2. Metadata Extraction
Extract comprehensive file metadata:
```python
import os
from datetime import datetime

def extract_file_metadata(file_path: Path) -> dict:
    """
    Extract file metadata.
    
    Args:
        file_path: Path to file
    
    Returns:
        Dictionary with metadata
    """
    try:
        stat = file_path.stat()
        
        return {
            'name': file_path.name,
            'stem': file_path.stem,
            'extension': file_path.suffix,
            'size': stat.st_size,
            'size_human': format_file_size(stat.st_size),
            'created': datetime.fromtimestamp(stat.st_ctime).isoformat(),
            'modified': datetime.fromtimestamp(stat.st_mtime).isoformat(),
            'accessed': datetime.fromtimestamp(stat.st_atime).isoformat(),
            'absolute_path': str(file_path.absolute()),
        }
    except Exception as e:
        return {'error': str(e)}

def format_file_size(bytes_size: int) -> str:
    """Format bytes to human-readable size"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"
```

### 3. Content-Based Categorization
Categorize files by analyzing names and content:
```python
def categorize_file(file_path: Path, file_type: dict, metadata: dict) -> dict:
    """
    Categorize file based on name patterns and type.
    
    Args:
        file_path: Path to file
        file_type: File type dict from detect_file_type()
        metadata: Metadata dict from extract_file_metadata()
    
    Returns:
        Categorization with priority and destination
    """
    name = file_path.name.lower()
    
    # Invoice patterns
    invoice_patterns = ['invoice', 'bill', 'billing', 'payment-due']
    if any(pattern in name for pattern in invoice_patterns):
        return {
            'category': 'invoice',
            'priority': 'urgent',
            'destination': 'Needs_Action/urgent/',
            'type_desc': 'Financial Invoice',
            'reason': 'Filename contains invoice/bill keywords'
        }
    
    # Receipt patterns
    receipt_patterns = ['receipt', 'purchase', 'order-confirmation']
    if any(pattern in name for pattern in receipt_patterns):
        return {
            'category': 'receipt',
            'priority': 'normal',
            'destination': 'Needs_Action/normal/',
            'type_desc': 'Receipt/Purchase',
            'reason': 'Filename contains receipt keywords'
        }
    
    # Contract/agreement patterns
    contract_patterns = ['contract', 'agreement', 'nda', 'proposal']
    if any(pattern in name for pattern in contract_patterns):
        return {
            'category': 'contract',
            'priority': 'urgent',
            'destination': 'Needs_Action/urgent/',
            'type_desc': 'Legal Document',
            'reason': 'Filename contains contract keywords'
        }
    
    # Report patterns
    report_patterns = ['report', 'analysis', 'summary', 'statement']
    if any(pattern in name for pattern in report_patterns):
        return {
            'category': 'report',
            'priority': 'normal',
            'destination': 'Needs_Action/normal/',
            'type_desc': 'Report/Analysis',
            'reason': 'Filename contains report keywords'
        }
    
    # Default categorization by file type
    if file_type['type'] == 'document':
        return {
            'category': 'document',
            'priority': 'normal',
            'destination': 'Needs_Action/normal/',
            'type_desc': 'General Document',
            'reason': 'Document file type'
        }
    elif file_type['type'] == 'data':
        return {
            'category': 'data',
            'priority': 'normal',
            'destination': 'Needs_Action/normal/',
            'type_desc': 'Data File',
            'reason': 'Data file type (spreadsheet/CSV)'
        }
    else:
        return {
            'category': 'unknown',
            'priority': 'low',
            'destination': 'Inbox/files/',
            'type_desc': 'Uncategorized File',
            'reason': 'No matching patterns, needs manual review'
        }
```

### 4. Text Extraction (PDF)
Extract text from PDF files for analysis:
```python
def extract_pdf_text(file_path: Path, max_pages: int = 3) -> str:
    """
    Extract text from PDF (first few pages only).
    
    Args:
        file_path: Path to PDF file
        max_pages: Maximum pages to extract (default: 3)
    
    Returns:
        Extracted text or error message
    """
    try:
        # For Bronze tier, use basic extraction
        # In production, use PyPDF2 or pdfplumber
        import PyPDF2
        
        text_parts = []
        with open(file_path, 'rb') as file:
            reader = PyPDF2.PdfReader(file)
            num_pages = min(len(reader.pages), max_pages)
            
            for i in range(num_pages):
                page = reader.pages[i]
                text_parts.append(page.extract_text())
        
        full_text = '\n'.join(text_parts)
        return full_text[:2000]  # Limit to 2000 chars
        
    except ImportError:
        return "[PDF text extraction not available - PyPDF2 not installed]"
    except Exception as e:
        return f"[Error extracting PDF text: {e}]"
```

### 5. Markdown Summary Generation
Generate structured markdown summary:
```python
def generate_file_markdown(file_path: Path, metadata: dict, 
                          file_type: dict, category: dict,
                          text_preview: str = None) -> str:
    """
    Generate markdown summary of file.
    
    Args:
        file_path: Path to file
        metadata: File metadata
        file_type: File type information
        category: Categorization result
        text_preview: Optional text preview
    
    Returns:
        Formatted markdown string
    """
    timestamp = datetime.now().isoformat()
    
    markdown = f"""# File: {metadata['name']}

**Type:** {category['type_desc']}
**Category:** {category['category']}
**Size:** {metadata['size_human']}
**Priority:** {category['priority'].upper()}

## Classification
- **Destination:** {category['destination']}
- **Reason:** {category['reason']}
- **File Type:** {file_type['category']} ({file_type['extension']})

## Summary
{generate_content_summary(text_preview, file_type)}

## Metadata
- **Original Path:** {metadata['absolute_path']}
- **Extension:** {metadata['extension']}
- **Created:** {metadata['created']}
- **Modified:** {metadata['modified']}
- **MIME Type:** {file_type.get('mime_type', 'Unknown')}

## Actions Needed
{generate_action_items(category)}

## File Location
- **Original:** `{metadata['absolute_path']}`
- **Vault:** `AI_Employee_Vault/{category['destination']}{generate_safe_filename(file_path)}`

---
*Organized by file-organizer skill at {timestamp}*
"""
    return markdown

def generate_content_summary(text_preview: str, file_type: dict) -> str:
    """Generate content summary based on available preview"""
    if not text_preview or text_preview.startswith('['):
        return f"Binary {file_type['category']} file - no text preview available."
    
    if len(text_preview) < 100:
        return f"Content preview: {text_preview}"
    
    return f"Content preview (first 500 chars):\n\n{text_preview[:500]}..."

def generate_action_items(category: dict) -> str:
    """Generate action items based on category"""
    actions = ["- [ ] Review file content"]
    
    if category['category'] == 'invoice':
        actions.extend([
            "- [ ] Verify invoice details",
            "- [ ] Process payment",
            "- [ ] Update accounting records"
        ])
    elif category['category'] == 'contract':
        actions.extend([
            "- [ ] Legal review required",
            "- [ ] Obtain necessary signatures",
            "- [ ] File in contracts folder"
        ])
    elif category['category'] == 'receipt':
        actions.extend([
            "- [ ] Match to transaction",
            "- [ ] Add to expense report"
        ])
    else:
        actions.append("- [ ] Archive when complete")
    
    return '\n'.join(actions)
```

### 6. Safe Filename Generation
Create vault-safe filenames:
```python
import re

def generate_safe_filename(file_path: Path) -> str:
    """
    Generate safe filename with naming convention.
    
    Format: YYYY-MM-DD_category_description.ext
    
    Args:
        file_path: Original file path
    
    Returns:
        Safe filename string
    """
    # Get date
    date = datetime.now().strftime('%Y-%m-%d')
    
    # Clean filename
    base_name = file_path.stem
    safe_name = re.sub(r'[^\w\s-]', '', base_name)
    safe_name = re.sub(r'[-\s]+', '-', safe_name)[:50].strip('-')
    
    # Determine category prefix from filename
    name_lower = base_name.lower()
    if 'invoice' in name_lower:
        prefix = 'invoice'
    elif 'receipt' in name_lower:
        prefix = 'receipt'
    elif 'contract' in name_lower:
        prefix = 'contract'
    elif 'report' in name_lower:
        prefix = 'report'
    else:
        prefix = 'document'
    
    return f"{date}_{prefix}_{safe_name}{file_path.suffix}"
```

## Complete Organization Pipeline

```python
import shutil

def organize_file_complete(file_path: Path) -> dict:
    """
    Complete file organization pipeline.
    
    Steps:
    1. Detect file type
    2. Extract metadata
    3. Categorize file
    4. Extract text preview (if applicable)
    5. Generate markdown summary
    6. Save markdown to vault
    7. Copy original file
    8. Update dashboard
    
    Args:
        file_path: Path to file to organize
    
    Returns:
        Result dictionary
    """
    # Step 1: Detect type
    file_type = detect_file_type(file_path)
    
    # Step 2: Extract metadata
    metadata = extract_file_metadata(file_path)
    
    # Step 3: Categorize
    category = categorize_file(file_path, file_type, metadata)
    
    # Step 4: Extract text if PDF
    text_preview = None
    if file_type['category'] == 'pdf' and file_type['processable']:
        text_preview = extract_pdf_text(file_path)
    
    # Step 5: Generate markdown
    markdown = generate_file_markdown(file_path, metadata, file_type, 
                                      category, text_preview)
    
    # Step 6: Save markdown to vault
    vault_path = Path("AI_Employee_Vault")
    dest_dir = vault_path / category['destination']
    dest_dir.mkdir(parents=True, exist_ok=True)
    
    safe_filename = generate_safe_filename(file_path)
    markdown_path = dest_dir / f"{Path(safe_filename).stem}.md"
    markdown_path.write_text(markdown, encoding='utf-8')
    
    # Step 7: Copy original file
    file_copy_path = dest_dir / safe_filename
    shutil.copy2(file_path, file_copy_path)
    
    # Step 8: Log and update
    from vault_management import write_log
    write_log('INFO', 'FileOrganizer', 
              f"Organized {file_path.name} → {category['destination']}")
    
    from dashboard_updater import add_activity, update_daily_stats
    add_activity(f"Organized {file_path.name} → {category['destination']}")
    update_daily_stats('file')
    
    return {
        'status': 'success',
        'markdown_path': str(markdown_path),
        'file_path': str(file_copy_path),
        'category': category,
        'priority': category['priority']
    }
```

## Filesystem Watcher

Monitor directory for new files:
```python
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import time

class VaultFileHandler(FileSystemEventHandler):
    """Handle filesystem events for vault organization"""
    
    def __init__(self, watched_dir: str):
        self.watched_dir = Path(watched_dir)
        super().__init__()
    
    def on_created(self, event):
        """Handle new file creation"""
        if event.is_directory:
            return
        
        file_path = Path(event.src_path)
        
        # Wait for file to finish writing
        time.sleep(2)
        
        # Skip temporary files
        if file_path.name.startswith('.') or file_path.name.startswith('~'):
            return
        
        # Organize file
        try:
            result = organize_file_complete(file_path)
            print(f"✅ Organized: {file_path.name} → {result['category']['destination']}")
        except Exception as e:
            print(f"❌ Error organizing {file_path.name}: {e}")
            from vault_management import write_log
            write_log('ERROR', 'FileOrganizer', f"Failed: {file_path.name}: {e}")

def start_file_watcher(directory: str):
    """Start watching directory for new files"""
    event_handler = VaultFileHandler(directory)
    observer = Observer()
    observer.schedule(event_handler, directory, recursive=False)
    observer.start()
    
    print(f"👀 Watching directory: {directory}")
    print("Press Ctrl+C to stop...")
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        observer.stop()
        print("\n⏸️  Watcher stopped")
    
    observer.join()
```

## File Category Rules

### Invoice (Urgent)
- Patterns: invoice, bill, billing, payment-due
- Destination: Needs_Action/urgent/
- Actions: Verify, process payment, update records

### Receipt (Normal)
- Patterns: receipt, purchase, order-confirmation
- Destination: Needs_Action/normal/
- Actions: Match transaction, add to expenses

### Contract (Urgent)
- Patterns: contract, agreement, nda, proposal
- Destination: Needs_Action/urgent/
- Actions: Legal review, signatures, file

### Report (Normal)
- Patterns: report, analysis, summary, statement
- Destination: Needs_Action/normal/
- Actions: Review, share with team

### Generic Document (Normal)
- No specific patterns
- Destination: Needs_Action/normal/
- Actions: Review and categorize

## Error Handling

- **Corrupted file**: Log error, move to Inbox/files/
- **Unsupported type**: Move to Inbox/files/ for manual review
- **Permission denied**: Log with suggested permissions fix
- **Duplicate file**: Check if truly duplicate (by hash), rename if different
- **Large file (>100MB)**: Save metadata only, link to original location

## Integration

- Uses `vault-management` for file operations and logging
- Calls `dashboard-updater` after organizing
- Reads rules from `Company_Handbook.md`

## Notes

- Only processes files in monitored directory (no subdirectories)
- Waits 2 seconds after file creation to ensure write completion
- Skips hidden files (starting with . or ~)
- Preserves original file metadata (timestamps)
- Creates both markdown summary and file copy in vault