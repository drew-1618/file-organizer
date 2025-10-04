import argparse
import shutil
from pathlib import Path
import sys

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
    parser.add_argument('-d', '--dry-run', action='store_true', help='Simulate the organization without making changes')
    return parser


def organize_files(source_dir, dry_run=False):
    source_path = Path(source_dir)
    if not source_path.is_dir():
        print(f"Error: {source_dir} is not a valid directory.")
        sys.exit(1)

    for item in source_path.iterdir():
        if item.is_file() and not item.name.startswith('.'):
            extension = item.suffix.lower().lstrip('.')
            target_folder_name = FILE_TYPE_MAP.get(extension, 'Miscellaneous') 
            target_folder = source_path / target_folder_name
            if not target_folder.exists() and not dry_run:
                target_folder.mkdir()
                print(f"[ACTION] Created directory: {target_folder_name}/")
            target_path = target_folder / item.name
            if not dry_run:
                try:
                    shutil.move(str(item), str(target_path))
                    print(f"[MOVE] {item.name} -> {target_folder_name}/")
                except Exception as e:
                    print(f"[ERROR] Could not move {item.name}. Reason: {e}")
            else:
                print(f"[DRY-RUN] Would move {item.name} -> {target_folder_name}/")

if __name__ == "__main__":
    parser = setup_parser()
    args = parser.parse_args()
    organize_files(args.source_dir, args.dry_run)

