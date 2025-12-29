class DiffFormatter:
    """Formats diff lines with ANSI colors"""

    @staticmethod
    def format_diff_lines(lines: list[str]) -> list[str]:
        """Add ANSI colors to diff lines"""
        formatted: list[str] = []
        for line in lines:
            if line.startswith('+'):
                formatted.append(f"\033[32m{line}\033[0m")  # Green
            elif line.startswith('-'):
                formatted.append(f"\033[31m{line}\033[0m")  # Red
            else:
                formatted.append(line)
        return formatted

class StatusFormatter:
    """Formats status messages with consistent styling"""

    @staticmethod
    def format_status_line(message: str, elapsed: int, tokens: int) -> str:
        """Format a status line with timing and token count"""
        return f"\033[38;5;183m{message}\033[0m\033[38;5;240m ({elapsed}s waited, {tokens} tokens)\033[0m"
