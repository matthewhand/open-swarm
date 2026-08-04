---
name: counting-lines
description: Counts the non-blank lines in a file using the bundled count.py script. Use when asked for an exact line count of a file, where guessing is unacceptable.
---

# Counting Lines

Do not estimate or eyeball line counts — run the bundled script, which is the
source of truth.

## Steps

1. Run the script on the target file:

   ```bash
   python3 count.py <path>
   ```

2. Report the exact integer it prints. If the script errors, report the error
   verbatim rather than guessing a number.
