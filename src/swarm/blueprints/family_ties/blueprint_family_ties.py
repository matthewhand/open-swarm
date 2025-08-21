#!/usr/bin/env python3
"""
Family Ties Blueprint Entry Point
This file serves as an entry point to the actual family_ties blueprint located in the stewie directory.
"""

import sys
import os
from pathlib import Path

# Add the stewie directory to the path so we can import the actual blueprint
stewie_dir = Path(__file__).parent.parent / "stewie"
sys.path.insert(0, str(stewie_dir))

# Import and run the actual blueprint
from blueprint_family_ties import StewieBlueprint

def main():
    """Main entry point for the family_ties blueprint."""
    import asyncio
    
    # Create and run the blueprint
    blueprint = StewieBlueprint("family_ties")
    
    # Get command line arguments (skip the script name)
    args = sys.argv[1:] if len(sys.argv) > 1 else []
    
    # Run the blueprint
    asyncio.run(blueprint.run(args))

if __name__ == "__main__":
    main()
