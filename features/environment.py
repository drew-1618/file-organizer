from pathlib import Path
import shutil
from behave import fixture, register_type


def parse_flags(text):
    """Converts a space-separated string of flags into a list."""
    if text:
        # Splits the string by space, strips whitespace, and filters out empty strings
        return [flag.strip() for flag in text.split(' ') if flag.strip()]
    return []

register_type(Flags=parse_flags)


# cleanup hook
def after_scenario(context, scenario):
    if hasattr(context, 'source_dir') and context.source_dir.exists():
        shutil.rmtree(context.source_dir)