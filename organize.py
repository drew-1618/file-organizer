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
with open(CONFIG_FILE, 'r') as f:
    FILE_TYPE_MAP = json.load(f)
logging.basicConfig(
    filename=LOGGING_FILE,
    level=logging.INFO,
    filemode='w',
    format='%(asctime)s - %(levelname)s - %(message)s')

HASHES_SEEN = set()

def setup_parser():
    # may need to update the epilog with more examples
    parser = argparse.ArgumentParser(
        description='Organize files in a directory by their types.',
        epilog='Example usage: python3 organize.py Downloads'
    )
    # Required positional argument for source directory
    parser.add_argument('source_dir', help='Directory to organize')
    # Optional flag for dry run
    parser.add_argument('-d', '--dry-run', action='store_true', help='Simulate the organization without making changes')
    # Optional flag for archiving files older than specified days
    parser.add_argument('--archive-older-than', type=int, metavar='DAYS', default=0, help='Archive files older than specified days')
    # Optional flag for minimum file size in MB
    parser.add_argument('--min-size-mb', type=int, metavar='MB', default=0, help='Only organize files larger than specified size in MB')
    # Optional flag for date prefixing
    parser.add_argument('--date-prefixing', type=str, metavar='TYPE', default=None, help='Prefix files with their creation or modification date (YYYY-MM-DD_)')
    # Optional flag for deduplication
    parser.add_argument('--deduping', action='store_true', help='Enable deduplication based on file content hash')
    # Optional flag for deleting duplicates
    parser.add_argument('--delete-duplicates', action='store_true', help='Delete duplicate files instead of skipping them (use with --deduping)')
    return parser


def calculate_file_hash(file_path, hash_algo='md5'):
    file_hash = hashlib.new(hash_algo)
    try:
        with open(file_path, 'rb') as f:
            while chunk := f.read(CHUNK_SIZE):
                file_hash.update(chunk)
    except Exception as e:
        # Log error but return empty hash string
        logging.error(f"Failed to hash {file_path.name}: {e}")
        return ""
    return file_hash.hexdigest()


def organize_files(source_dir, dry_run=False, archive_older_than=0, min_size_mb=0, date_prefixing=None, deduping=False, delete_duplicates=False):
    source_path = Path(source_dir)
    if not source_path.is_dir():
        print(f"Error: {source_dir} is not a valid directory.")
        logging.error(f"{source_dir} is not a directory.")
        sys.exit(1)

    logging.info(f"Starting organization in: {source_dir}")

    archive_threshold = None
    min_size_bytes = None
    date_to_use = None

    if archive_older_than > 0:
        current_time = datetime.now()
        archive_threshold = current_time - timedelta(days=archive_older_than)
        logging.info(f"Archive mode: Active. Files modified before {archive_threshold.strftime('%Y-%m-%d %H:%M')} will be archived.")

    if min_size_mb > 0:
        min_size_bytes = min_size_mb * 1024 * 1024   # 1 MB = 1024 KB * 1024 Bytes
        logging.info(f"Minimum size filter: Active. Organizing files >= {min_size_mb} MB.")

    if date_prefixing is not None:
        if date_prefixing == 'modified':
            logging.info("Date prefixing: Active. Files will be prefixed with their modification date.")
        elif date_prefixing == 'created':
            logging.info("Date prefixing: Active. Files will be prefixed with their creation date.")
        else:
            logging.error(f"Invalid date type '{date_prefixing}'. Renaming feature disabled for this session.")
            date_to_use = None

    if deduping and delete_duplicates:
        delete_confirmation = input("Warning: You have enabled deletion of duplicate files. This action is irreversible. Do you want to proceed? (Y/N): ").upper()
        if delete_confirmation == 'Y':
            logging.info("Deduplication with deletion: Active. Duplicate files will be deleted.")
        elif delete_confirmation == 'N':
            delete_duplicates = False
            logging.info("Deduplication with deletion: Disabled by user. Duplicate files will be skipped instead.")
        else:
            logging.info("Deduplication with deletion: Invalid input. Duplicate files will be skipped instead.")
            delete_duplicates = False
    for item in source_path.iterdir():
        if item.is_file() and not item.name.startswith('.'):
            extension = item.suffix.lower().lstrip('.')
            target_folder_name = FILE_TYPE_MAP.get(extension, 'Miscellaneous') 
            date_modified = datetime.fromtimestamp(item.stat().st_mtime)
            final_file_name = item.name

            if min_size_bytes is not None and item.stat().st_size < min_size_bytes:
                logging.info(f"Skipping {item.name} (size below {min_size_mb} MB).")
                continue

            if archive_threshold is not None and date_modified < archive_threshold:
                target_folder_name = f"{target_folder_name}/Archive"

            if date_to_use is not None:
                date_str = date_to_use.strftime('%Y-%m-%d_')
                final_file_name = f"{date_str}{final_file_name}"

            target_folder = source_path / target_folder_name
            target_path = target_folder / final_file_name
            
            if deduping:
                source_hash = calculate_file_hash(item)
                if source_hash in HASHES_SEEN:
                    if delete_duplicates and not dry_run:
                        try:
                            item.unlink()
                            logging.info(f"Deleted duplicate file: {item.name}.")
                        except Exception as e:
                            logging.error(f"Could not delete {item.name}. Reason: {e}")
                    else:
                        # skip if deletion is off or is a dry run
                        logging.info(f"Duplicate found. Skipping redundant file: {item.name}.")
                    continue
                # if unique so far, add to seen set
                HASHES_SEEN.add(source_hash)

                if target_path.exists():
                    target_hash = calculate_file_hash(target_path)
                    if source_hash == target_hash:
                        logging.info(f"Duplicate file detected: {item.name} is identical to {target_path.name}.")
                        if delete_duplicates and not dry_run:
                            try:
                                item.unlink()
                                logging.info(f"Deleted duplicate file: {item.name}.")
                            except Exception as e:
                                logging.error(f"Could not delete {item.name}. Reason: {e}")
                        else:
                            logging.info(f"Duplicate found. Skipping reundant file: {item.name}.")
                        continue

            if not target_folder.exists() and not dry_run:
                target_folder.mkdir(parents=True)
                logging.info(f"Created directory: {target_folder_name}/")

            if not dry_run:
                final_stem, final_suffix = Path(final_file_name).stem, Path(final_file_name).suffix
                try:
                    duplicate_count = 1
                    while target_path.exists():
                        target_path = target_folder / f"{final_stem}_{duplicate_count}{final_suffix}"
                        duplicate_count += 1
                    shutil.move(str(item), str(target_path))
                    logging.info(f"Moving {final_file_name} -> {target_folder_name}/")
                except Exception as e:
                    logging.error(f"Could not move {final_file_name}. Reason: {e}")
            else:
                logging.info(f"[DRY-RUN] Would move {final_file_name} -> {target_folder_name}/")

    logging.info("Organization complete.")

if __name__ == "__main__":
    parser = setup_parser()
    args = parser.parse_args()
    organize_files(args.source_dir, args.dry_run, args.archive_older_than, args.min_size_mb,
                   args.date_prefixing, args.deduping, args.delete_duplicates)
