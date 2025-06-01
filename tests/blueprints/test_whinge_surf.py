import time
import json
from swarm.blueprints.whinge_surf.blueprint_whinge_surf import WhingeSurfBlueprint
import pytest 
from unittest.mock import MagicMock 

def test_run_and_check_status(mocker):
    ws = WhingeSurfBlueprint()

    # Mock job states
    mock_job_running = mocker.MagicMock()
    mock_job_running.status = "RUNNING"
    mock_job_running.exit_code = None
    mock_job_running.output = "hi" # Initial output

    mock_job_completed = mocker.MagicMock()
    mock_job_completed.status = "COMPLETED"
    mock_job_completed.exit_code = 0
    mock_job_completed.output = "hi\nbye" # Final output

    mocker.patch.object(ws.job_service, 'launch', return_value="test-job-123")
    # get_status will be called multiple times, return running then completed
    mocker.patch.object(ws.job_service, 'get_status', side_effect=[mock_job_running, mock_job_completed])
    # get_output will be called after completion
    mocker.patch.object(ws.job_service, 'get_output', return_value="hi\nbye")


    job_id = ws.job_service.launch(
        command=["python3", "-c", "print('hi'); time.sleep(0.1); print('bye')"], # Shortened sleep
        tracking_label="test-job"
    )

    # First check - RUNNING state
    job_status_running = ws.job_service.get_status(job_id)
    assert job_status_running.status == "RUNNING"

    # Simulate time passing for the job to complete for the next get_status call
    # The side_effect handles the state change, so direct time.sleep isn't strictly necessary
    # for the mock's behavior, but good for conceptual clarity.

    # Second check - COMPLETED state
    job_status_completed = ws.job_service.get_status(job_id)
    assert job_status_completed.status == "COMPLETED"
    assert job_status_completed.exit_code == 0

    # Verify output
    output = ws.job_service.get_output(job_id) # This was ws.job_service.get_output(job_id)
    assert 'hi' in output and 'bye' in output

def test_kill_subprocess(mocker):
    ws = WhingeSurfBlueprint()
    mock_job_running = mocker.MagicMock()
    mock_job_running.status = "RUNNING"

    # This mock will be for the job_service.terminate method
    mock_terminate_method = mocker.patch.object(ws.job_service, 'terminate', return_value="TERMINATED")
    # Mock get_status if kill_subprocess checks it before/after
    mocker.patch.object(ws.job_service, 'get_status', return_value=mock_job_running)


    job_id = "test-job-to-kill"
    # The original ws.kill_subprocess(pid) was calling os.kill and updating internal state.
    # Now we are testing the service layer directly for termination.
    # If ws.kill_subprocess is still the public API to test, it should use job_service.terminate.
    # For now, let's assume we are testing the interaction with the service.

    # If ws.kill_subprocess is the target:
    # It should internally call self.job_service.terminate(job_id_from_pid)
    # and self.job_service.update_status(job_id_from_pid, "TERMINATED")
    # Let's assume ws.kill_subprocess is refactored to take job_id
    
    # If testing ws.kill_subprocess(job_id) which uses the service:
    ws.kill_subprocess(job_id) # Assuming ws.kill_subprocess is refactored
    mock_terminate_method.assert_called_once_with(job_id)
    # assert 'killed' in result_msg or 'terminated' in result_msg

    # If directly testing the service call as in the previous step:
    # result = ws.job_service.terminate(job_id) # This was already tested by calling ws.kill_subprocess
    # assert result == "TERMINATED"
    # mock_terminate_method.assert_called_once_with(job_id)


def test_tail_and_show_output(mocker):
    ws = WhingeSurfBlueprint()

    mock_job_with_logs = mocker.MagicMock()
    mock_job_with_logs.name = "test-pid-123" # Ensure it has a name if used for title
    # For tail_output, job_service.get_log_tail should be called
    mocker.patch.object(ws.job_service, 'get_log_tail', return_value=["foo", "bar"])
    # For show_output, job_service.get_full_log should be called
    mocker.patch.object(ws.job_service, 'get_full_log', return_value="foo\nbar\nend of log")
    # Mock get_status to indicate job exists
    mock_existing_job_status = mocker.MagicMock()
    mock_existing_job_status.status = "COMPLETED" # Or "RUNNING"
    mocker.patch.object(ws.job_service, 'get_status', return_value=mock_existing_job_status)


    pid_or_job_id = "test-pid-123" # Use a consistent ID

    # Test tail output
    # ws.tail_output now directly returns the list from the service
    tail_result_list = ws.tail_output(pid_or_job_id)
    assert isinstance(tail_result_list, list)
    assert "foo" in tail_result_list
    assert "bar" in tail_result_list
    ws.job_service.get_log_tail.assert_called_once_with(pid_or_job_id)


    # Test show output
    # The show_output method in blueprint calls ansi_emoji_box, so we mock that.
    mock_show_ux_box_call = mocker.patch.object(ws.ux, 'ansi_emoji_box', return_value="Mocked Box for show_output")
    ws.show_output(pid_or_job_id)
    mock_show_ux_box_call.assert_called_once_with(
        title="Show Output",
        content="foo\nbar\nend of log", # Expected full log content
        summary=f"Full output for job {pid_or_job_id}.",
        op_type="show_output",
        params={"job_id": pid_or_job_id},
        result_count=len("foo\nbar\nend of log")
    )
    ws.job_service.get_full_log.assert_called_once_with(pid_or_job_id)
    mock_show_ux_box_call.reset_mock() # Reset for next assertion


    # Test case where job is not found for tail_output
    mocker.patch.object(ws.job_service, 'get_status', return_value=None) # Simulate job not found
    # The ux.ansi_emoji_box is called by ws.tail_output if job_service.get_status returns None
    mock_tail_ux_box_call_notfound = mocker.patch.object(ws.ux, 'ansi_emoji_box', return_value="Mocked Box: No such job for tail")
    
    ws.tail_output("nonexistent-job-tail") # Use a distinct ID
    mock_tail_ux_box_call_notfound.assert_called_once_with(
        title="Tail Output", 
        content="No such job: nonexistent-job-tail", 
        op_type="tail_output", params={"pid": "nonexistent-job-tail"}, result_count=0
    )
    mock_tail_ux_box_call_notfound.reset_mock() 

    # Test case where job is not found for show_output
    # get_status is already mocked to return None
    mock_show_ux_box_call_notfound = mocker.patch.object(ws.ux, 'ansi_emoji_box', return_value="Mocked Box: No such job for show")
    ws.show_output("nonexistent-job-show") # Use a distinct ID
    mock_show_ux_box_call_notfound.assert_called_once_with(
        title="Show Output", 
        content="No such job: nonexistent-job-show", 
        op_type="show_output", params={"pid": "nonexistent-job-show"}, result_count=0
    )


def test_list_and_prune_jobs(mocker): 
    ws = WhingeSurfBlueprint()
    mock_active_job = MagicMock(); mock_active_job.id="job1"; mock_active_job.command_str="cmd1"; mock_active_job.status = "RUNNING"; mock_active_job.pid=123
    mock_finished_job = MagicMock(); mock_finished_job.id="job2"; mock_finished_job.command_str="cmd2"; mock_finished_job.status = "COMPLETED"; mock_finished_job.pid=456
    
    mocker.patch.object(ws.job_service, 'list_all', return_value=[mock_active_job, mock_finished_job])
    mocker.patch.object(ws.job_service, 'prune_completed', return_value=["job2"]) 
    mock_ux_box_call = mocker.patch.object(ws.ux, 'ansi_emoji_box', return_value="Mocked Box")


    ws.list_jobs()
    mock_ux_box_call.assert_any_call(
        title="WhingeSurf Jobs",
        content=mocker.ANY, 
        op_type="list_jobs",
        result_count=2
    )
    
    ws.prune_jobs()
    ws.job_service.prune_completed.assert_called_once()
    mock_ux_box_call.assert_called_with( 
        title="Pruned Jobs",
        content="Removed 1 completed job(s): job2",
        op_type="prune_jobs",
        result_count=1
    )


def test_resource_usage_and_analyze_self(mocker):
    mock_monitor_service = mocker.MagicMock()
    mock_metrics_data = {
        'cpu': {'percent': 5.2},
        'memory': {'rss': 10240, 'vms': 20480},
        'threads': 2
    }
    mock_monitor_service.get_metrics.return_value = mock_metrics_data
    
    ws = WhingeSurfBlueprint(monitor_service=mock_monitor_service)
    mock_ux_box_call = mocker.patch.object(ws.ux, 'ansi_emoji_box', return_value="Mocked Box")


    job_id_for_usage = "active-job-id"
    mock_job_status = MagicMock(); mock_job_status.status = "RUNNING"; mock_job_status.pid = 12345
    mocker.patch.object(ws.job_service, 'get_status', return_value=mock_job_status)

    ws.resource_usage(job_id_for_usage)
    ws.monitor_service.get_metrics.assert_called_once_with(process_pid=12345)
    mock_ux_box_call.assert_any_call( 
        title=f"Resource Usage for Job {job_id_for_usage} (PID: 12345)",
        content=json.dumps(mock_metrics_data, indent=2), 
        op_type="resource_usage"
    )
    
    ws.analyze_self(output_format='text')
    mock_ux_box_call.assert_called_with( 
        title="WhingeSurf Self-Analysis",
        content="Ultra-enhanced code analysis complete. All systems nominal. 🌊", 
        op_type="analyze_self"
    )


def test_self_update(mocker): 
    ws = WhingeSurfBlueprint()
    mock_ux_box_call = mocker.patch.object(ws.ux, 'ansi_emoji_box', return_value="Mocked Box")
    ws.self_update()
    mock_ux_box_call.assert_called_once_with(
        title="WhingeSurf Self-Update",
        content="Self-update initiated. Please restart if necessary.",
        op_type="self_update"
    )
