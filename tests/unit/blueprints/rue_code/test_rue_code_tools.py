import unittest
import os
import subprocess
import re
from unittest.mock import patch, mock_open, MagicMock, call

# Import functions directly from the blueprint file
# Adjust path if necessary based on test runner's working directory
from blueprints.rue_code.blueprint_rue_code import (
    execute_command, read_file, write_to_file, apply_diff, search_files, list_files, prepare_git_commit
)

@unittest.skip('Skipping tool tests until FunctionTool interaction is refactored')
class TestRueCodeTools(unittest.TestCase):

    def setUp(self):
        # Mock CWD to control file operations
        self.mock_cwd = "/fake/cwd"
        patcher = patch('os.getcwd', return_value=self.mock_cwd)
        self.addCleanup(patcher.stop)
        self.mock_os_getcwd = patcher.start()

    @patch('subprocess.run')
    def test_execute_command_success(self, mock_run):
        """Test successful command execution."""
        mock_process = MagicMock()
        mock_process.returncode = 0
        mock_process.stdout = "Success output"
        mock_process.stderr = ""
        mock_run.return_value = mock_process

        result = execute_command("echo 'hello'")
        mock_run.assert_called_once_with("echo 'hello'", capture_output=True, text=True, timeout=60, check=False, shell=True)
        self.assertEqual(result, "Exit: 0\nSTDOUT:\nSuccess output\nSTDERR:")

    @patch('subprocess.run')
    def test_execute_command_error(self, mock_run):
        """Test command execution with non-zero exit code."""
        mock_process = MagicMock()
        mock_process.returncode = 1
        mock_process.stdout = ""
        mock_process.stderr = "Error message"
        mock_run.return_value = mock_process

        result = execute_command("invalid_command")
        self.assertEqual(result, "Exit: 1\nSTDOUT:\n\nSTDERR:\nError message")

    @patch('subprocess.run', side_effect=Exception("Subprocess failed"))
    def test_execute_command_exception(self, mock_run):
        """Test exception during command execution."""
        result = execute_command("some_command")
        self.assertTrue(result.startswith("Error: Subprocess failed"))

    def test_execute_command_empty(self):
        """Test empty command string."""
        result = execute_command("")
        self.assertEqual(result, "Error: No command.")

    @patch("builtins.open", new_callable=mock_open, read_data="line1\nline2")
    def test_read_file_success(self, mock_file):
        """Test reading a file successfully."""
        file_path = "test.txt"
        result = read_file(file_path)
        # mock_open doesn't handle absolute paths well by default with os.path.abspath
        # We rely on the function logic to form the path passed to open
        mock_file.assert_called_once_with(file_path, "r", encoding="utf-8")
        self.assertEqual(result, "line1\nline2")

    @patch("builtins.open", new_callable=mock_open, read_data="line1\nline2")
    def test_read_file_with_line_numbers(self, mock_file):
        """Test reading a file with line numbers."""
        result = read_file("test.txt", include_line_numbers=True)
        self.assertEqual(result, "1: line1\n2: line2")

    @patch("builtins.open", side_effect=FileNotFoundError("File vanished"))
    def test_read_file_not_found(self, mock_file):
        """Test reading a non-existent file."""
        result = read_file("nonexistent.txt")
        self.assertEqual(result, "Error: File not found at path: nonexistent.txt")

    # Note: Testing write/diff requires more complex mocking if we strictly enforce CWD checks
    # For simplicity, we'll mock os.path.abspath within the test if needed

    @patch("os.makedirs")
    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.abspath")
    def test_write_to_file_success(self, mock_abspath, mock_file, mock_makedirs):
        """Test writing to a file successfully within mocked CWD."""
        file_path = "output/new_file.txt"
        content = "Hello there!"
        full_path = os.path.join(self.mock_cwd, "output/new_file.txt")
        mock_abspath.return_value = full_path # Ensure abspath returns within mock CWD

        result = write_to_file(file_path, content)

        mock_abspath.assert_called_once_with(file_path)
        mock_makedirs.assert_called_once_with(os.path.dirname(full_path), exist_ok=True)
        mock_file.assert_called_once_with(full_path, "w", encoding="utf-8")
        mock_file().write.assert_called_once_with(content)
        self.assertEqual(result, f"OK: Wrote to {file_path}.")


    @patch("os.path.abspath")
    def test_write_to_file_outside_cwd(self, mock_abspath):
        """Test attempting to write outside CWD."""
        file_path = "../outside.txt"
        # Make abspath return something NOT starting with the mocked CWD
        mock_abspath.return_value = "/fake/other_dir/outside.txt"

        result = write_to_file(file_path, "secret data")
        self.assertTrue(result.startswith("Error: Cannot write outside current working directory"))


    # apply_diff combines read and write, requires mocking both + os.path.exists
    @patch("blueprints.rue_code.blueprint_rue_code.read_file")
    @patch("blueprints.rue_code.blueprint_rue_code.write_to_file")
    @patch("os.path.exists")
    @patch("os.path.abspath")
    def test_apply_diff_success(self, mock_abspath, mock_exists, mock_write, mock_read):
        """Test applying a successful diff."""
        file_path = "file_to_diff.py"
        full_path = os.path.join(self.mock_cwd, file_path)
        mock_abspath.return_value = full_path
        mock_exists.return_value = True
        mock_read.return_value = "Original content with old_text."
        mock_write.return_value = f"OK: Wrote to {file_path}." # Simulate success

        result = apply_diff(file_path, "old_text", "new_text")

        mock_read.assert_called_once_with(file_path)
        mock_write.assert_called_once_with(file_path, "Original content with new_text.")
        self.assertEqual(result, f"OK: Applied diff to {file_path}.")


    @patch("os.walk")
    @patch("builtins.open", new_callable=mock_open, read_data="Content with MATCH.")
    @patch("os.path.abspath")
    def test_list_files_recursive(self, mock_abspath, mock_file, mock_walk):
        """Test listing files recursively."""
        mock_abspath.return_value = self.mock_cwd # Ensure search starts within CWD
        # Simulate os.walk output
        mock_walk.return_value = [
            (self.mock_cwd, ['subdir', '.hidden_dir'], ['file1.txt', '.hidden_file']),
            (os.path.join(self.mock_cwd, 'subdir'), [], ['file2.py']),
        ]

        result = list_files(".")
        expected_files = sorted(["file1.txt", "subdir/file2.py"]) # Sorted, no hidden
        self.assertEqual(result, "Files found:\n" + "\n".join(expected_files))
        mock_walk.assert_called_once_with(self.mock_cwd)


    # prepare_git_commit requires mocking execute_command (which mocks subprocess.run)
    @patch("blueprints.rue_code.blueprint_rue_code.execute_command")
    def test_prepare_git_commit_success(self, mock_exec_cmd):
        """Test successful git commit sequence."""
        # Simulate output of mocked execute_command
        mock_exec_cmd.side_effect = [
            "Exit: 0\nSTDOUT:\nM modified_file.txt\nSTDERR:", # git status shows changes
            "Exit: 0\nSTDOUT:\n\nSTDERR:",                 # git add successful
            "Exit: 0\nSTDOUT:\n[main 1234567] Test commit\n 1 file changed, 1 insertion(+)\nSTDERR:", # git commit successful
        ]
        commit_msg = "Test commit"
        result = prepare_git_commit(commit_msg, add_all=True)

        expected_calls = [
            call("git status --porcelain"),
            call("git add ."),
            call('git commit -m "Test commit"'),
        ]
        mock_exec_cmd.assert_has_calls(expected_calls)
        self.assertTrue(result.startswith("OK: Committed 'Test commit'."))

    @patch("blueprints.rue_code.blueprint_rue_code.execute_command")
    def test_prepare_git_commit_no_changes(self, mock_exec_cmd):
        """Test git commit when there are no changes."""
        mock_exec_cmd.return_value = "Exit: 0\nSTDOUT:\n\nSTDERR:" # git status shows no changes
        result = prepare_git_commit("No changes commit")
        mock_exec_cmd.assert_called_once_with("git status --porcelain")
        self.assertEqual(result, "No changes detected to commit.")


if __name__ == '__main__':
    unittest.main()
