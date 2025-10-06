import argparse
import shutil
from pathlib import Path
import sys
from datetime import datetime, timedelta
import json
import logging
import hashlib

CHUNK_SIZE = 65536   # 64KB

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

# --- Utility Functions ---

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


def calculate_file_hash(file_path, hash_algo='md5'):
    """Calculates hash of a file efficiently by reading it in chunks."""
    file_hash = hashlib.new(hash_algo)
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(CHUNK_SIZE):
                file_hash.update(chunk)
    except Exception as e:
        logging.error(f"Failed to hash {file_path.name}: {e}")
        return ""
    return file_hash.hexdigest()


# --- Helper Functions ---

def _apply_date_prefix(item, file_name, date_prefixing):
    """Applies date prefixing to the filename if specified."""
    if date_prefixing not in ('modified', 'created'):
        return file_name # No change
        
    if date_prefixing == 'modified':
        date_modified = datetime.fromtimestamp(item.stat().st_mtime)
    else: # created
        date_to_use = datetime.fromtimestamp(item.stat().st_ctime)

    date_str = date_to_use.strftime('%Y-%m-%d_')
    return f"{date_str}{file_name}"


def _get_target_names(item, date_prefixing):
    """Determines the base folder name and applies date prefixing to the filename."""
    extension = item.suffix.lower().lstrip('.')
    target_folder_name = FILE_TYPE_MAP.get(extension, 'Miscellaneous') 
    final_file_name = item.name
    date_modified = datetime.fromtimestamp(item.stat().st_mtime)

    final_file_name = _apply_date_prefix(item, final_file_name, date_prefixing)        
    return target_folder_name, final_file_name, date_modified


def _handle_archiving(target_folder_name, date_modified, archive_threshold):
    """Applies the archiving rule to the target folder name."""
    if archive_threshold is not None and date_modified < archive_threshold:
        return Path(target_folder_name) / "Archive"
    return Path(target_folder_name)


def _handle_deduping(item, target_folder, final_file_name, hashes_seen, deduping, delete_duplicates, dry_run):
    """
    Performs content-based deduping checks.
    Returns True if file should be skipped/deleted.
    """
    if not deduping:
        return False

    source_hash = calculate_file_hash(item)
    if not source_hash:
        logging.error(f"Skipping deduplication for {item.name} due to hash calculation failure.")
        return False

    target_path = target_folder / final_file_name
    
    # Source-to-Source Check (Has this hash been seen earlier in this run?)
    if source_hash in hashes_seen:
        action = "Deleted" if delete_duplicates and not dry_run else "Skipped"
        if delete_duplicates and not dry_run:
            try:
                item.unlink()
            except Exception as e:
                logging.error(f"Could not delete {item.name}. Reason: {e}")
                return False
        logging.info(f"Source duplicate found. {action} redundant file: {item.name}.")
        return True
        
    hashes_seen.add(source_hash)

    # Source-to-Target Check (Does a copy exist at the destination path?)
    if target_path.exists():
        target_hash = calculate_file_hash(target_path)
        if source_hash == target_hash:
            action = "Deleted" if delete_duplicates and not dry_run else "Skipped"
            if delete_duplicates and not dry_run:
                try:
                    item.unlink()
                except Exception as e:
                    logging.error(f"Could not delete {item.name}. Reason: {e}")
                    return False
            logging.info(f"Target duplicate found. {action} redundant file: {item.name}.")
            return True
            
    return False


def _execute_move(item, target_folder, target_path, final_folder_name, final_file_name, dry_run):
    """
    Handles folder creation, name conflict resolution, and the file move/dry-run.
    """
    if not dry_run:
        final_stem, final_suffix = Path(final_file_name).stem, Path(final_file_name).suffix
        try:
            duplicate_count = 1
            # Name Conflict Resolution
            while target_path.exists():
                target_path = target_folder / f"{final_stem}_{duplicate_count}{final_suffix}"
                duplicate_count += 1
            shutil.move(str(item), str(target_path))
            logging.info(f"Moving {item.name} -> {target_path.name} in {final_folder_name}/")
        except Exception as e:
            logging.error(f"Could not move {item.name}. Reason: {e}")
    else:
        # Dry Run Logging
        logging.info(f"[DRY-RUN] Would move {item.name} -> {final_folder_name}/{final_file_name}")


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

    if not in_place:
        category_folders = set(FILE_TYPE_MAP.values())
        category_folders.add('Miscellaneous')
        category_folders.add('Archive')

    for item in source_path.iterdir():
        # Skip category folders
        if not in_place and item.name in category_folders and item.is_dir():
            logging.info(f"Skipping category folder: {item.name}/")
            continue

        if item.is_file() and not item.name.startswith('.'):

            # Size Check
            if min_size_bytes is not None and item.stat().st_size < min_size_bytes:
                logging.info(f"Skipping {item.name} (size below {min_size_mb} MB).")
                continue

            if in_place:
                target_folder_name = item.parent.name if item.parent != source_path else '.'
                final_file_name = item.name
                date_modified = datetime.fromtimestamp(item.stat().st_mtime)
                # Apply date prefixing if needed
                final_file_name = _apply_date_prefix(item, final_file_name, date_prefixing)
            else:
                target_folder_name, final_file_name, date_modified = _get_target_names(item, date_prefixing)

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
            
            # 4. Deduping
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
