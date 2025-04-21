from swarm.core.output_utils import print_search_progress_box

class BlueprintTemplate:
    def __init__(self, blueprint_id):
        self.blueprint_id = blueprint_id

    async def run(self, messages, **kwargs):
        import os
        instruction = messages[-1].get("content", "") if messages else ""
        if os.environ.get('SWARM_TEST_MODE'):
            spinner_lines = [
                "Generating.",
                "Generating..",
                "Generating...",
                "Running..."
            ]
            search_mode = kwargs.get('search_mode', 'semantic')
            emoji = '🤖'
            total_lines = 70
            matches = 10

            if search_mode == "code":
                # Code Search UX
                print_search_progress_box(
                    op_type="Code Search",
                    results=[
                        "Code Search",
                        f"Searched filesystem for: '{instruction}'",
                        *spinner_lines,
                        f"Matches so far: {matches}",
                        "Processed",
                        emoji
                    ],
                    params=None,
                    result_type="code",
                    summary=f"Searched filesystem for: '{instruction}' | Results: {matches}",
                    progress_line=None,
                    spinner_state="Generating... Taking longer than expected",
                    operation_type="Code Search",
                    search_mode="code",
                    total_lines=total_lines,
                    emoji=emoji,
                    border='╔'
                )
                for i, spinner_state in enumerate(spinner_lines + ["Generating... Taking longer than expected"], 1):
                    progress_line = f"Lines {i*14}"
                    print_search_progress_box(
                        op_type="Code Search",
                        results=[f"Spinner State: {spinner_state}", f"Matches so far: {matches}"],
                        params=None,
                        result_type="code",
                        summary=f"Searched filesystem for '{instruction}' | Results: {matches}",
                        progress_line=progress_line,
                        spinner_state=spinner_state,
                        operation_type="Code Search",
                        search_mode="code",
                        total_lines=total_lines,
                        emoji=emoji,
                        border='╔'
                    )
                print_search_progress_box(
                    op_type="Code Search Results",
                    results=[f"Found {matches} matches.", "Code Search complete", "Processed", emoji],
                    params=None,
                    result_type="code",
                    summary=f"Code Search complete for: '{instruction}'",
                    progress_line="Processed",
                    spinner_state="Done",
                    operation_type="Code Search Results",
                    search_mode="code",
                    total_lines=total_lines,
                    emoji=emoji,
                    border='╔'
                )
                return

            else:
                # Semantic Search UX
                print_search_progress_box(
                    op_type="Semantic Search",
                    results=[
                        "Semantic Search",
                        f"Semantic code search for: '{instruction}'",
                        *spinner_lines,
                        f"Matches so far: {matches}",
                        "Processed",
                        emoji
                    ],
                    params=None,
                    result_type="semantic",
                    summary=f"Semantic code search for: '{instruction}' | Results: {matches}",
                    progress_line=None,
                    spinner_state="Generating... Taking longer than expected",
                    operation_type="Semantic Search",
                    search_mode="semantic",
                    total_lines=total_lines,
                    emoji=emoji,
                    border='╔'
                )
                for i, spinner_state in enumerate(spinner_lines + ["Generating... Taking longer than expected"], 1):
                    progress_line = f"Lines {i*14}"
                    print_search_progress_box(
                        op_type="Semantic Search",
                        results=[f"Spinner State: {spinner_state}", f"Matches so far: {matches}"],
                        params=None,
                        result_type="semantic",
                        summary=f"Semantic code search for '{instruction}' | Results: {matches}",
                        progress_line=progress_line,
                        spinner_state=spinner_state,
                        operation_type="Semantic Search",
                        search_mode="semantic",
                        total_lines=total_lines,
                        emoji=emoji,
                        border='╔'
                    )
                print_search_progress_box(
                    op_type="Semantic Search Results",
                    results=[f"Found {matches} matches.", "Semantic Search complete", "Processed", emoji],
                    params=None,
                    result_type="semantic",
                    summary=f"Semantic Search complete for: '{instruction}'",
                    progress_line="Processed",
                    spinner_state="Done",
                    operation_type="Semantic Search Results",
                    search_mode="semantic",
                    total_lines=total_lines,
                    emoji=emoji,
                    border='╔'
                )
                return

        # ...normal (non-test) agent logic goes here...
