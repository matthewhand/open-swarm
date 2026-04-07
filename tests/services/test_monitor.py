import pytest
from swarm.services.monitor import DefaultMonitorService

def test_get_metrics_returns_dict():
    """Test that get_metrics returns a dictionary."""
    service = DefaultMonitorService()
    metrics = service.get_metrics("test_job")
    assert isinstance(metrics, dict)

def test_get_metrics_content():
    """Test that get_metrics returns the expected hardcoded values."""
    service = DefaultMonitorService()
    metrics = service.get_metrics("test_job")
    assert "cpu" in metrics
    assert "memory" in metrics
    assert metrics["cpu"] == 25.0
    assert metrics["memory"] == 1024

def test_get_metrics_with_different_job_ids():
    """Test that get_metrics accepts different job IDs."""
    service = DefaultMonitorService()
    metrics1 = service.get_metrics("job1")
    metrics2 = service.get_metrics("job2")
    assert metrics1 == metrics2
