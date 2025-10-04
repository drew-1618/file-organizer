import argparse
import shutil
from pathlib import Path
import sys
from datetime import datetime, timedelta

FILE_TYPE_MAP = {
    # Images
    'jpg': 'Images', 'jpeg': 'Images', 'png': 'Images', 
    'gif': 'Images', 'bmp': 'Images', 'tiff': 'Images',
    'svg': 'Images',
    # Documents
    'pdf': 'Documents', 'doc': 'Documents', 'docx': 'Documents',
    'txt': 'Documents', 'xls': 'Documents', 'xlsx': 'Documents',
    'ppt': 'Documents', 'pptx': 'Documents', 'odt': 'Documents',
    # Audio
    'mp3': 'Audio', 'wav': 'Audio', 'aac': 'Audio',
    'flac': 'Audio', 'ogg': 'Audio', 'm4a': 'Audio',
    # Videos
    'mp4': 'Videos', 'avi': 'Videos', 'mkv': 'Videos',
    'mov': 'Videos', 'wmv': 'Videos', 'flv': 'Videos',
    # Archives
    'zip': 'Archives', 'rar': 'Archives', 'tar': 'Archives',
    'gz': 'Archives', '7z': 'Archives',
    # Scripts
    'py': 'Scripts', 'js': 'Scripts', 'sh': 'Scripts',
    'bat': 'Scripts', 'pl': 'Scripts', 'rb': 'Scripts'
}

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
    return parser


def organize_files(source_dir, dry_run=False, archive_older_than=0, min_size_mb=0):
    source_path = Path(source_dir)
    if not source_path.is_dir():
        print(f"Error: {source_dir} is not a valid directory.")
        sys.exit(1)

    archive_threshold = None
    min_size_bytes = None

    if archive_older_than > 0:
        current_time = datetime.now()
        archive_threshold = current_time - timedelta(days=archive_older_than)
        print(f"Archive mode: Active. Files modified before {archive_threshold.strftime('%Y-%m-%d %H:%M')} will be archived.")

    if min_size_mb > 0:
        min_size_bytes = min_size_mb * 1024 * 1024   # 1 MB = 1024 KB * 1024 Bytes
        print(f"Minimum size filter: Active. Organizing files >= {min_size_mb} MB.")

    for item in source_path.iterdir():
        if item.is_file() and not item.name.startswith('.'):
            extension = item.suffix.lower().lstrip('.')
            target_folder_name = FILE_TYPE_MAP.get(extension, 'Miscellaneous') 

            date_modified = datetime.fromtimestamp(item.stat().st_mtime)
            if archive_threshold is not None and date_modified < archive_threshold:
                target_folder_name = f"{target_folder_name}/Archive"

            if min_size_bytes is not None and item.stat().st_size < min_size_bytes:
                print(f"[SKIP] {item.name} (size below {min_size_mb} MB)")
                continue

            target_folder = source_path / target_folder_name
            target_path = target_folder / item.name

            if not target_folder.exists() and not dry_run:
                target_folder.mkdir(parents=True)
                print(f"[ACTION] Created directory: {target_folder_name}/")

            if not dry_run:
                try:
                    duplicate_count = 1
                    while target_path.exists():
                        target_path = target_folder / f"{item.stem}_{duplicate_count}{item.suffix}"
                        duplicate_count += 1
                    shutil.move(str(item), str(target_path))
                    print(f"[MOVE] {item.name} -> {target_folder_name}/")
                except Exception as e:
                    print(f"[ERROR] Could not move {item.name}. Reason: {e}")
            else:
                print(f"[DRY-RUN] Would move {item.name} -> {target_folder_name}/")

if __name__ == "__main__":
    parser = setup_parser()
    args = parser.parse_args()
    organize_files(args.source_dir, args.dry_run, args.archive_older_than, args.min_size_mb)
