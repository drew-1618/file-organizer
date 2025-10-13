import json
import logging
from pathlib import Path
import sys
from datetime import datetime, timedelta


RULES_FILE = "config/rules.json"
MEGABYTE = 1024 * 1024

def load_rules(rules_path):
    """Loads rules from a JSON file."""
    rules_path = Path(rules_path)
    if not rules_path.exists():
        logging.error(f"Rules file at {rules_path} not found. Proceeding with default behavior.")
        return []

    try:
        with open(rules_path, 'r') as f:
            rules = json.load(f)
        if not isinstance(rules, list):
            logging.error(f"Rules file format invalid. Expected a list of rules. Proceeding with default behavior.")
            return []

        valid_rules = []
        for i, rule in enumerate(rules):
            if not isinstance(rule, dict) or 'filters' not in rule or 'action' not in rule:
                logging.warning(f"Rule at index {i} is malformed (missing 'filters' or 'action'). Skipping.")
                continue
            rule['priority'] = rule.get('priority', 0)  # Default priority if not specified
            valid_rules.append(rule)

        valid_rules.sort(key=lambda r: r['priority'], reverse=True)
        logging.info(f"Successfully validated and loaded {len(valid_rules)} custom rules from {rules_path}.")
        return valid_rules

    except json.JSONDecodeError as e:
        logging.error(f"Failed to parse rules file {rules_path.name}. Check JSON syntax. Error: {e}. Proceeding with default behavior.")
        return []
    except Exception as e:
        logging.error(f"An unexpected error occurred while loading rules: {e}")
        return []


def find_matching_rule(file_path, custom_rules):
    """Finds the highest priority rule that matches the given file."""
    for rule in custom_rules:
        all_filters_match = True
        for filter_type, filter_value in rule['filters'].items():
            if not _check_filter(file_path, filter_type, filter_value):
                all_filters_match = False
                break  # Failed one filter, go to next rule
        if all_filters_match:
            logging.info(f"File '{file_path.name}' matched custom rule: '{rule.get('name', 'Unnamed Rule')}'")
            return rule  # Return highest priority matching rule
    return None  # No matching rule found


def _check_filter(file_path, filter_type, filter_value):
    """Checks if a specific filter matches the file."""
    # Gather metadata
    try:
        file_stat = file_path.stat()
        file_size = file_stat.st_size
        file_mtime = datetime.fromtimestamp(file_stat.st_mtime)
    except OSError:
        # File vanished or access denied
        return False

    if filter_type == 'extensions':
        file_ext = file_path.suffix.lower().lstrip('.')
        if isinstance(filter_value, list):
            return file_ext in [ext.lower().lstrip('.') for ext in filter_value]
        return file_ext == str(filter_value).lower().lstrip('.')

    # Case insensitive
    elif filter_type == 'filename_contains':
        filter_str = str(filter_value).lower()
        if not filter_str: 
            return True 
        return filter_str in file_path.name.lower()

    elif filter_type == "filename_starts_with":
        return file_path.name.lower().startswith(str(filter_value).lower())

    elif filter_type == "filename_ends_with":
        return file_path.name.lower().endswith(str(filter_value).lower())

    elif filter_type == 'min_size_mb':
        # Convert MB to bytes for comparison
        try:
            min_size_bytes = int(filter_value) * MEGABYTE
            return file_size >= min_size_bytes
        except ValueError:
            logging.warning(f"Invalid size value for min_size_mb: {filter_value}")
            return False

    elif filter_type == 'older_than_days':
        try:
            days = int(filter_value)
            threshold = datetime.now() - timedelta(days=filter_value)
            return file_mtime <= threshold
        except ValueError:
            logging.warning(f"Invalid day value for older_than_days: {filter_value}")
            return False

    elif filter_type == 'newer_than_days':
        try:
            days = int(filter_value)
            threshold = datetime.now() - timedelta(days=filter_value)
            return file_mtime >= threshold
        except ValueError:
            logging.warning(f"Invalid day value for newer_than_days: {filter_value}")
            return False
    # Default: no filter
    logging.warning(f"Unsupported filter type: {filter_type}. Assuming no match.")
    return False
