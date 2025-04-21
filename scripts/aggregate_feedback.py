import sys
from pathlib import Path
import re

def aggregate_feedback(feedback_dir):
    summary = {
        'satisfaction': [],
        'likes': [],
        'improvements': [],
        'spinner': [],
        'progress_updates': [],
        'suggestions': [],
        'distinction': [],
        'result_counts': [],
        'confusion': [],
        'cli_features': [],
        'pain_points': [],
        'comments': []
    }
    for file in Path(feedback_dir).glob('*.md'):
        text = file.read_text()
        # Simple regex-based extraction for survey questions
        satisfaction = re.findall(r'satisfied.*?([1-5])', text, re.I)
        if satisfaction:
            summary['satisfaction'].extend(satisfaction)
        for key, pattern in [
            ('likes', r'like most.*?\n(.*?)\n'),
            ('improvements', r'would you improve.*?\n(.*?)\n'),
            ('spinner', r'spinner messages.*?\n(.*?)\n'),
            ('progress_updates', r'periodic line/result updates.*?\n(.*?)\n'),
            ('suggestions', r'suggestions for additional progress.*?\n(.*?)\n'),
            ('distinction', r'distinction between code search.*?\n(.*?)\n'),
            ('result_counts', r'result counts.*?\n(.*?)\n'),
            ('confusion', r'confusion.*?\n(.*?)\n'),
            ('cli_features', r'features would you like to see.*?\n(.*?)\n'),
            ('pain_points', r'pain points.*?\n(.*?)\n'),
            ('comments', r'Additional Comments.*?\n(.*?)\n')
        ]:
            found = re.findall(pattern, text, re.I | re.S)
            if found:
                summary[key].extend([f.strip() for f in found if f.strip()])
    # Print simple summary
    print("Aggregated User Feedback Summary:")
    for key, values in summary.items():
        print(f"\n## {key.replace('_', ' ').title()}:")
        if values:
            for v in values:
                print(f"- {v}")
        else:
            print("- (No responses)")

if __name__ == "__main__":
    feedback_dir = sys.argv[1] if len(sys.argv) > 1 else "user_feedback"
    aggregate_feedback(feedback_dir)
