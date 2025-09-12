#!/usr/bin/env python3
"""
Automated Blueprint Test Generator
==================================

This script generates comprehensive test suites for undertested blueprints
to help reach the 1337 test goal.
"""

import os
import re
from pathlib import Path

def get_blueprint_info(blueprint_name):
    """Extract blueprint class name and basic info from blueprint file."""
    blueprint_path = f"src/swarm/blueprints/{blueprint_name}"
    
    if not os.path.exists(blueprint_path):
        return None, None
    
    # Look for the main blueprint file
    main_file = None
    for filename in [f"blueprint_{blueprint_name}.py", f"{blueprint_name}.py"]:
        file_path = os.path.join(blueprint_path, filename)
        if os.path.exists(file_path):
            main_file = file_path
            break
    
    if not main_file:
        return None, None
    
    # Extract class name from file
    try:
        with open(main_file, 'r') as f:
            content = f.read()
        
        # Find blueprint class
        class_match = re.search(r'class\s+(\w*Blueprint\w*)\s*\(', content)
        if class_match:
            class_name = class_match.group(1)
            return class_name, main_file
    except:
        pass
    
    return None, None

def generate_blueprint_test(blueprint_name, class_name, template_path="tmp_rovodev_blueprint_test_template.py"):
    """Generate a test file for a specific blueprint using the template."""
    
    # Read template
    with open(template_path, 'r') as f:
        template_content = f.read()
    
    # Replace placeholders
    test_content = template_content.replace('{BLUEPRINT_NAME}', blueprint_name)
    test_content = test_content.replace('{BLUEPRINT_CLASS}', class_name)
    
    # Create specific imports and adjustments based on blueprint
    specific_imports = f"""
# Specific imports for {blueprint_name} blueprint
from src.swarm.blueprints.{blueprint_name}.blueprint_{blueprint_name} import {class_name}
"""
    
    # Replace the generic import
    test_content = test_content.replace(
        f"from src.swarm.blueprints.{blueprint_name}.blueprint_{blueprint_name} import {class_name}",
        specific_imports.strip()
    )
    
    return test_content

def get_undertested_blueprints():
    """Get list of blueprints that need more tests."""
    undertested = []
    
    # Get all blueprint directories
    blueprint_dirs = []
    for item in os.listdir('src/swarm/blueprints'):
        path = os.path.join('src/swarm/blueprints', item)
        if os.path.isdir(path) and item != '__pycache__':
            blueprint_dirs.append(item)
    
    # Check existing test counts
    blueprint_tests = {}
    for root, dirs, files in os.walk('tests/blueprints'):
        for file in files:
            if file.startswith('test_') and file.endswith('.py'):
                bp_name = file.replace('test_', '').replace('.py', '')
                # Handle variations
                for variant in ['_cli', '_spinner_and_box', '_unit', '_tools', '_testmode', '_agent_mcp_assignment', '_analysis', '_cost', '_progressive_tool']:
                    if bp_name.endswith(variant):
                        bp_name = bp_name.replace(variant, '')
                        break
                
                filepath = os.path.join(root, file)
                try:
                    with open(filepath, 'r') as f:
                        content = f.read()
                    test_count = len(re.findall(r'def test_[^(]*\(', content))
                    
                    if bp_name not in blueprint_tests:
                        blueprint_tests[bp_name] = 0
                    blueprint_tests[bp_name] += test_count
                except:
                    pass
    
    # Identify undertested blueprints (< 10 tests)
    for bp_name in blueprint_dirs:
        test_count = blueprint_tests.get(bp_name, 0)
        if test_count < 10:
            class_name, main_file = get_blueprint_info(bp_name)
            if class_name:  # Only include blueprints we can analyze
                undertested.append((bp_name, class_name, test_count))
    
    return undertested

def main():
    """Generate tests for undertested blueprints."""
    print("🧪 Automated Blueprint Test Generator")
    print("=" * 50)
    
    undertested = get_undertested_blueprints()
    
    print(f"Found {len(undertested)} undertested blueprints:")
    for bp_name, class_name, test_count in undertested:
        print(f"  {bp_name:20s} - {class_name:25s} ({test_count} tests)")
    
    print("\nGenerating comprehensive test suites...")
    
    generated_count = 0
    total_new_tests = 0
    
    for bp_name, class_name, current_test_count in undertested:
        test_filename = f"tests/blueprints/test_{bp_name}_comprehensive.py"
        
        # Skip if comprehensive test already exists
        if os.path.exists(test_filename):
            print(f"  ⏭️  Skipping {bp_name} - comprehensive test already exists")
            continue
        
        try:
            test_content = generate_blueprint_test(bp_name, class_name)
            
            # Write the test file
            os.makedirs(os.path.dirname(test_filename), exist_ok=True)
            with open(test_filename, 'w') as f:
                f.write(test_content)
            
            # Count tests in generated file
            new_test_count = len(re.findall(r'def test_[^(]*\(', test_content))
            total_new_tests += new_test_count
            generated_count += 1
            
            print(f"  ✅ Generated {test_filename} ({new_test_count} tests)")
            
        except Exception as e:
            print(f"  ❌ Failed to generate tests for {bp_name}: {e}")
    
    print(f"\n📊 Summary:")
    print(f"  Generated test files: {generated_count}")
    print(f"  New tests created: {total_new_tests}")
    print(f"  Progress toward 1337: +{total_new_tests}")
    
    if generated_count > 0:
        print(f"\n⚠️  Note: Generated tests are templates and may need customization")
        print(f"   Review and adjust based on each blueprint's specific functionality")

if __name__ == "__main__":
    main()