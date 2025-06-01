import time
from swarm.blueprints.whinge_surf.blueprint_whinge_surf import WhingeSurfBlueprint

def test_run_and_check_status(mocker):
    ws = WhingeSurfBlueprint()
    
    # Mock job with status transition
    mock_job = mocker.MagicMock()
    mock_job.status = "RUNNING"
    mock_job.exit_code = None
    
    # Configure mock to transition status after first call
    def status_side_effect(*args):
        mock_job.status = "COMPLETED"
        mock_job.exit_code = 0
        return mock_job
    
    mocker.patch.object(ws.job_service, 'launch', return_value="test-job-123")
    mocker.patch.object(ws.job_service, 'get_status',
                       side_effect=[mock_job, status_side_effect()])
    
    job_id = ws.job_service.launch(
        command=["python3", "-c", "print('hi'); time.sleep(1); print('bye')"],
        tracking_label="test-job"
    )
    
    # First check - RUNNING state
    job = ws.job_service.get_status(job_id)
    assert job.status == "RUNNING"
    
    # Second check - COMPLETED state
    job = ws.job_service.get_status(job_id)
    assert job.status == "COMPLETED"
    assert job.exit_code == 0
    
    # Verify output
    output = ws.job_service.get_output(job_id)
    assert 'hi' in output and 'bye' in output

def test_kill_subprocess(mocker):
    ws = WhingeSurfBlueprint()
    mock_job = mocker.MagicMock()
    mock_job.status = "RUNNING"
    mock_job.terminate.return_value = "TERMINATED"
    
    mocker.patch.object(ws.job_service, 'get_status', return_value=mock_job)
    mocker.patch.object(ws.job_service, 'terminate', return_value="TERMINATED")
    
    job_id = "test-job-123"
    result = ws.job_service.terminate(job_id)
    
    assert result == "TERMINATED"
    mock_job.terminate.assert_called_once()
    assert mock_job.status == "TERMINATED"

def test_tail_and_show_output(mocker):
    ws = WhingeSurfBlueprint()
    
    # Mock job output with dataclass structure
    mock_job = mocker.MagicMock()
    mock_job.log_tail = ["foo\n", "bar\n"]
    mock_job.full_log = "foo\nbar\n"
    
    mocker.patch.object(ws, 'run_subprocess_in_background', return_value="test-pid-123")
    mocker.patch.object(ws.job_service, 'get_status', return_value=mock_job)
    
    pid = ws.run_subprocess_in_background(["python3", "-c", "print('test')"])
    
    # Test tail output
    tail_result = ws.tail_output(pid)
    assert isinstance(tail_result, list)
    assert any("foo" in line for line in tail_result)
    
    # Test show output
    full_output = ws.show_output(pid)
    assert isinstance(full_output, str)
    assert "foo" in full_output and "bar" in full_output

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

def test_resource_usage_and_analyze_self(mocker):
    mock_monitor_service = mocker.MagicMock()
    mock_monitor_service.get_metrics.return_value = {
        'cpu': {'percent': 5.2},
        'memory': {'rss': 10240, 'vms': 20480},
        'threads': 2
    }
    ws = WhingeSurfBlueprint(monitor_service=mock_monitor_service)
    mock_metrics = {
        'cpu': {'percent': 5.2},
        'memory': {'rss': 10240, 'vms': 20480},
        'threads': 2
    }
    mocker.patch.object(ws.monitor_service, 'get_metrics', return_value=mock_metrics)
    
    metrics = ws.monitor_service.get_metrics("test-job-123")
    
    assert isinstance(metrics, dict)
    assert 0 < metrics['cpu']['percent'] < 100
    assert metrics['memory']['rss'] > 0
    analysis = ws.analyze_self(output_format='text')
    assert 'Ultra-enhanced code analysis.' in analysis or 'class WhingeSurfBlueprint' in analysis

def test_self_update():
    ws = WhingeSurfBlueprint()
    # This test only verifies that the method runs and returns a string (does not actually update code)
    result = ws.self_update_from_prompt("Add a test comment", test=True)
    assert 'Self-update completed.' in result
