#!/usr/bin/env python3
"""
Script to combine Python, JS, and JSON files into a single text file.
Excludes test files and specified directories.
"""

import os
import sys
from pathlib import Path


def should_exclude(path):
    """Check if a path should be excluded."""
    path_str = str(path)
    exclusions = [
        "/tests/", 
        "test_", 
        "/dist/",
        "/.archive_runtime/",
        "/.archived_runtime/",
        "/node_modules/",
        "/.mypy_cache/"
    ]
    return any(exclusion in path_str for exclusion in exclusions)


def get_files_by_extension(root_dir, extensions):
    """Get all files with specified extensions, excluding certain paths."""
    files = []
    for ext in extensions:
        for file_path in Path(root_dir).rglob(f"*.{ext}"):
            if not should_exclude(file_path):
                # For Python files, also exclude if they are test files
                if ext == "py":
                    if "test_" in file_path.name or "/tests/" in str(file_path):
                        continue
                files.append(file_path)
    return sorted(files)


def main():
    root_dir = "/home/erpnext/frappe-bench/apps/flexirule"
    output_file = "/home/erpnext/Documents/flexirule/combined_flexirule_14_1_2026.txt"
    
    # Get all Python, JS, JSON, and Vue files
    py_files = get_files_by_extension(root_dir, ["py"])
    js_files = get_files_by_extension(root_dir, ["js"])
    json_files = get_files_by_extension(root_dir, ["json"])
    vue_files = get_files_by_extension(root_dir, ["vue"])

    all_files = py_files + js_files + json_files + vue_files
    
    with open(output_file, 'w', encoding='utf-8') as outfile:
        for file_path in all_files:
            try:
                # Write the file path header
                outfile.write(f"=== {file_path} ===\n")
                
                # Read and write the file content
                with open(file_path, 'r', encoding='utf-8') as infile:
                    content = infile.read()
                    outfile.write(content)
                
                # Add a separator after each file's content
                outfile.write("\n\n")
                
                print(f"Processed: {file_path}")
            except Exception as e:
                print(f"Error processing {file_path}: {str(e)}")
                continue
    
    print(f"\nCombined file created: {output_file}")
    print(f"Total files processed: {len(all_files)}")


if __name__ == "__main__":
    main()