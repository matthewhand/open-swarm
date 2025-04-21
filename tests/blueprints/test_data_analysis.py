import pytest
import asyncio
from src.swarm.blueprints.blueprint_data_analysis import DataAnalysisBlueprint

@pytest.mark.asyncio
async def test_summary_statistics_normal():
    blueprint = DataAnalysisBlueprint(blueprint_id="test_data_analysis")
    data = [1, 2, 3, 4, 5]
    stats = await blueprint.summary_statistics(data)
    assert stats["mean"] == 3
    assert stats["median"] == 3
    assert stats["mode"] in (1, 2, 3, 4, 5)  # All values are valid modes for unique data
    assert round(stats["stdev"], 5) == 1.58114

@pytest.mark.asyncio
async def test_summary_statistics_empty():
    blueprint = DataAnalysisBlueprint(blueprint_id="test_data_analysis")
    data = []
    stats = await blueprint.summary_statistics(data)
    assert "error" in stats
    assert stats["error"] == "No data provided."

@pytest.mark.asyncio
async def test_summary_statistics_invalid():
    blueprint = DataAnalysisBlueprint(blueprint_id="test_data_analysis")
    data = ["a", "b", "c"]
    stats = await blueprint.summary_statistics(data)
    assert stats["mean"] is None
    assert stats["median"] is None
    assert stats["mode"] is None
    assert stats["stdev"] is None

@pytest.mark.asyncio
async def test_filter_data_basic():
    blueprint = DataAnalysisBlueprint(blueprint_id="test_data_analysis")
    data = [
        {"name": "Alice", "age": 30},
        {"name": "Bob", "age": 25},
        {"name": "Alice", "age": 40}
    ]
    criteria = {"name": "Alice"}
    filtered = await blueprint.filter_data(data, criteria)
    assert len(filtered) == 2
    assert all(row["name"] == "Alice" for row in filtered)

@pytest.mark.asyncio
async def test_filter_data_invalid():
    blueprint = DataAnalysisBlueprint(blueprint_id="test_data_analysis")
    assert await blueprint.filter_data(None, {"x": 1}) == []
    assert await blueprint.filter_data([1, 2, 3], {"x": 1}) == []
    assert await blueprint.filter_data([{"x": 1}], None) == []

@pytest.mark.asyncio
async def test_generate_report():
    blueprint = DataAnalysisBlueprint(blueprint_id="test_data_analysis")
    analysis_results = {"mean": 3, "median": 3, "mode": 1, "stdev": 1.58}
    report = await blueprint.generate_report(analysis_results)
    assert "Data Analysis Report:" in report
    assert "- Mean: 3" in report
    assert "- Stdev: 1.58" in report

@pytest.mark.asyncio
async def test_generate_report_invalid():
    blueprint = DataAnalysisBlueprint(blueprint_id="test_data_analysis")
    report = await blueprint.generate_report(None)
    assert "No analysis results to report" in report
