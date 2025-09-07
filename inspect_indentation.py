import os

file_path = "/mnt/models/open-swarm-mcp/src/swarm/blueprints/echocraft/blueprint_echocraft.py"
start_line = 220  # A few lines before the error
end_line = 240    # A few lines after the error

if not os.path.exists(file_path):
    print(f"Error: File not found at {file_path}")
else:
    with open(file_path, 'rb') as f: # Open in binary mode to preserve raw bytes
        lines = f.readlines()

    print(f"--- Inspecting indentation for {file_path} (Lines {start_line}-{end_line}) ---")
    print("Legend: '.' = space, '->' = tab, '\n' = newline")
    print("-" * 80)

    for i, line_bytes in enumerate(lines):
        line_num = i + 1
        if start_line <= line_num <= end_line:
            try:
                line_str = line_bytes.decode('utf-8')
            except UnicodeDecodeError:
                line_str = f"<UNDECODABLE BYTES: {line_bytes}>"

            # Replace spaces with dots and tabs with arrows for visual inspection
            visual_line = line_str.replace(' ', '.').replace('\t', '->').rstrip('\n')

            # Get raw representation to show all escape sequences
            raw_line = repr(line_bytes)[2:-1] # Remove b'' and trailing newline repr

            print(f"Line {line_num}:")
            print(f"  Visual: '{visual_line}'")
            print(f"  Raw:    '{raw_line}'")
            print("-" * 80)

