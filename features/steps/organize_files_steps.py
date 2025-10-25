from pathlib import Path
import shutil
import subprocess
import sys
import os
import glob

from behave import given, when, then

def _execute_organizer(context):
    python_executable = sys.executable
    script_path = Path("src/organize.py")
    source_dir_path = context.source_dir.resolve()
    
    command = [
        python_executable,
        str(script_path),
        str(source_dir_path)
    ]
    
    if hasattr(context, 'flags') and context.flags:
        command.extend(context.flags) 
    
    context.process = subprocess.run(command, capture_output=True, text=True, check=False)


@given('a file of type "{ext}" exists in the source directory')
def step_impl(context, ext):
    if not hasattr(context, 'files_created'):
        context.files_created = {}

    context.filename = f"test_file.{ext}" 
    context.files_created[ext] = context.filename
    file_path = context.source_dir / context.filename
    file_path.touch()

@when('the organizer is run')
def step_impl(context):
    context.flags = []
    _execute_organizer(context)

@when('the organizer is run with the "{flags:Flags}" flag(s)')
def step_impl(context, flags):
    context.flags = flags
    _execute_organizer(context)

@then('the "{folder_name}" folder should exist')
def step_impl(context, folder_name):
    expected_folder_path = context.source_dir / folder_name
    assert expected_folder_path.is_dir(), f"Expected directory {expected_folder_path} does not exist."

@then('the "{folder_name}" folder should not exist')
def step_impl(context, folder_name):
    expected_folder_path = context.source_dir / folder_name
    assert not expected_folder_path.is_dir(), f"Expected directory {expected_folder_path} does exist."

@then('the "{ext}" file should be in the "{folder_name}" folder')
def step_impl(context, ext, folder_name):
    file_name_to_check = context.files_created[ext]
    expected_file_path = context.source_dir / folder_name / file_name_to_check
    assert expected_file_path.is_file(), f"Expected file {expected_file_path} does not exist."

@then('the "{ext}" file should be in the source directory')
def step_impl(context, ext):
    expected_file_path = context.source_dir / context.filename
    assert expected_file_path.is_file(), f"Expected file {expected_file_path} does not exist."

@then('the file should be in the "{folder_name}" folder with date "{status}" prefixing')
def step_impl(context, folder_name, status):
    destination_folder = context.source_dir / folder_name
    search_pattern = f"*-*-*_{context.filename}"
    found_files = list(destination_folder.glob(search_pattern))
    assert len(found_files) == 1, f"Expected exactly one date-prefixed file but instead found {len(found_files)}"
