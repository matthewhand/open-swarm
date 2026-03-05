"""
Unit tests for src/swarm/services/job.py
=======================================

Tests job serialization/deserialization, launch, status transitions, log retrieval,
termination, and pruning behaviors using mocks only.
"""

import json
from pathlib import Path
from unittest.mock import patch, MagicMock, mock_open
import pytest
import time

# Import the module under test
from swarm.services.job import Job, DefaultJobService


# =============================================================================
# Fixtures
# =============================================================================

@pytest.fixture
def mock_job_data_dir(tmp_path):
    """Mock the job data directory to a temporary path and ensure directories exist."""
    outputs_dir = tmp_path / "outputs"
    outputs_dir.mkdir(exist_ok=True)
    
    with patch('swarm.services.job.SWARM_JOB_DATA_DIR', tmp_path):
        with patch('swarm.services.job.JOBS_METADATA_FILE', tmp_path / "jobs_metadata.json"):
            with patch('swarm.services.job.JOB_OUTPUTS_DIR', outputs_dir):
                yield tmp_path


@pytest.fixture
def job_service(mock_job_data_dir):
    """Create a fresh job service instance with mock data directory."""
    return DefaultJobService()


@pytest.fixture
def sample_job_dict():
    """Return a sample job dictionary for serialization tests."""
    return {
        "id": "test_job_1234567890123",
        "command_list": ["echo", "hello", "world"],
        "command_str": "echo hello world",
        "status": "RUNNING",
        "pid": 12345,
        "exit_code": None,
        "output_file_path": "/tmp/test_job.log",
        "tracking_label": "test_job",
        "created_at": 1234567890.123,
        "updated_at": 1234567890.123,
    }


# =============================================================================
# Tests for Job class
# =============================================================================

class TestJob:
    """Test Job dataclass functionality."""

    def test_job_creation_with_minimal_parameters(self):
        """Test creating a job with minimal parameters."""
        job = Job(id="test_job", command_list=["echo", "hello"])
        assert job.id == "test_job"
        assert job.command_list == ["echo", "hello"]
        assert job.command_str == "echo hello"
        assert job.status == "PENDING"
        assert job.pid is None
        assert job.exit_code is None
        assert job.output_file_path is not None
        assert job.tracking_label is None
        assert isinstance(job.created_at, float)
        assert isinstance(job.updated_at, float)

    def test_job_creation_with_all_parameters(self):
        """Test creating a job with all parameters."""
        created_at = time.time() - 3600
        updated_at = time.time() - 1800
        output_path = Path("/tmp/test_output.log")

        job = Job(
            id="test_job",
            command_list=["echo", "hello"],
            command_str="echo hello world",
            status="RUNNING",
            pid=12345,
            exit_code=None,
            output_file_path=output_path,
            tracking_label="test_label",
            created_at=created_at,
            updated_at=updated_at,
        )

        assert job.id == "test_job"
        assert job.command_list == ["echo", "hello"]
        assert job.command_str == "echo hello world"
        assert job.status == "RUNNING"
        assert job.pid == 12345
        assert job.exit_code is None
        assert job.output_file_path == output_path
        assert job.tracking_label == "test_label"
        assert job.created_at == created_at
        assert job.updated_at == updated_at

    def test_job_to_dict(self, sample_job_dict):
        """Test job serialization to dictionary."""
        job = Job.from_dict(sample_job_dict)
        job_dict = job.to_dict()

        assert job_dict == sample_job_dict

    def test_job_from_dict(self, sample_job_dict):
        """Test job deserialization from dictionary."""
        job = Job.from_dict(sample_job_dict)

        assert job.id == sample_job_dict["id"]
        assert job.command_list == sample_job_dict["command_list"]
        assert job.command_str == sample_job_dict["command_str"]
        assert job.status == sample_job_dict["status"]
        assert job.pid == sample_job_dict["pid"]
        assert job.exit_code == sample_job_dict["exit_code"]
        assert str(job.output_file_path) == sample_job_dict["output_file_path"]
        assert job.tracking_label == sample_job_dict["tracking_label"]
        assert job.created_at == sample_job_dict["created_at"]
        assert job.updated_at == sample_job_dict["updated_at"]

    def test_job_from_dict_with_missing_fields(self):
        """Test job deserialization with missing optional fields."""
        minimal_data = {
            "id": "test_job",
            "command_list": ["echo", "hello"],
        }
        job = Job.from_dict(minimal_data)

        assert job.id == minimal_data["id"]
        assert job.command_list == minimal_data["command_list"]
        assert job.command_str == "echo hello"  # Should be auto-generated from command_list
        assert job.status == "UNKNOWN"
        assert job.pid is None
        assert job.exit_code is None
        assert job.output_file_path is not None
        assert job.tracking_label is None
        assert isinstance(job.created_at, float)
        assert isinstance(job.updated_at, float)

    def test_job_post_init(self):
        """Test __post_init__ method behavior."""
        # Test command_str generation
        job1 = Job(id="test_job", command_list=["python", "-m", "http.server"])
        assert job1.command_str == "python -m http.server"

        # Test output_file_path generation
        job2 = Job(id="test_job_123", command_list=["echo", "test"])
        assert "test_job_123" in str(job2.output_file_path)


# =============================================================================
# Tests for DefaultJobService
# =============================================================================

class TestDefaultJobService:
    """Test DefaultJobService functionality."""

    def test_service_initialization(self, job_service):
        """Test service initialization."""
        assert isinstance(job_service, DefaultJobService)

    @patch('swarm.services.job.subprocess.Popen')
    @patch('swarm.services.job.threading.Thread')
    def test_launch_valid_command(self, mock_thread, mock_popen, job_service):
        """Test launching a valid command."""
        # Setup mock process
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.stdout = MagicMock()
        mock_process.stdout.readline = MagicMock(return_value='')
        mock_process.wait = MagicMock()
        mock_popen.return_value = mock_process

        # Setup mock thread
        mock_thread_instance = MagicMock()
        mock_thread.return_value = mock_thread_instance

        # Launch job
        job_id = job_service.launch(["echo", "hello"])

        # Verify job is created and running
        assert isinstance(job_id, str)
        assert len(job_id) > 0

        job = job_service.get_status(job_id)
        assert job is not None
        assert job.id == job_id
        assert job.command_list == ["echo", "hello"]
        assert job.status == "RUNNING"
        assert job.pid == 12345

        mock_popen.assert_called_once()

    def test_launch_empty_command(self, job_service):
        """Test launching an empty command list."""
        with pytest.raises(ValueError):
            job_service.launch([])

    @patch('swarm.services.job.subprocess.Popen')
    def test_launch_command_not_found(self, mock_popen, job_service):
        """Test launching a command that is not found."""
        mock_popen.side_effect = FileNotFoundError("Command not found")

        with pytest.raises(FileNotFoundError):
            job_service.launch(["nonexistent_command"])

    @patch('swarm.services.job.subprocess.Popen')
    def test_launch_generic_error(self, mock_popen, job_service):
        """Test launching a command that raises a generic error."""
        mock_popen.side_effect = Exception("Generic error")

        with pytest.raises(Exception):
            job_service.launch(["invalid_command"])

    def test_get_status_nonexistent_job(self, job_service):
        """Test getting status of a nonexistent job."""
        assert job_service.get_status("nonexistent_job") is None

    @patch('swarm.services.job.subprocess.Popen')
    def test_get_full_log_nonexistent_job(self, mock_popen, job_service):
        """Test getting log of a nonexistent job."""
        assert job_service.get_full_log("nonexistent_job") == "[Job not found]"

    @patch('swarm.services.job.subprocess.Popen')
    def test_get_log_tail_nonexistent_job(self, mock_popen, job_service):
        """Test getting log tail of a nonexistent job."""
        assert job_service.get_log_tail("nonexistent_job") == ["[Job not found]"]

    def test_get_full_log_no_output_file(self, job_service):
        """Test getting log when output file is missing."""
        # Create a job directly without launching (to avoid subprocess issues)
        job = Job(id="test_job_no_output", command_list=["echo", "hello"])
        job.output_file_path = None
        
        with patch.object(job_service, 'get_status', return_value=job):
            log = job_service.get_full_log("test_job_no_output")
            assert "[No output file found" in log

    def test_get_full_log_with_content(self, job_service):
        """Test getting log with content."""
        # Create a job directly with a known output file path
        job = Job(id="test_job_with_log", command_list=["echo", "hello"])
        
        with patch.object(job_service, 'get_status', return_value=job), \
             patch('pathlib.Path.open', new_callable=mock_open, read_data="Line 1\nLine 2\nLine 3"), \
             patch('pathlib.Path.exists', return_value=True):
            log = job_service.get_full_log("test_job_with_log")
            assert log == "Line 1\nLine 2\nLine 3"

    def test_get_full_log_with_max_chars(self, job_service):
        """Test getting log with max chars limit."""
        job = Job(id="test_job_with_max_chars", command_list=["echo", "hello"])
        
        # Mock the get_status method to return our test job
        with patch.object(job_service, 'get_status', return_value=job):
            # Patch Path.exists at the module level
            with patch('swarm.services.job.Path.exists', return_value=True):
                with patch('swarm.services.job.Path.open', new_callable=mock_open, read_data="Line 1\nLine 2\nLine 3"):
                    log = job_service.get_full_log("test_job_with_max_chars", max_chars=6)
                    assert log == "Line 3"

    def test_get_log_tail_default_lines(self, job_service):
        """Test getting log tail with default lines."""
        job = Job(id="test_job_tail_default", command_list=["echo", "hello"])
        
        with patch.object(job_service, 'get_status', return_value=job), \
             patch('pathlib.Path.open', new_callable=mock_open, read_data="Line 1\nLine 2\nLine 3"), \
             patch('pathlib.Path.exists', return_value=True):
            tail = job_service.get_log_tail("test_job_tail_default")
            assert tail == ["Line 1", "Line 2", "Line 3"]

    def test_get_log_tail_specific_lines(self, job_service):
        """Test getting log tail with specific number of lines."""
        job = Job(id="test_job_tail_specific", command_list=["echo", "hello"])
        
        with patch.object(job_service, 'get_status', return_value=job), \
             patch('pathlib.Path.open', new_callable=mock_open, read_data="Line 1\nLine 2\nLine 3"), \
             patch('pathlib.Path.exists', return_value=True):
            tail = job_service.get_log_tail("test_job_tail_specific", n_lines=2)
            assert tail == ["Line 2", "Line 3"]

    def test_list_all_empty(self, job_service):
        """Test listing all jobs when none exist."""
        assert job_service.list_all() == []

    @patch('swarm.services.job.subprocess.Popen')
    def test_list_all_with_jobs(self, mock_popen, job_service):
        """Test listing all jobs when there are jobs."""
        job_id1 = job_service.launch(["echo", "hello"])
        job_id2 = job_service.launch(["python", "-m", "http.server"])

        jobs = job_service.list_all()
        assert len(jobs) == 2
        assert any(job.id == job_id1 for job in jobs)
        assert any(job.id == job_id2 for job in jobs)

    def test_terminate_nonexistent_job(self, job_service):
        """Test terminating a nonexistent job."""
        assert job_service.terminate("nonexistent_job") == "NOT_FOUND"

    @patch('swarm.services.job.subprocess.Popen')
    def test_terminate_completed_job(self, mock_popen, job_service):
        """Test terminating a completed job."""
        job_id = job_service.launch(["echo", "hello"])
        job = job_service.get_status(job_id)
        job.status = "COMPLETED"
        job.exit_code = 0

        assert job_service.terminate(job_id) == "ALREADY_STOPPED"

    def test_terminate_running_job(self, job_service):
        """Test terminating a running job."""
        # Create a job directly with a running process handle
        job = Job(id="test_job_running", command_list=["echo", "hello"])
        job.status = "RUNNING"
        
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()
        mock_process.wait = MagicMock()
        mock_process.returncode = -15
        job._process_handle = mock_process
        
        with patch.object(job_service, 'get_status', return_value=job):
            result = job_service.terminate("test_job_running")
            assert result == "TERMINATED"
            assert job.status == "TERMINATED"

    def test_terminate_running_job_timeout(self, job_service):
        """Test terminating a running job that times out and requires force kill."""
        from subprocess import TimeoutExpired
        
        job = Job(id="test_job_timeout", command_list=["echo", "hello"])
        job.status = "RUNNING"
        job.pid = 12345
        
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.terminate = MagicMock()
        mock_process.kill = MagicMock()
        # First wait raises TimeoutExpired, second succeeds
        mock_process.wait.side_effect = [TimeoutExpired(cmd="test", timeout=2), None]
        mock_process.returncode = -9
        job._process_handle = mock_process
        
        # Add job to service's internal dict
        job_service._jobs["test_job_timeout"] = job
        
        result = job_service.terminate("test_job_timeout")

        assert result == "TERMINATED"
        mock_process.kill.assert_called_once()

    def test_terminate_running_job_error(self, job_service):
        """Test terminating a running job that raises an error."""
        job = Job(id="test_job_error", command_list=["echo", "hello"])
        job.status = "RUNNING"
        job.pid = 12345
        
        mock_process = MagicMock()
        mock_process.pid = 12345
        mock_process.terminate.side_effect = Exception("Termination error")
        job._process_handle = mock_process
        
        # Add job to service's internal dict
        job_service._jobs["test_job_error"] = job
        
        result = job_service.terminate("test_job_error")
        assert result == "ERROR"

    @patch('swarm.services.job.subprocess.Popen')
    def test_prune_no_jobs(self, mock_popen, job_service):
        """Test pruning completed jobs when no jobs exist."""
        pruned_ids = job_service.prune_completed()
        assert pruned_ids == []

    @patch('swarm.services.job.subprocess.Popen')
    def test_prune_completed_jobs(self, mock_popen, job_service):
        """Test pruning completed jobs."""
        job_id1 = job_service.launch(["echo", "hello"])
        job_id2 = job_service.launch(["python", "-m", "http.server"])

        job1 = job_service.get_status(job_id1)
        job1.status = "COMPLETED"
        job1.exit_code = 0

        job2 = job_service.get_status(job_id2)
        job2.status = "FAILED"
        job2.exit_code = 1

        pruned_ids = job_service.prune_completed()
        assert len(pruned_ids) == 2
        assert job_id1 in pruned_ids
        assert job_id2 in pruned_ids

        # Verify jobs are removed
        assert job_service.get_status(job_id1) is None
        assert job_service.get_status(job_id2) is None

    def test_prune_running_jobs(self, job_service):
        """Test that running jobs are not pruned."""
        # Create a running job directly
        job = Job(id="test_job_running_prune", command_list=["echo", "hello"])
        job.status = "RUNNING"
        
        with patch.object(job_service, 'get_status', return_value=job):
            pruned_ids = job_service.prune_completed()
            assert len(pruned_ids) == 0

    @patch('swarm.services.job.subprocess.Popen')
    def test_get_output_alias(self, mock_popen, job_service):
        """Test get_output method (alias for get_full_log)."""
        with patch.object(job_service, 'get_full_log', return_value="test log content"):
            job_id = job_service.launch(["echo", "hello"])
            assert job_service.get_output(job_id) == "test log content"

    @patch('swarm.services.job.subprocess.Popen')
    @patch('pathlib.Path.unlink')
    def test_prune_with_log_file_deletion(self, mock_unlink, mock_popen, job_service):
        """Test that log files are deleted when pruning jobs."""
        job_id = job_service.launch(["echo", "hello"])
        job = job_service.get_status(job_id)
        job.status = "COMPLETED"
        job.exit_code = 0

        job_service.prune_completed()
        mock_unlink.assert_called_once()

    @patch('swarm.services.job.subprocess.Popen')
    @patch('pathlib.Path.unlink')
    def test_prune_with_log_file_error(self, mock_unlink, mock_popen, job_service):
        """Test pruning jobs when log file deletion fails."""
        mock_unlink.side_effect = OSError("Cannot delete file")

        job_id = job_service.launch(["echo", "hello"])
        job = job_service.get_status(job_id)
        job.status = "COMPLETED"
        job.exit_code = 0

        pruned_ids = job_service.prune_completed()
        assert len(pruned_ids) == 1
        assert job_id in pruned_ids


# =============================================================================
# Tests with disk persistence
# =============================================================================

class TestJobServicePersistence:
    """Test job service disk persistence."""

    def test_save_and_load_jobs(self, job_service, mock_job_data_dir):
        """Test saving and loading jobs from disk."""
        # Create a job directly and save it
        job = Job(id="test_job_persist", command_list=["echo", "hello"])
        job.status = "COMPLETED"
        job.exit_code = 0
        
        job_service._jobs["test_job_persist"] = job
        job_service._save_jobs_to_disk()

        # Create a new instance to simulate restart
        new_service = DefaultJobService()
        assert len(new_service.list_all()) == 1

        loaded_job = new_service.get_status("test_job_persist")
        assert loaded_job is not None
        assert loaded_job.id == "test_job_persist"
        assert loaded_job.command_list == ["echo", "hello"]

    def test_load_running_job_from_disk(self, job_service, mock_job_data_dir):
        """Test that running jobs from disk are marked as stale."""
        # Create a job and save it with RUNNING status
        job = Job(id="test_job_stale", command_list=["echo", "hello"])
        job.status = "RUNNING"
        job.pid = 12345
        
        # Manually save the job to disk
        job_service._jobs["test_job_stale"] = job
        job_service._save_jobs_to_disk()
        
        # Create a new instance to load the jobs
        new_service = DefaultJobService()
        loaded_job = new_service.get_status("test_job_stale")

        assert loaded_job is not None
        assert loaded_job.status == "UNKNOWN_STALE"

    def test_load_corrupted_jobs_file(self, job_service, mock_job_data_dir):
        """Test loading corrupted jobs metadata file."""
        # Create corrupt JSON file
        with (mock_job_data_dir / "jobs_metadata.json").open("w") as f:
            f.write("this is not valid JSON")

        # Should handle the error gracefully
        with patch('swarm.services.job.logger') as mock_logger:
            service = DefaultJobService()
            assert len(service.list_all()) == 0
            mock_logger.error.assert_called_once()

    def test_save_jobs_with_error(self, job_service, mock_job_data_dir):
        """Test handling errors when saving jobs to disk."""
        # Create a job directly
        job = Job(id="test_job_save_error", command_list=["echo", "hello"])
        job.status = "COMPLETED"
        job.exit_code = 0
        
        job_service._jobs["test_job_save_error"] = job
        
        # Make save operation fail
        with patch.object(job_service, '_save_jobs_to_disk', side_effect=Exception("Save error")):
            # Should raise exception (not caught in prune_completed)
            with pytest.raises(Exception, match="Save error"):
                job_service.prune_completed()


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
