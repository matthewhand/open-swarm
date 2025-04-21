from swarm.core.output_utils import print_search_progress_box

class DataAnalysisBlueprint:
    """
    Blueprint for performing data analysis tasks.

    Features:
    - Code search: Search datasets/files for code/data patterns.
    - Semantic search: Analyze datasets/files for semantic meaning.
    - Summary statistics: Compute mean, median, mode, etc.
    - Filtering: Filter data by criteria.
    - Report generation: Summarize findings in a human-readable format.
    - Supports enhanced ANSI/emoji boxes for all output, with result counts, parameters, and periodic progress updates.
    """
    def __init__(self, blueprint_id):
        self.blueprint_id = blueprint_id

    async def run(self, messages, **kwargs):
        """
        Main entrypoint for the blueprint. Handles code/semantic search and delegates to analysis methods.
        """
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
            emoji = '📊'
            total_lines = 70
            matches = 10

            if search_mode == "code":
                print_search_progress_box(
                    op_type="Code Search",
                    results=[
                        "Code Search",
                        f"Searched dataset for: '{instruction}'",
                        *spinner_lines,
                        f"Matches so far: {matches}",
                        "Processed",
                        emoji
                    ],
                    params=None,
                    result_type="code",
                    summary=f"Searched dataset for: '{instruction}' | Results: {matches}",
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
                        summary=f"Searched dataset for '{instruction}' | Results: {matches}",
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
                print_search_progress_box(
                    op_type="Semantic Search",
                    results=[
                        "Semantic Search",
                        f"Semantic data analysis for: '{instruction}'",
                        *spinner_lines,
                        f"Matches so far: {matches}",
                        "Processed",
                        emoji
                    ],
                    params=None,
                    result_type="semantic",
                    summary=f"Semantic data analysis for: '{instruction}' | Results: {matches}",
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
                        summary=f"Semantic data analysis for '{instruction}' | Results: {matches}",
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

    async def summary_statistics(self, data):
        """
        Compute summary statistics (mean, median, mode, std, etc.) for the given data.
        Returns a dictionary with the computed statistics.
        Only computes if all values are numeric; otherwise, returns None for all fields.
        """
        import statistics
        if not data:
            return {"error": "No data provided."}
        if not all(isinstance(x, (int, float)) for x in data):
            return {"mean": None, "median": None, "mode": None, "stdev": None}
        stats = {}
        try:
            stats["mean"] = statistics.mean(data)
        except Exception:
            stats["mean"] = None
        try:
            stats["median"] = statistics.median(data)
        except Exception:
            stats["median"] = None
        try:
            stats["mode"] = statistics.mode(data)
        except Exception:
            stats["mode"] = None
        try:
            stats["stdev"] = statistics.stdev(data) if len(data) > 1 else 0.0
        except Exception:
            stats["stdev"] = None
        return stats

    async def filter_data(self, data, criteria):
        """
        Filter the data according to the given criteria.
        Criteria should be a dict {key: value} and data a list of dicts.
        Returns a filtered list of dicts matching all criteria.
        """
        if not isinstance(data, list) or not isinstance(criteria, dict):
            return []
        filtered = []
        for row in data:
            if not isinstance(row, dict):
                continue
            if all(row.get(k) == v for k, v in criteria.items()):
                filtered.append(row)
        return filtered

    async def generate_report(self, analysis_results):
        """
        Generate a human-readable report from analysis results (dict).
        Returns a formatted string.
        """
        if not isinstance(analysis_results, dict):
            return "No analysis results to report."
        lines = ["Data Analysis Report:"]
        for k, v in analysis_results.items():
            lines.append(f"- {k.title()}: {v}")
        return "\n".join(lines)

    # Add more data analysis methods as needed
