import pytest
from unittest.mock import patch
from swarm.extensions.cli.selection import prompt_user_to_select_blueprint

@patch("builtins.input", return_value="1")
def test_valid_input(mock_input):
    blueprints_metadata = {
        "blueprint1": {
            "title": "Blueprint One",
            "description": "The first blueprint.",
        },
        "blueprint2": {
            "title": "Blueprint Two",
            "description": "The second blueprint.",
        },
    }

    with patch("builtins.print") as mock_print:
        result = prompt_user_to_select_blueprint(blueprints_metadata)

        # Verify the selected blueprint
        assert result == "blueprint1", "The selected blueprint should match the user input."

        # Verify that the print statement for "Available Blueprints:" is present
        assert any(
            call_args[0][0].strip() == "Available Blueprints:"
            for call_args in mock_print.call_args_list
        ), "Expected 'Available Blueprints:' to be printed."


@patch("builtins.input", return_value="0")
def test_cancel_selection_returns_none(mock_input):
    blueprints_metadata = {
        "alpha": {"title": "Alpha", "description": "First"},
        "beta": {"title": "Beta", "description": "Second"},
    }

    with patch("builtins.print") as mock_print:
        result = prompt_user_to_select_blueprint(blueprints_metadata)
        assert result is None
        # Ensure prompt printed list header
        assert any(
            call.args and isinstance(call.args[0], str) and call.args[0].strip() == "Available Blueprints:"
            for call in mock_print.mock_calls
        )


def test_empty_metadata_returns_none_and_message():
    with patch("swarm.extensions.cli.selection.color_text", side_effect=lambda t, c: t):
        with patch("builtins.print") as mock_print:
            result = prompt_user_to_select_blueprint({})
            assert result is None
            # Message indicating no blueprints available is printed
            assert any(
                call.args and isinstance(call.args[0], str) and "No blueprints available" in call.args[0]
                for call in mock_print.mock_calls
            )


def test_invalid_input_then_valid_selection():
    # First an invalid string, then a valid choice '2'
    inputs = iter(["not-a-number", "2"])  # noqa: WPS317
    blueprints_metadata = {
        "one": {"title": "One", "description": "Desc"},
        "two": {"title": "Two", "description": "Desc"},
    }

    with patch("builtins.input", side_effect=lambda _: next(inputs)):
        with patch("builtins.print") as mock_print:
            selected = prompt_user_to_select_blueprint(blueprints_metadata)
            assert selected == "two"
            # Ensure it printed an invalid input message at least once
            assert any(
                call.args and isinstance(call.args[0], str) and "Invalid input" in call.args[0]
                for call in mock_print.mock_calls
            )


def test_out_of_range_then_valid_selection():
    # Out of range '9', then valid '1'
    inputs = iter(["9", "1"])  # noqa: WPS317
    blueprints_metadata = {
        "uno": {"title": "Uno", "description": "Desc"},
        "dos": {"title": "Dos", "description": "Desc"},
    }

    with patch("builtins.input", side_effect=lambda _: next(inputs)):
        with patch("builtins.print") as mock_print:
            selected = prompt_user_to_select_blueprint(blueprints_metadata)
            assert selected == "uno"
            # Ensure it guided user about allowed range
            assert any(
                call.args and isinstance(call.args[0], str) and "Please enter a number between" in call.args[0]
                for call in mock_print.mock_calls
            )
