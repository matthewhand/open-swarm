#!/usr/bin/env python3

import os
import glob

def main():
    blueprints_dir = 'blueprints'
    system_tests_dir = os.path.join('tests', 'system')
    os.makedirs(system_tests_dir, exist_ok=True)

    for d in os.listdir(blueprints_dir):
        subdir = os.path.join(blueprints_dir, d)
        if os.path.isdir(subdir):
            pattern = os.path.join(subdir, 'blueprint_*.py')
            files = glob.glob(pattern)
            if files:
                blueprint_file = os.path.basename(files[0])
                test_file_path = os.path.join(system_tests_dir, f'test_{d}.sh')
                if not os.path.exists(test_file_path):
                    command = f'echo -e "what is your purpose\\n/quit" | python {os.path.join(blueprints_dir, d, blueprint_file)}'
                    with open(test_file_path, 'w') as f:
                        f.write("#!/bin/bash\n")
                        f.write(command + "\n")
                    os.chmod(test_file_path, 0o755)
                    print(f"Created test: {test_file_path}")
                else:
                    print(f"Test already exists: {test_file_path}")

if __name__ == '__main__':
    main()