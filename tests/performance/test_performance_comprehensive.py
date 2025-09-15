"""
Comprehensive performance testing for Swarm system.
Tests response times, memory usage, and scalability.
"""

import threading
import time

import psutil
from swarm.blueprints.geese.blueprint_geese import GeeseBlueprint


class TestPerformanceComprehensive:
    """Comprehensive performance testing suite."""

    def test_blueprint_creation_performance(self):
        """Test performance of blueprint creation with comprehensive metrics."""
        import statistics

        start_time = time.time()
        creation_times = []

        # Create 100 blueprints and measure individual creation times
        blueprints = []
        for i in range(100):
            bp_start = time.perf_counter()
            bp = GeeseBlueprint(blueprint_id=f"perf_{i}")
            bp_end = time.perf_counter()

            blueprints.append(bp)
            creation_times.append(bp_end - bp_start)

        end_time = time.time()
        total_duration = end_time - start_time

        # Performance assertions
        assert total_duration < 2.0, f"Total creation time {total_duration:.2f}s exceeded 2.0s limit"
        assert len(blueprints) == 100, "Not all blueprints were created"

        # Statistical analysis
        avg_creation_time = statistics.mean(creation_times)
        max_creation_time = max(creation_times)
        min_creation_time = min(creation_times)

        # Individual blueprint creation should be fast
        assert avg_creation_time < 0.01, f"Average creation time {avg_creation_time:.4f}s too slow"
        assert max_creation_time < 0.05, f"Max creation time {max_creation_time:.4f}s too slow"
        assert min_creation_time > 0, "Creation time should be positive"

        # Validate blueprint integrity
        for i, bp in enumerate(blueprints):
            assert bp.blueprint_id == f"perf_{i}"
            assert bp.NAME == "geese"
            assert hasattr(bp, 'ux')
            assert hasattr(bp, 'spinner')

    def test_memory_usage_during_creation(self):
        """Test memory usage during blueprint creation."""
        process = psutil.Process()
        initial_memory = process.memory_info().rss / 1024 / 1024  # MB

        # Create many blueprints
        blueprints = []
        for i in range(200):
            bp = GeeseBlueprint(blueprint_id=f"memory_{i}")
            blueprints.append(bp)

        final_memory = process.memory_info().rss / 1024 / 1024  # MB
        memory_increase = final_memory - initial_memory

        # Memory increase should be reasonable (< 50MB)
        assert memory_increase < 50.0
        assert len(blueprints) == 200

    def test_concurrent_blueprint_operations(self):
        """Test concurrent blueprint operations."""
        results = []
        errors = []

        def create_and_test_blueprint(index):
            try:
                start = time.time()
                bp = GeeseBlueprint(blueprint_id=f"concurrent_{index}")
                end = time.time()

                results.append({
                    'index': index,
                    'duration': end - start,
                    'blueprint': bp
                })
            except Exception as e:
                errors.append(e)

        # Create 20 threads
        threads = []
        for i in range(20):
            thread = threading.Thread(target=create_and_test_blueprint, args=(i,))
            threads.append(thread)

        start_time = time.time()
        # Start all threads
        for thread in threads:
            thread.start()

        # Wait for all threads
        for thread in threads:
            thread.join()

        end_time = time.time()
        total_duration = end_time - start_time

        # Verify results
        assert len(results) == 20
        assert len(errors) == 0
        assert total_duration < 5.0  # Should complete in under 5 seconds

        # Check individual operation times
        for result in results:
            assert result['duration'] < 1.0  # Each operation < 1 second

    def test_configuration_loading_performance(self):
        """Test performance of configuration loading."""
        # Test with various config sizes
        config_sizes = [10, 50, 100, 500]

        for size in config_sizes:
            config = {}
            for i in range(size):
                config[f"key_{i}"] = f"value_{i}"

            start_time = time.time()
            bp = GeeseBlueprint(blueprint_id=f"config_perf_{size}", config=config)
            end_time = time.time()

            duration = end_time - start_time
            # Should load config quickly regardless of size
            assert duration < 0.1  # Under 100ms
            assert bp is not None

    def test_large_scale_blueprint_management(self):
        """Test managing large numbers of blueprints."""
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss / 1024 / 1024

        # Create 500 blueprints
        blueprints = []
        for i in range(500):
            bp = GeeseBlueprint(blueprint_id=f"large_scale_{i}")
            blueprints.append(bp)

        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss / 1024 / 1024

        creation_time = end_time - start_time
        memory_usage = end_memory - start_memory

        # Performance assertions
        assert creation_time < 10.0  # Under 10 seconds
        assert memory_usage < 100.0  # Under 100MB increase
        assert len(blueprints) == 500

        # Cleanup
        del blueprints

    def test_operation_throughput(self):
        """Test operation throughput under load."""
        operations_per_second = []

        for batch in range(5):
            start_time = time.time()

            # Perform 100 operations
            for i in range(100):
                bp = GeeseBlueprint(blueprint_id=f"throughput_{batch}_{i}")
                assert bp is not None

            end_time = time.time()
            duration = end_time - start_time
            ops_per_sec = 100 / duration
            operations_per_second.append(ops_per_sec)

        # Average throughput should be reasonable
        avg_throughput = sum(operations_per_second) / len(operations_per_second)
        assert avg_throughput > 50  # At least 50 operations per second

    def test_memory_efficiency_over_time(self):
        """Test memory efficiency over extended operations."""
        process = psutil.Process()
        memory_readings = []

        # Perform operations over time
        for cycle in range(10):
            # Create batch of blueprints
            blueprints = []
            for i in range(50):
                bp = GeeseBlueprint(blueprint_id=f"efficiency_{cycle}_{i}")
                blueprints.append(bp)

            # Record memory
            memory_mb = process.memory_info().rss / 1024 / 1024
            memory_readings.append(memory_mb)

            # Cleanup
            del blueprints
            import gc
            gc.collect()

        # Memory should not grow significantly over time
        if len(memory_readings) > 1:
            memory_growth = memory_readings[-1] - memory_readings[0]
            assert memory_growth < 20.0  # Less than 20MB growth over 10 cycles

    def test_cpu_usage_during_operations(self):
        """Test CPU usage during operations."""
        process = psutil.Process()

        start_cpu = process.cpu_percent(interval=0.1)

        # Perform CPU-intensive operations
        for i in range(1000):
            bp = GeeseBlueprint(blueprint_id=f"cpu_test_{i}")
            # Perform some basic operations
            config = bp._config
            assert config is not None

        end_cpu = process.cpu_percent(interval=0.1)

        # CPU usage should be reasonable
        cpu_increase = end_cpu - start_cpu
        assert cpu_increase < 50.0  # Less than 50% CPU increase

    def test_response_time_consistency(self):
        """Test response time consistency."""
        response_times = []

        # Measure response times for multiple operations
        for i in range(50):
            start_time = time.time()
            GeeseBlueprint(blueprint_id=f"consistency_{i}")
            end_time = time.time()

            response_time = end_time - start_time
            response_times.append(response_time)

        # Calculate statistics
        avg_time = sum(response_times) / len(response_times)
        max_time = max(response_times)
        min_time = min(response_times)

        # Response times should be consistent
        assert avg_time < 0.01  # Average under 10ms
        assert max_time < 0.1   # Max under 100ms
        assert max_time / min_time < 10  # Max should not be 10x min

    def test_scalability_with_complex_configs(self):
        """Test scalability with complex configurations."""
        # Create increasingly complex configurations
        for complexity in range(1, 11):
            config = self._generate_complex_config(complexity)

            start_time = time.time()
            GeeseBlueprint(blueprint_id=f"complex_{complexity}", config=config)
            end_time = time.time()

            duration = end_time - start_time

            # Should scale reasonably with complexity
            expected_max_time = complexity * 0.01  # 10ms per complexity level
            assert duration < expected_max_time

    def _generate_complex_config(self, complexity):
        """Generate complex configuration for testing."""
        config = {}
        for i in range(complexity):
            config[f"level_{i}"] = {
                "nested": {"value": f"test_{i}"},
                "array": list(range(i + 1)),
                "boolean": i % 2 == 0
            }
        return config

    def test_resource_cleanup_efficiency(self):
        """Test efficiency of resource cleanup."""
        process = psutil.Process()

        # Create resources
        start_memory = process.memory_info().rss / 1024 / 1024
        blueprints = []

        for i in range(100):
            bp = GeeseBlueprint(blueprint_id=f"cleanup_{i}")
            blueprints.append(bp)

        peak_memory = process.memory_info().rss / 1024 / 1024

        # Cleanup
        del blueprints
        import gc
        gc.collect()

        end_memory = process.memory_info().rss / 1024 / 1024

        memory_cleanup = peak_memory - end_memory
        memory_efficiency = memory_cleanup / (peak_memory - start_memory)

        # Should cleanup at least 80% of allocated memory
        assert memory_efficiency > 0.8

    def test_load_distribution_under_concurrency(self):
        """Test load distribution under concurrent operations."""
        import concurrent.futures

        def create_blueprint_with_timing(index):
            start = time.time()
            GeeseBlueprint(blueprint_id=f"load_{index}")
            end = time.time()
            return end - start

        # Use thread pool for concurrent execution
        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            futures = [executor.submit(create_blueprint_with_timing, i) for i in range(100)]
            response_times = [future.result() for future in concurrent.futures.as_completed(futures)]

        # Analyze load distribution
        avg_time = sum(response_times) / len(response_times)
        std_dev = (sum((t - avg_time) ** 2 for t in response_times) / len(response_times)) ** 0.5

        # Standard deviation should be reasonable (not too much variation)
        coefficient_of_variation = std_dev / avg_time
        assert coefficient_of_variation < 0.5  # Less than 50% variation
