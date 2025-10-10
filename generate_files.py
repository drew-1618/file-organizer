from pathlib import Path
import json
from random import choice, randint, randbytes, uniform
from shutil import rmtree
from time import time
import os
import argparse

from file_manager import get_config, CONFIG_FILE

SECONDS_IN_90_DAYS = 90 * 24 * 3600
SECONDS_IN_30_DAYS = 30 * 24 * 3600
MAX_FILE_SIZE = 5 * 1024 * 1024   # 5 MB
MIN_FILE_SIZE = 1 * 1024          # 1 KB
FILE_TYPE_MAP = get_config(CONFIG_FILE)
EXTENSIONS_LIST = [
    f"{ext}"
    for ext in FILE_TYPE_MAP.keys()
    if ext != "_README_"
]


def setup_parser():
    """Defines and sets up the command line interface using argparse."""
    parser = argparse.ArgumentParser(
        description='Generate sample files for testing the file organizer.',
        epilog='Example usage: python3 generate_files.py sample_dir --num-files 20'
    )
    parser.add_argument('base_dir', help='Base directory to create sample files in')
    parser.add_argument('-n', '--num-files', type=int, default=10, help='Number of sample files to generate (default: 10)')
    parser.add_argument('--clean', action='store_true', help='Clean the base directory before generating files')
    return parser

def generate_sample_files(base_dir, num_files=10, clean=False):
    if clean:
        try:
            rmtree(base_dir)
            print(f"Cleaned existing directory: {base_dir}")
        except FileNotFoundError:
            pass  # Directory does not exist, nothing to clean
    base_path = Path(base_dir)
    base_path.mkdir(parents=True, exist_ok=True)

    now = time()
    time_90_days_ago = now - SECONDS_IN_90_DAYS
    time_30_days_ago = now - SECONDS_IN_30_DAYS

    for i in range(num_files):
        extension = choice(EXTENSIONS_LIST)
        file_path = base_path / f"sample_file_{i+1}.{extension}"

        file_size = randint(MIN_FILE_SIZE, MAX_FILE_SIZE)
        with open(file_path, 'wb') as f:
            f.write(randbytes(file_size))

        file_mtime = uniform(time_90_days_ago, time_30_days_ago)
        file_atime = uniform(time_30_days_ago, now)

        os.utime(file_path, (file_atime, file_mtime))
        
if __name__ == "__main__":
    parser = setup_parser()
    args = parser.parse_args()
    generate_sample_files(args.base_dir, args.num_files, args.clean)