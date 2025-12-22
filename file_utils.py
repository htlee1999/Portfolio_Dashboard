"""
File operation utilities.
Centralized functions for directory and JSON file operations.
"""

import os
import json
import streamlit as st
from typing import Any, Optional


def ensure_directory(path: str) -> None:
    """
    Ensure a directory exists, creating it if necessary.

    Args:
        path: Directory path to ensure exists
    """
    os.makedirs(path, exist_ok=True)


def ensure_parent_directory(file_path: str) -> None:
    """
    Ensure the parent directory of a file path exists.

    Args:
        file_path: Path to a file whose parent directory should exist
    """
    parent_dir = os.path.dirname(file_path)
    if parent_dir:
        os.makedirs(parent_dir, exist_ok=True)


def load_json(file_path: str, default: Optional[Any] = None) -> Any:
    """
    Safely load a JSON file with error handling.

    Args:
        file_path: Path to the JSON file
        default: Default value to return if file doesn't exist or is invalid

    Returns:
        Parsed JSON data or default value
    """
    if default is None:
        default = {}

    try:
        if not os.path.exists(file_path):
            return default

        with open(file_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    except json.JSONDecodeError:
        return default
    except Exception:
        return default


def save_json(file_path: str, data: Any, indent: int = 2, show_errors: bool = True) -> bool:
    """
    Safely save data to a JSON file with directory creation.

    Args:
        file_path: Path to save the JSON file
        data: Data to serialize to JSON
        indent: JSON indentation level (default: 2)
        show_errors: Whether to show errors via st.error (default: True)

    Returns:
        True if successful, False otherwise
    """
    try:
        ensure_parent_directory(file_path)

        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=indent, default=str)

        return True
    except Exception as e:
        if show_errors:
            st.error(f"Error saving file: {str(e)}")
        return False


def file_exists(file_path: str) -> bool:
    """Check if a file exists."""
    return os.path.exists(file_path)


def get_file_size(file_path: str) -> int:
    """Get file size in bytes, returns 0 if file doesn't exist."""
    try:
        return os.path.getsize(file_path)
    except OSError:
        return 0


def get_file_modified_time(file_path: str) -> float:
    """Get file modification time, returns 0 if file doesn't exist."""
    try:
        return os.path.getmtime(file_path)
    except OSError:
        return 0
