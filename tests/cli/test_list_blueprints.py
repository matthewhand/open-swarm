"""
Test case for the list_blueprints command.
"""
import argparse
import os
import pathlib
from pathlib import Path as RealPath

import pytest
from swarm.core import paths
from swarm.extensions.cli.commands.list_blueprints import Path as SutPathGlobal
from swarm.extensions.cli.commands.list_blueprints import execute, register_args


class MockBlueprintClass:
    """A mock class to act as a blueprint class type."""
    pass

MOCK_DISCOVERED_DATA = {
    "bp_user_1": {
        "class_type": MockBlueprintClass,
        "metadata": {
            "name": "User Blueprint Alpha",
            "abbreviation": "alpha",
            "version": "1.0.0",
            "description": "First user blueprint.",
            "author": "User"
        }
    },
    "bp_user_2": {
        "class_type": MockBlueprintClass,
        "metadata": {
            "name": "User Blueprint Beta",
            "version": "0.5.0",
            "description": "Second user blueprint, source only."
        }
    }
}

MOCK_AVAILABLE_DATA = {
    "avail_bp_1": {
        "class_type": MockBlueprintClass,
        "metadata": {
            "name": "Available Gamma",
            "abbreviation": "gamma",
            "version": "2.0.0",
            "description": "An available blueprint.",
            "author": "Package Maintainer"
        }
    },
    "avail_bp_no_abbr": {
        "class_type": MockBlueprintClass,
        "metadata": {
            "name": "Available Delta",
            "version": "1.0.0",
            "description": "Available, no abbreviation."
        }
    }
}

@pytest.fixture
def mock_basic_paths_env(mocker, tmp_path):
    user_blueprints_dir = tmp_path / "mock_user_blueprints"
    user_bin_dir = tmp_path / "mock_user_bin"
    user_blueprints_dir.mkdir(exist_ok=True)
    user_bin_dir.mkdir(exist_ok=True)

    mocker.patch.object(paths, 'get_user_blueprints_dir', return_value=user_blueprints_dir)
    mocker.patch.object(paths, 'get_user_bin_dir', return_value=user_bin_dir)

    return {
        "user_blueprints_dir": user_blueprints_dir,
        "user_bin_dir": user_bin_dir,
    }

_OriginalPosixPath_is_file = pathlib.PosixPath.is_file

def test_execute_list_user_installed(capsys, mocker, mock_basic_paths_env):
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args([])
    mocker.patch("swarm.extensions.cli.commands.list_blueprints.discover_blueprints", return_value=MOCK_DISCOVERED_DATA)

    user_bin_dir_real = mock_basic_paths_env["user_bin_dir"]
    compiled_exe_path_alpha_str = str(user_bin_dir_real / "alpha")
    compiled_exe_path_beta_str = str(user_bin_dir_real / "bp_user_2")

    print(f"DEBUG_TEST: user_bin_dir_real is type: {type(user_bin_dir_real)}")
    print(f"DEBUG_TEST: Target alpha path string: {compiled_exe_path_alpha_str}")
    print(f"DEBUG_TEST: Target beta path string: {compiled_exe_path_beta_str}")

    os_access_calls_log = []
    def custom_os_access(path_arg, mode):
        path_str = str(path_arg)
        os_access_calls_log.append(f"Path: '{path_str}', Mode: {mode}")
        print(f"DEBUG_MOCK: os.access called with path='{path_str}', mode={mode}")
        result = False
        if path_str == compiled_exe_path_alpha_str and mode == os.X_OK:
            result = True
        print(f"DEBUG_MOCK: os.access returning {result} for '{path_str}'")
        return result
    mocker.patch('os.access', side_effect=custom_os_access)

    is_file_calls_log = []
    def custom_posixpath_is_file_side_effect(self):
        path_str = str(self)
        is_file_calls_log.append(f"Path: '{path_str}'")

        if path_str == compiled_exe_path_alpha_str:
            print(f"DEBUG_MOCK: custom_posixpath_is_file for '{path_str}' (alpha) returning True")
            return True
        if path_str == compiled_exe_path_beta_str:
            print(f"DEBUG_MOCK: custom_posixpath_is_file for '{path_str}' (beta) returning False")
            return False

        print(f"DEBUG_MOCK: custom_posixpath_is_file for '{path_str}' (UNMATCHED) calling original.")
        return _OriginalPosixPath_is_file(self)

    mocker.patch('pathlib.PosixPath.is_file',
                 side_effect=custom_posixpath_is_file_side_effect,
                 autospec=True)

    execute(args)

    print("\nDEBUG_TEST: Calls to custom_posixpath_is_file during SUT execution:")
    for entry in is_file_calls_log:
        print(f"  {entry}")
    print("--- End of is_file calls ---\n")

    print("\nDEBUG_TEST: Calls to custom_os_access during SUT execution:")
    for entry in os_access_calls_log:
        print(f"  {entry}")
    print("--- End of os.access calls ---\n")

    captured = capsys.readouterr()
    output = captured.out

    assert f"Listing user-installed blueprints (source in {mock_basic_paths_env['user_blueprints_dir']})" in output
    assert f"Found {len(MOCK_DISCOVERED_DATA)} user-installed blueprint source(s):" in output
    assert "Key/ID: bp_user_1" in output
    assert "Name: User Blueprint Alpha" in output
    assert "Abbreviation: alpha" in output
    assert "Status: Compiled" in output
    assert "Key/ID: bp_user_2" in output
    assert "Name: User Blueprint Beta" in output
    assert "Abbreviation: N/A" not in output
    assert "Status: Source only" in output


def test_execute_list_available(capsys, mocker, mock_basic_paths_env):
    # mocker.stopall() # Keep this if other tests need a completely clean slate from this point
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(["--available"])
    mocker.patch("swarm.extensions.cli.commands.list_blueprints.discover_blueprints", return_value=MOCK_AVAILABLE_DATA)

    # Mock find_spec to simulate package not found, forcing dev path check
    mocker.patch("importlib.util.find_spec", return_value=None)

    # To ensure the dev path is also considered "not found" for this specific test variant,
    # we need to mock its .is_dir() check.
    # The dev_path_candidate in SUT is: Path(__file__).resolve().parent.parent.parent.parent / "blueprints"
    # We need to get the SUT's __file__ to construct this path accurately for mocking.
    sut_list_blueprints_file = RealPath(execute.__globals__['__file__'])
    expected_dev_path_candidate = sut_list_blueprints_file.resolve().parent.parent.parent.parent / "blueprints"

    original_is_dir = SutPathGlobal.is_dir # Get the original is_dir from SUT's Path
                                           # (which is likely PosixPath.is_dir)

    def mock_is_dir(self_path_instance):
        print(f"DEBUG_MOCK: mock_is_dir called for {self_path_instance}")
        if self_path_instance == expected_dev_path_candidate:
            print(f"DEBUG_MOCK: mock_is_dir returning False for dev path candidate: {self_path_instance}")
            return False
        # For other paths, especially those created by tmp_path, call original.
        # This check is tricky; be careful not to break tmp_path operations.
        # A safer way if original_is_dir is an unbound method:
        if hasattr(self_path_instance, '_raw_paths'): # Heuristic for actual Path objects
             return original_is_dir.__get__(self_path_instance, type(self_path_instance))()
        return False # Fallback for other mock types if any

    # Patch is_dir on the SUT's Path object (e.g. pathlib.PosixPath.is_dir)
    # We need to ensure this mock is specific enough not to break pytest's tmp_path.
    # A more robust way is to patch where it's used, if possible, or be very specific.
    # For now, let's try patching it on the class SUT uses.
    mocker.patch.object(SutPathGlobal, 'is_dir', side_effect=mock_is_dir, autospec=True)


    execute(args)
    captured = capsys.readouterr()
    output = captured.out
    print(f"DEBUG_TEST: Output for test_execute_list_available:\n{output}")
    assert "INFO: No available (package/development) blueprint source directory could be determined." in output
    assert "No available blueprints found in package or development source." in output


def test_execute_no_user_installed_blueprints(capsys, mocker, mock_basic_paths_env):
    # mocker.stopall() # Removed: Let mock_basic_paths_env apply for consistent path
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args([])
    # This mock ensures that even if the (mocked) user_bp_dir exists, no blueprints are "found"
    mocker.patch("swarm.extensions.cli.commands.list_blueprints.discover_blueprints", return_value={})

    # Ensure paths.get_user_blueprints_dir is using the mocked path from mock_basic_paths_env
    # This is already handled by mock_basic_paths_env if mocker.stopall() is removed.

    execute(args)
    captured = capsys.readouterr()
    output = captured.out
    print(f"DEBUG_TEST: Output for test_execute_no_user_installed_blueprints:\n{output}")
    # The SUT will use the path returned by the (mocked) paths.get_user_blueprints_dir()
    assert f"Listing user-installed blueprints (source in {mock_basic_paths_env['user_blueprints_dir']})" in output
    assert f"No user-installed blueprints found in {mock_basic_paths_env['user_blueprints_dir']}." in output


def test_execute_no_available_blueprints(capsys, mocker, mock_basic_paths_env):
    # This test asserts the message when a dev path IS found, but discover_blueprints returns {}
    # mocker.stopall() # Keep this if other tests need a completely clean slate from this point
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(["--available"])
    mocker.patch("swarm.extensions.cli.commands.list_blueprints.discover_blueprints", return_value={})

    # Simulate package not found
    mocker.patch("importlib.util.find_spec", return_value=None)

    # For this test, we assume the development path *is* found and is a directory.
    # The SUT will then call discover_blueprints (mocked to return {}),
    # leading to "No available blueprints found..."
    # We don't need to mock .is_dir() here if we want to test this specific branch.
    # The previous test_execute_list_available now tests the "could not be determined" branch.

    execute(args)
    captured = capsys.readouterr()
    output = captured.out
    print(f"DEBUG_TEST: Output for test_execute_no_available_blueprints:\n{output}")
    assert "Listing available blueprints (from package/development source)..." in output # This part should still appear
    assert "No available blueprints found in package or development source." in output
    assert "INFO: No available (package/development) blueprint source directory could be determined." not in output


def test_execute_discovery_exception_user_installed(capsys, mocker, mock_basic_paths_env):
    # mocker.stopall() # Let mock_basic_paths_env apply
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args([])
    mocker.patch("swarm.extensions.cli.commands.list_blueprints.discover_blueprints", side_effect=Exception("User Discovery Failed!"))
    execute(args)
    captured = capsys.readouterr()
    output = captured.out
    assert f"Listing user-installed blueprints (source in {mock_basic_paths_env['user_blueprints_dir']})" in output
    assert "An error occurred while listing user-installed blueprints: User Discovery Failed!" in output

def test_execute_discovery_exception_available(capsys, mocker, mock_basic_paths_env):
    # mocker.stopall() # Let mock_basic_paths_env apply for paths.get_user_blueprints_dir if it were used
    parser = argparse.ArgumentParser()
    register_args(parser)
    args = parser.parse_args(["--available"])

    # Assume a source directory IS found (e.g., dev path)
    mocker.patch("importlib.util.find_spec", return_value=None) # No package
    # Let dev path be found by default (its .is_dir() will be true)

    # Mock discover_blueprints to raise an exception
    mocker.patch("swarm.extensions.cli.commands.list_blueprints.discover_blueprints", side_effect=Exception("Available Discovery Failed!"))

    execute(args)
    captured = capsys.readouterr()
    output = captured.out
    assert "Listing available blueprints (from package/development source)..." in output
    assert "An error occurred while listing available blueprints: Available Discovery Failed!" in output
