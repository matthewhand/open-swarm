import tempfile
from pathlib import Path
import sys
sys.path.insert(0, 'src')
from swarm.core.swarm_cli import find_entry_point

def test_find_entry_point_prefers_cli():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "codey"
        d.mkdir()
        (d / "codey_cli.py").touch()
        (d / "blueprint_codey.py").touch()
        (d / "codey.py").touch()
        assert find_entry_point(d) == "codey_cli.py"

def test_find_entry_point_falls_back():
    with tempfile.TemporaryDirectory() as tmp:
        d = Path(tmp) / "foo"
        d.mkdir()
        (d / "blueprint_foo.py").touch()
        assert find_entry_point(d) == "blueprint_foo.py"

if __name__ == "__main__":
    test_find_entry_point_prefers_cli()
    test_find_entry_point_falls_back()
    print("tests passed")
