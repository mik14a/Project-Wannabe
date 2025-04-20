import json
import os
from typing import Dict, Any, Optional

# Define the structure of the project data
ProjectData = Dict[str, Any]

class ProjectIOError(Exception):
    """Custom exception for project I/O errors."""
    pass

def save_project_data(filepath: str, data: ProjectData):
    """
    Saves the project data (details, main text, memo) to a JSON file.

    Args:
        filepath: The path to save the JSON file.
        data: A dictionary containing the project data.
              Expected keys: 'details', 'main_text', 'memo_text'.

    Raises:
        ProjectIOError: If an error occurs during saving.
    """
    try:
        # Ensure the directory exists
        dirpath = os.path.dirname(filepath)
        if dirpath: # Only create if not saving to root
            os.makedirs(dirpath, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=4, ensure_ascii=False)
        print(f"Project data saved successfully to: {filepath}") # Debug log
    except IOError as e:
        raise ProjectIOError(f"Failed to save project data to {filepath}: {e}")
    except Exception as e:
        raise ProjectIOError(f"An unexpected error occurred while saving project data: {e}")

def load_project_data(filepath: str) -> ProjectData:
    """
    Loads project data from a JSON file.

    Args:
        filepath: The path to the JSON file to load.

    Returns:
        A dictionary containing the loaded project data.
        Expected keys: 'details', 'main_text', 'memo_text'.
        Returns an empty dict if file not found or error occurs.

    Raises:
        ProjectIOError: If the file is not found or cannot be parsed.
    """
    if not os.path.exists(filepath):
        raise ProjectIOError(f"Project file not found: {filepath}")

    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            data: ProjectData = json.load(f)
            # Basic validation (can be expanded)
            if not isinstance(data, dict):
                 raise ProjectIOError("Invalid project file format: Not a JSON object.")
            # Check for expected top-level keys (optional but recommended)
            # if 'details' not in data or 'main_text' not in data or 'memo_text' not in data:
            #     print("Warning: Loaded project data might be missing expected keys.")
            print(f"Project data loaded successfully from: {filepath}") # Debug log
            return data
    except json.JSONDecodeError as e:
        raise ProjectIOError(f"Failed to parse project file {filepath}: Invalid JSON format. {e}")
    except IOError as e:
        raise ProjectIOError(f"Failed to read project file {filepath}: {e}")
    except Exception as e:
        raise ProjectIOError(f"An unexpected error occurred while loading project data: {e}")


def save_output_text(filepath: str, output_text: str, include_title: bool = False, title: Optional[str] = None):
    """
    Saves the output text content to a plain text file.

    Args:
        filepath: The path to save the text file.
        output_text: The string content from the output area.
        include_title: Whether to prepend the title to the file.
        title: The project title (required if include_title is True).

    Raises:
        ProjectIOError: If an error occurs during saving.
    """
    if include_title and not title:
         raise ValueError("Title must be provided if include_title is True.")

    try:
        # Ensure the directory exists
        dirpath = os.path.dirname(filepath)
        if dirpath:
            os.makedirs(dirpath, exist_ok=True)

        with open(filepath, 'w', encoding='utf-8') as f:
            if include_title and title:
                f.write(f"# {title}\n\n") # Ensure double newline after title
            f.write(output_text)
        print(f"Output text saved successfully to: {filepath}") # Debug log
    except IOError as e:
        raise ProjectIOError(f"Failed to save output text to {filepath}: {e}")
    except Exception as e:
        raise ProjectIOError(f"An unexpected error occurred while saving output text: {e}")

# Example Usage (for testing)
if __name__ == "__main__":
    test_data = {
        "details": {
            "title": "テストプロジェクト",
            "keywords": ["テスト", "JSON"],
            "genres": ["サンプル"],
            "synopsis": "これはテスト用のあらすじです。",
            "setting": "テスト用の設定。",
            "plot": "テスト用のプロット。"
        },
        "main_text": "これは本文エリアのテストテキストです。\n複数行あります。",
        "memo_text": "これはメモエリアのテストテキストです。"
    }
    test_output = "これは出力エリアのテストテキストです。\nLLMからの生成結果。\n改行も含まれます。"
    save_dir = "test_saves"
    project_file = os.path.join(save_dir, "test_project.json")
    output_file_no_title = os.path.join(save_dir, "test_output_no_title.txt")
    output_file_with_title = os.path.join(save_dir, "test_output_with_title.txt")

    try:
        # Test saving project data
        print(f"\nSaving project data to {project_file}...")
        save_project_data(project_file, test_data)

        # Test loading project data
        print(f"\nLoading project data from {project_file}...")
        loaded_data = load_project_data(project_file)
        print("Loaded data:", json.dumps(loaded_data, indent=2, ensure_ascii=False))
        assert loaded_data == test_data

        # Test saving output without title
        print(f"\nSaving output text (no title) to {output_file_no_title}...")
        save_output_text(output_file_no_title, test_output)
        with open(output_file_no_title, 'r', encoding='utf-8') as f:
            assert f.read() == test_output

        # Test saving output with title
        print(f"\nSaving output text (with title) to {output_file_with_title}...")
        save_output_text(output_file_with_title, test_output, include_title=True, title=test_data["details"]["title"])
        with open(output_file_with_title, 'r', encoding='utf-8') as f:
            expected_content = f"# {test_data['details']['title']}\n\n{test_output}"
            assert f.read() == expected_content

        print("\nAll project_io tests passed!")

    except (ProjectIOError, ValueError, AssertionError) as e:
        print(f"\nError during project_io test: {e}")
    finally:
        # Clean up test files/directory
        # import shutil
        # if os.path.exists(save_dir):
        #     shutil.rmtree(save_dir)
        #     print(f"\nCleaned up test directory: {save_dir}")
        pass # Keep files for manual inspection if needed
