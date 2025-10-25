from pathlib import Path
import shutil
import tempfile
from behave import fixture, register_type


def parse_flags(text):
    """Converts a space-separated string of flags into a list."""
    if text:
        # Splits the string by space, strips whitespace, and filters out empty strings
        return [flag.strip() for flag in text.split(' ') if flag.strip()]
    return []

register_type(Flags=parse_flags)


TEMP_ROOT_DIR = Path(tempfile.gettempdir()) / "behave_temp"

def before_scenario(context, scenario):
    # Ensure a clean state
    if TEMP_ROOT_DIR.exists():
        shutil.rmtree(TEMP_ROOT_DIR)
    # Define testing directories
    context.source_dir = TEMP_ROOT_DIR / "source"
    context.dest_dir = TEMP_ROOT_DIR / "destination"
    # Create necessary directories
    context.source_dir.mkdir(parents=True, exist_ok=True)
    context.dest_dir.mkdir(parents=True, exist_ok=True)

# cleanup hook
def after_scenario(context, scenario):
    if TEMP_ROOT_DIR.exists():
        shutil.rmtree(TEMP_ROOT_DIR)