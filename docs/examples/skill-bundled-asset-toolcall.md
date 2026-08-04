### Skill with a bundled executable asset (skills + tool calling)

The `counting-lines` skill ships a `count.py` script. Running it through the
`cli_agent` blueprint with `skill=counting-lines` stages `count.py` into the
CLI's working directory; the write-mode CLI then **executes** it to answer —
rather than guessing — and the result is verified independently.

**Setup:** `target.txt` has 12 lines, **7 non-blank** (blank lines make
eyeballing error-prone, so a correct answer is strong evidence the script ran).

**Live result** (`scripts/prove_skill_asset_toolcall.py grok gemini`):

```
Skill: counting-lines (ships count.py)  ·  target.txt non-blank lines = 7
  grok     PASS  staged=True answer~=['7']  **7** non-blank lines in `target.txt`.
  gemini   PASS  staged=True answer~=['7']  There are 7 non-blank lines in target.txt.
  2/2 CLIs staged + executed the bundled count.py
```

`staged=True` confirms `count.py` was copied into the workdir; the `7` answer
confirms each CLI executed it. Skills and tool calling compose across CLIs.
