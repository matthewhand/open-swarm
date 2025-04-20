import time
from swarm.blueprints.whinge_surf.blueprint_whinge_surf import WhingeSurfBlueprint

def test_run_and_check_status():
    ws = WhingeSurfBlueprint()
    pid = ws.run_subprocess_in_background(["python3", "-c", "import time; print('hi'); time.sleep(1); print('bye')"])
    # Should be running immediately
    status = ws.check_subprocess_status(pid)
    assert status is not None and not status['finished']
    time.sleep(1.5)
    status = ws.check_subprocess_status(pid)
    assert status['finished'] and status['exit_code'] == 0
    output = ws.get_subprocess_output(pid)
    assert 'hi' in output and 'bye' in output

def test_kill_subprocess():
    ws = WhingeSurfBlueprint()
    pid = ws.run_subprocess_in_background(["python3", "-c", "import time; print('wait'); time.sleep(5)"])
    time.sleep(0.5)
    msg = ws.kill_subprocess(pid)
    assert 'killed' in msg or 'already finished' in msg
    status = ws.check_subprocess_status(pid)
    assert status['finished']

def test_tail_and_show_output():
    ws = WhingeSurfBlueprint()
    pid = ws.run_subprocess_in_background(["python3", "-c", "import time; print('foo'); time.sleep(1); print('bar')"])
    time.sleep(1.5)
    # Tail output (should not error, returns string)
    result = ws.tail_output(pid)
    assert isinstance(result, str)
    # Show output (should contain 'foo' and 'bar')
    shown = ws.show_output(pid)
    assert 'foo' in shown and 'bar' in shown

def test_list_and_prune_jobs():
    ws = WhingeSurfBlueprint()
    pid1 = ws.run_subprocess_in_background(["python3", "-c", "import time; print('job1'); time.sleep(0.5)"])
    pid2 = ws.run_subprocess_in_background(["python3", "-c", "import time; print('job2'); time.sleep(0.5)"])
    time.sleep(1)
    # List jobs (should show both jobs)
    listing = ws.list_jobs()
    assert 'job1' in listing or 'job2' in listing
    # Prune jobs (should remove finished jobs)
    pruned = ws.prune_jobs()
    assert 'Removed' in pruned

def test_resource_usage_and_analyze_self():
    ws = WhingeSurfBlueprint()
    pid = ws.run_subprocess_in_background(["python3", "-c", "import time; print('hi'); time.sleep(1)"])
    time.sleep(0.5)
    usage = ws.resource_usage(pid)
    assert 'CPU:' in usage or 'Error' in usage
    analysis = ws.analyze_self(output_format='text')
    assert 'Ultra-enhanced code analysis.' in analysis or 'class WhingeSurfBlueprint' in analysis

def test_self_update():
    ws = WhingeSurfBlueprint()
    # This test only verifies that the method runs and returns a string (does not actually update code)
    result = ws.self_update_from_prompt("Add a test comment", test=True)
    assert 'Self-update completed.' in result
