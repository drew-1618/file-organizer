import hashlib
import logging
import shutil
import json
from datetime import datetime
from pathlib import Path
import sys

CHUNK_SIZE = 65536   # 64KB
CONFIG_FILE = 'config/config.json'

def get_config(config_path):
    """Loads configuration from a JSON file."""
    try:
        with open(config_path, 'r') as f:
            FILE_TYPE_MAP = json.load(f)
        return FILE_TYPE_MAP
    except Exception as e:
        logging.error(f"Failed to load config file: {e}")
        sys.exit(1)

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


def _get_target_names(item, date_prefixing, file_type_map):
    """Determines the base folder name and applies date prefixing to the filename."""
    extension = item.suffix.lower().lstrip('.')
    target_folder_name = file_type_map.get(extension, 'Miscellaneous') 
    final_file_name = item.name
    date_modified = datetime.fromtimestamp(item.stat().st_mtime)

    final_file_name = _apply_date_prefix(item, final_file_name, date_prefixing)        
    return target_folder_name, final_file_name, date_modified


def _apply_date_prefix(item, file_name, date_prefixing):
    """Applies date prefixing to the filename if specified."""
    if date_prefixing not in ('modified', 'created'):
        return file_name # No change
        
    if date_prefixing == 'modified':
        date_to_use = datetime.fromtimestamp(item.stat().st_mtime)
    else: # created
        date_to_use = datetime.fromtimestamp(item.stat().st_ctime)

    date_str = date_to_use.strftime('%Y-%m-%d_')
    # Prevent double-prefixing
    if file_name.startswith(date_str):
        return file_name
    return f"{date_str}{file_name}"


def _handle_deduping(item, target_folder, final_file_name, hashes_seen, deduping, delete_duplicates, dry_run, stats):
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
                stats.increment_count('files_deleted')
            except Exception as e:
                logging.error(f"Could not delete {item.name}. Reason: {e}")
                return False
        else: stats.increment_count('files_skipped')
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
                    stats.increment_count('files_deleted')
                except Exception as e:
                    logging.error(f"Could not delete {item.name}. Reason: {e}")
                    return False
            else: stats.increment_count('files_skipped')
            logging.info(f"Target duplicate found. {action} redundant file: {item.name}.")
            return True
            
    return False


def _is_item_eligible(item, min_size_bytes, min_size_mb, category_folders, in_place):
    """Checks if the item is a file and meets the minimum size requirement."""
    if not item.is_file() or item.name.startswith('.'):
        logging.info(f"Skipping non-file or hidden item: {item.name}")
        return False

    if not in_place and item.is_dir() and item.name in category_folders:
        logging.info(f"Skipping category folder: {item.name}/")
        return False

    if min_size_bytes is not None and item.stat().st_size < min_size_bytes:
        logging.info(f"Skipping {item.name} (size below {min_size_mb} MB).")
        return False

    return True


def _execute_move(item, target_folder, target_path, final_folder_name, final_file_name, dry_run, stats):
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
            stats.increment_count('files_moved')
        except Exception as e:
            logging.error(f"Could not move {item.name}. Reason: {e}")
            stats.increment_count('files_skipped')
    else:
        # Dry Run Logging
        logging.info(f"[DRY-RUN] Would move {item.name} -> {final_folder_name}/{target_path.name}")
        stats.increment_count('files_moved')
