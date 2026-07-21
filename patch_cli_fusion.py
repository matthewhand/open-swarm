import re

with open('tests/api/test_cli_fusion_api.py', 'r') as f:
    content = f.read()

content = content.replace('"moa": {', '"cli_fusion": {')

with open('tests/api/test_cli_fusion_api.py', 'w') as f:
    f.write(content)
