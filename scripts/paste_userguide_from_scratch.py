#!/usr/bin/env python3
"""
Marker-driven exact paste for USERGUIDE.md (and README.md).
Insert before a ```text block:
<!-- from-scratch: wizard-capture.txt -->
```text
...old...
```
It replaces the body with exact content of $SCRATCH/wizard-capture.txt (stripped? but keep structure).

Run after fresh captures, before tests.
Never hand-edit the fenced output.
"""
import re
import os
import sys

def main():
    scratch = os.environ.get("SCRATCH", "/tmp/grok-goal-4567a1afab94/implementer")
    if not os.path.isdir(scratch):
        print("SCRATCH not found", scratch, file=sys.stderr)
        sys.exit(1)

    for mdfile in ["USERGUIDE.md", "README.md"]:
        if not os.path.exists(mdfile):
            continue
        with open(mdfile) as f:
            content = f.read()

        # find all markers and following ```text ... ```
        # pattern: marker comment then ```text\n ... \n```
        def replacer(match):
            marker = match.group(1).strip()
            fname = marker
            fpath = os.path.join(scratch, fname)
            if not os.path.exists(fpath):
                print(f"WARNING: no {fpath} for marker", file=sys.stderr)
                return match.group(0)  # leave as-is
            with open(fpath) as ff:
                newbody = ff.read().rstrip("\n")
            # preserve the fence style
            return f"<!-- from-scratch: {marker} -->\n```text\n{newbody}\n```"

        # match optional whitespace, the comment, then the fenced block
        pattern = r'<!--\s*from-scratch:\s*([^\s>]+?)\s*-->\s*```text\n(.*?)\n```'
        new_content, n = re.subn(pattern, replacer, content, flags=re.DOTALL)
        if n:
            with open(mdfile, "w") as f:
                f.write(new_content)
            print(f"Updated {n} block(s) in {mdfile} from {scratch}")
        else:
            print(f"No from-scratch markers updated in {mdfile}")

if __name__ == "__main__":
    main()
