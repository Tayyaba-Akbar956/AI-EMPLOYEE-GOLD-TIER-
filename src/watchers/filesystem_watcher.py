"""Filesystem Watcher - Monitor directories and organize files into vault"""
import mimetypes
import re
import shutil
import time
from datetime import datetime
from pathlib import Path

# Import vault management functions
try:
    from src.utils.vault_management import write_log, write_vault_file
    from src.utils.dashboard_updater import log_and_update
except ImportError:
    # Fallback for direct execution
    import sys
    sys.path.insert(0, str(Path(__file__).parent.parent.parent))
    from src.utils.vault_management import write_log, write_vault_file
    from src.utils.dashboard_updater import log_and_update


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


def format_file_size(bytes_size: int) -> str:
    """Format bytes to human-readable size"""
    for unit in ['B', 'KB', 'MB', 'GB', 'TB']:
        if bytes_size < 1024.0:
            return f"{bytes_size:.1f} {unit}"
        bytes_size /= 1024.0
    return f"{bytes_size:.1f} PB"


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

    # Step 4: Extract text if PDF (skip for Bronze tier simplicity)
    text_preview = None

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

    # Step 8: Log
    write_log('INFO', 'FileOrganizer',
              f"Organized {file_path.name} -> {category['destination']}")

    # Step 9: Update dashboard
    log_and_update(f"Organized file: {file_path.name}", stat_type='file')

    return {
        'status': 'success',
        'markdown_path': str(markdown_path),
        'file_path': str(file_copy_path),
        'category': category,
        'priority': category['priority']
    }


def start_watcher(watch_directory: str):
    """
    Start watching directory for new files.

    Args:
        watch_directory: Directory to monitor
    """
    watch_path = Path(watch_directory)
    if not watch_path.exists():
        print(f"❌ Watch directory does not exist: {watch_directory}")
        return

    print(f"👀 Watching directory: {watch_directory}")
    print("Press Ctrl+C to stop...")

    # Track already seen files
    seen_files = set(f.name for f in watch_path.iterdir() if f.is_file())

    try:
        while True:
            # Check for new files
            current_files = set(f.name for f in watch_path.iterdir() if f.is_file())
            new_files = current_files - seen_files

            for filename in new_files:
                file_path = watch_path / filename

                # Skip hidden/temp files
                if filename.startswith('.') or filename.startswith('~'):
                    continue

                # Wait for file to finish writing
                time.sleep(2)

                try:
                    result = organize_file_complete(file_path)
                    print(f"✅ Organized: {filename} -> {result['category']['destination']}")
                except Exception as e:
                    print(f"❌ Error organizing {filename}: {e}")
                    write_log('ERROR', 'FileOrganizer', f"Failed: {filename}: {e}")

            seen_files = current_files
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n⏸️  Watcher stopped")


if __name__ == '__main__':
    import sys
    watch_dir = sys.argv[1] if len(sys.argv) > 1 else './watch_folder'
    start_watcher(watch_dir)
