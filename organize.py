import argparse
from pathlib import Path
import sys
from datetime import datetime, timedelta
import json
import logging

from file_manager import (
    calculate_file_hash,
    _get_target_names,
    _apply_date_prefix,
    _handle_deduping,
    _handle_archiving,
    _is_item_eligible,
    _execute_move
)

CONFIG_FILE = 'config.json'
LOGGING_FILE = 'organizer.log'

try:
    with open(CONFIG_FILE, 'r') as f:
        FILE_TYPE_MAP = json.load(f)
except FileNotFoundError:
    print(f"FATAL ERROR: Configuration file '{CONFIG_FILE}' not found.")
    sys.exit(1)

logging.basicConfig(
    filename=LOGGING_FILE,
    level=logging.INFO,
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s')


def setup_parser():
    """Defines and sets up the command line interface using argparse."""
    parser = argparse.ArgumentParser(
        description='Organize files in a directory by their types.',
        epilog='Example usage: python3 organize.py Downloads --archive-older-than 30 --deduping'
    )
    parser.add_argument('source_dir', help='Directory to organize')
    parser.add_argument('-d', '--dry-run', action='store_true', help='Simulate the organization without making changes')
    parser.add_argument('--in-place', action='store_true', help='Apply rules without re-categorizing files (useful for pre-organized folders)')
    parser.add_argument('--archive-older-than', type=int, metavar='DAYS', default=0, help='Archive files older than specified days')
    parser.add_argument('--min-size-mb', type=int, metavar='MB', default=0, help='Only organize files larger than specified size in MB')
    parser.add_argument('--date-prefixing', type=str, metavar='TYPE', default=None, help='Prefix files with their creation or modification date (YYYY-MM-DD_)')
    parser.add_argument('--deduping', action='store_true', help='Enable deduplication based on file content hash')
    parser.add_argument('--delete-duplicates', action='store_true', help='Delete duplicate files instead of skipping them (use with --deduping)')
    return parser


def _prepare_run(archive_older_than, min_size_mb, date_prefixing, deduping, delete_duplicates):
    min_size_bytes = None
    archive_threshold = None
    
    if archive_older_than > 0:
        current_time = datetime.now()
        archive_threshold = current_time - timedelta(days=archive_older_than)
        logging.info(f"Archive mode: Active. Files modified before {archive_threshold.strftime('%Y-%m-%d %H:%M')} will be archived.")

    if min_size_mb > 0:
        min_size_bytes = min_size_mb * 1024 * 1024   # 1 MB = 1024 KB * 1024 Bytes
        logging.info(f"Minimum size filter: Active. Organizing files >= {min_size_mb} MB.")

    # Log date prefixing status
    if date_prefixing == 'modified':
        logging.info("Date prefixing: Active. Files will be prefixed with their modification date.")
    elif date_prefixing == 'created':
        logging.info("Date prefixing: Active. Files will be prefixed with their creation date.")
    elif date_prefixing is not None:
        logging.error(f"Invalid date type '{date_prefixing}'. Renaming feature disabled for this session.")
        date_prefixing = None

    # Input confirmation for permanent deletion
    if deduping and delete_duplicates:
        delete_confirmation = input("Warning: You have enabled deletion of duplicate files. This action is irreversible. Do you want to proceed? (Y/N): ").upper()
        if delete_confirmation != 'Y':
            delete_duplicates = False
            logging.info("Deduplication with deletion: Disabled by user. Duplicate files will be skipped instead.")
        else:
            logging.info("Deduplication with deletion: Active. Duplicate files will be deleted.")

    return archive_threshold, min_size_bytes, date_prefixing, delete_duplicates


def organize_files(source_dir, dry_run=False, in_place=False, archive_older_than=0, min_size_mb=0, date_prefixing=None, deduping=False, delete_duplicates=False):
    """Core logic to orchestrate file filtering, transformation, and execution."""
    source_path = Path(source_dir)
    if not source_path.is_dir():
        print(f"Error: {source_dir} is not a valid directory.")
        logging.error(f"{source_dir} is not a directory.")
        sys.exit(1)

    logging.info(f"Starting organization in: {source_dir}")
    if in_place:
        logging.info("In-place mode: Active. Files will not be re-categorized, only processed with selected rules.")

    hashes_seen = set()
    
    archive_threshold, min_size_bytes, date_prefixing, delete_duplicates = _prepare_run(
        archive_older_than,
        min_size_mb,
        date_prefixing,
        deduping,
        delete_duplicates
    )

    if not in_place:
        category_folders = set(FILE_TYPE_MAP.values())
        category_folders.add('Miscellaneous')
        category_folders.add('Archive')

    for item in source_path.iterdir():
        
        if not _is_item_eligible(item, min_size_bytes, min_size_mb, category_folders if not in_place else set(), in_place):
            continue

        if in_place:
            target_folder_name = item.parent.name if item.parent != source_path else '.'
            final_file_name = item.name
            date_modified = datetime.fromtimestamp(item.stat().st_mtime)
            # Apply date prefixing if needed
            final_file_name = _apply_date_prefix(item, final_file_name, date_prefixing)
        else:
            target_folder_name, final_file_name, date_modified = _get_target_names(item, date_prefixing, FILE_TYPE_MAP)

        final_folder_path = _handle_archiving(target_folder_name, date_modified, archive_threshold)

        if in_place:
            if 'Archive' in str(final_folder_path):
                target_folder = source_path / 'Archive'
            else:
                target_folder = source_path
        else:
            # normal 
            target_folder = source_path / final_folder_path

        target_path = target_folder / final_file_name

        # Convert to string for logging
        final_folder_name = str(final_folder_path) if not in_place else (target_folder.name if target_folder != source_path else '.')

        if not target_folder.exists() and not dry_run:
            target_folder.mkdir(parents=True, exist_ok=True)
            logging.info(f"Created directory: {final_folder_name}/")
            
        if deduping:
            should_skip = _handle_deduping(item, target_folder, final_file_name, hashes_seen, deduping, delete_duplicates, dry_run)
            if should_skip:
                continue
            
        # Move File
        if target_path != item:
            _execute_move(item, target_folder, target_path, final_folder_name, final_file_name, dry_run)

    logging.info("Organization complete.")

# --- Main Execution ---
if __name__ == "__main__":
    parser = setup_parser()
    args = parser.parse_args()
    organize_files(args.source_dir, args.dry_run, args.in_place, args.archive_older_than, args.min_size_mb,
                   args.date_prefixing, args.deduping, args.delete_duplicates)
