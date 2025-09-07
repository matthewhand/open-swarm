import json
import multiprocessing
import os
import random
import subprocess
import sys
import time

NUM_PROCESSES = max(8, multiprocessing.cpu_count() * 2)
LOG_DIR = "swarm_nuclear_logs"
REPORT_FILE = "swarm_nuclear_final_report.json"

os.makedirs(LOG_DIR, exist_ok=True)

def run_test_instance(proc_id):
    """Run an isolated test_swarm_integration.py instance, capturing output, with staggered start."""
    # Staggered launch: random delay between 0.5 and 3 seconds
    delay = random.uniform(0.5, 3.0)
    time.sleep(delay)
    log_path = os.path.join(LOG_DIR, f"swarm_{proc_id}.log")
    try:
        result = subprocess.run(
            [sys.executable, "test_swarm_integration.py"],
            capture_output=True, text=True, timeout=600
        )
        with open(log_path, "w") as f:
            f.write(result.stdout)
            f.write("\n--- STDERR ---\n")
            f.write(result.stderr)
        return {"proc_id": proc_id, "exit_code": result.returncode, "log": log_path}
    except Exception as e:
        with open(log_path, "w") as f:
            f.write(f"Exception: {e}\n")
        return {"proc_id": proc_id, "exit_code": 99, "log": log_path}

def main():
    print(f"\n🚨 LAUNCHING STAGGERED NUCLEAR SWARM: Spawning {NUM_PROCESSES} test armies! 🚨\n")
    with multiprocessing.Pool(NUM_PROCESSES) as pool:
        results = pool.map(run_test_instance, range(NUM_PROCESSES))
    # Aggregate results
    all_logs = []
    all_green = True
    for res in results:
        with open(res["log"]) as f:
            log_content = f.read()
        all_logs.append({"proc_id": res["proc_id"], "exit_code": res["exit_code"], "log": log_content})
        if res["exit_code"] != 0:
            all_green = False
    with open(REPORT_FILE, "w") as f:
        json.dump(all_logs, f, indent=2)
    if all_green:
        print("\n✅ ALL TEST ARMIES PASSED! SWARM IS GREEN. PR CAN BE SUBMITTED.\n")
    else:
        print("\n❌ SOME TEST ARMIES FAILED! CHECK LOGS IN swarm_nuclear_logs/ AND REPORT FILE.\n")
    print(f"See {REPORT_FILE} for full nuclear swarm results.")

if __name__ == "__main__":
    main()
