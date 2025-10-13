import argparse
from pathlib import Path
import sys
from datetime import datetime, timedelta
import json
import logging

from run_stats import FileStats
from rule_engine import load_rules, find_matching_rule, RULES_FILE

from file_manager import (
    get_config,
    CONFIG_FILE,
    calculate_file_hash,
    _get_target_names,
    _apply_date_prefix,
    _handle_deduping,
    _is_item_eligible,
    _execute_move
)

LOGGING_FILE = 'organizer.log'

FILE_TYPE_MAP = get_config(CONFIG_FILE)

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
    parser.add_argument('-i', '--in-place', action='store_true', help='Apply rules without re-categorizing files (useful for pre-organized folders)')
    ### parser.add_argument('-a', '--archive-older-than', type=int, metavar='DAYS', default=0, help='Archive files older than specified days')
    parser.add_argument('-m', '--min-size-mb', type=int, metavar='MB', default=0, help='Only organize files larger than specified size in MB')
    parser.add_argument('-p', '--date-prefixing', type=str, metavar='TYPE', default=None, help='Prefix files with their creation or modification date (YYYY-MM-DD_)')
    parser.add_argument('-D', '--deduping', action='store_true', help='Enable deduplication based on file content hash')
    parser.add_argument('-k', '--delete-duplicates', action='store_true', help='Delete duplicate files instead of skipping them (use with --deduping)')
    return parser


def _prepare_run(min_size_mb, date_prefixing, deduping, delete_duplicates):
    min_size_bytes = None

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

    return min_size_bytes, date_prefixing, delete_duplicates


def organize_files(source_dir, dry_run=False, in_place=False, min_size_mb=0, date_prefixing=None, deduping=False, delete_duplicates=False):
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
    stats = FileStats()
    custom_rules = load_rules(RULES_FILE)
    
    min_size_bytes, date_prefixing, delete_duplicates = _prepare_run(
        min_size_mb,
        date_prefixing,
        deduping,
        delete_duplicates
    )

    if not in_place:
        category_folders = set(FILE_TYPE_MAP.values())
        category_folders.add('Miscellaneous')

    for item in source_path.iterdir():
        
        if not _is_item_eligible(item, min_size_bytes, min_size_mb, category_folders if not in_place else set(), in_place):
            continue

        try:
            file_size = item.stat().st_size
            file_extension = item.suffix
            stats.add_file_data(file_size, file_extension)
        except OSError:
            # This handles rare cases where the file disappears between iterdir() and stat()
            logging.warning(f"File vanished during processing: {item.name}. Skipping.")
            stats.increment_count('files_skipped')
            continue


        rule_action_delete = False
        matching_rule = find_matching_rule(item, custom_rules)

        if matching_rule:
            rule_action = matching_rule['action']
            target_folder_name = rule_action.get('move_to', target_folder_name if 'target_folder_name' in locals() else 'Miscellaneous')
            final_file_name = item.name

            if 'rename_prefix' in rule_action:
                prefix = rule_action['rename_prefix']
                final_name = f"{prefix}{final_file_name}"
                stats.increment_count('files_renamed')

            rule_action_delete = rule_action.get('delete_file', False)

        else:  # Default extension-based logic
            target_folder_name, final_file_name, date_modified = _get_target_names(item, date_prefixing, FILE_TYPE_MAP)

        if rule_action_delete:
            if not dry_run:
                try:
                    item.unlink()
                    stats.increment_count('files_deleted')
                    logging.info(f"File {item.name} deleted by custom rule: {matching_rule.get('name', 'Unnamed Rule')}.")
                except Exception as e:
                    logging.error(f"Could not delete {item.name} via custom rule. Reason: {e}")
                    stats.increment_count('files_skipped')
            else:
                logging.info(f"[DRY-RUN] Would delete {item.name} by custom rule: {matching_rule.get('name', 'Unnamed Rule')}.")
                stats.increment_count('files_deleted')
            continue  # Go to next item

        if in_place:
            target_folder = source_path
        else:
            target_folder = source_path / Path(target_folder_name)
            
        target_path = target_folder / final_file_name

        # If the target is the same as the source path, use '.' for cleaner logging
        if target_folder == source_path:
             final_folder_name = '.'
        else:
             final_folder_name = str(target_folder.relative_to(source_path))

        if not target_folder.exists() and not dry_run:
            target_folder.mkdir(parents=True, exist_ok=True)
            logging.info(f"Created directory: {final_folder_name}/")
            stats.increment_count('directories_created')
            
        if deduping:
            should_skip = _handle_deduping(item, target_folder, final_file_name, hashes_seen, deduping, delete_duplicates, dry_run, stats)
            if should_skip:
                continue

        # Move File
        if target_path != item:
            _execute_move(item, target_folder, target_path, final_folder_name, final_file_name, dry_run, stats)
        else:
            logging.info(f"File already in correct location: {item.name}. No action taken.")
            stats.increment_count('files_skipped')

    # Summary Report
    stats.generate_report()
    logging.info("Organization complete.")

# --- Main Execution ---
if __name__ == "__main__":
    parser = setup_parser()
    args = parser.parse_args()
    organize_files(args.source_dir, args.dry_run, args.in_place, args.min_size_mb,
                   args.date_prefixing, args.deduping, args.delete_duplicates)
