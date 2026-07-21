#!/bin/bash
set -euo pipefail
SCRATCH="${SCRATCH:?set SCRATCH}"
mkdir -p "$SCRATCH"

echo "=== CLI evidence captures (primary entry, ordered for lifecycle) ==="
# clean state for repeatable success
rm -rf /tmp/swarm-wiz-test /tmp/swarm-add-src

# 1. wizard non-int (guide args)
PYTHONPATH=src SWARM_TEST_MODE=1 python3 -m swarm.core.swarm_cli wizard --non-interactive -n "DemoTeam" -r "Lead:coordinator,Eng:engineer" --no-shortcut --output-dir /tmp/swarm-wiz-test 2>&1 | tee "$SCRATCH/wizard-capture.txt"

# 2. config list/add (for expanded)
PYTHONPATH=src SWARM_TEST_MODE=1 python3 -m swarm.core.swarm_cli config list --section llm 2>&1 | tee "$SCRATCH/config-list-after.txt"

# 3. add
mkdir -p /tmp/swarm-add-src
PYTHONPATH=src SWARM_TEST_MODE=1 python3 -m swarm.core.swarm_cli add /tmp/swarm-add-src --name demoadd 2>&1 | tee "$SCRATCH/add.txt"

# 4. delete
PYTHONPATH=src SWARM_TEST_MODE=1 python3 -m swarm.core.swarm_cli delete demoadd 2>&1 | tee "$SCRATCH/delete.txt"

# 5. install then uninstall (full lifecycle)
PYTHONPATH=src SWARM_TEST_MODE=1 python3 -m swarm.core.swarm_cli install-executable codey 2>&1 | tee "$SCRATCH/cli-install.txt"
PYTHONPATH=src SWARM_TEST_MODE=1 python3 -m swarm.core.swarm_cli uninstall codey 2>&1 | tee "$SCRATCH/uninstall.txt"

# 6. --help (for wizard --help cite + coverage)
PYTHONPATH=src SWARM_TEST_MODE=1 python3 -m swarm.core.swarm_cli --help 2>&1 | tee "$SCRATCH/cli-help-clean.txt"

# also useful list for journey refs
PYTHONPATH=src SWARM_TEST_MODE=1 python3 -m swarm.core.swarm_cli list --available 2>&1 | tee "$SCRATCH/cli-list.txt"

# launch for documented path
PYTHONPATH=src SWARM_TEST_MODE=1 python3 -m swarm.core.swarm_cli launch codey --message "final verif" 2>&1 | tee "$SCRATCH/cli-launch.txt"

echo "CLI evidence captured to $SCRATCH"
ls -l "$SCRATCH"/{wizard-capture.txt,add.txt,delete.txt,uninstall.txt,cli-help-clean.txt,cli-install.txt,cli-launch.txt,config-list-after.txt} | cat
exit 0
