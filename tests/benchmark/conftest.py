"""Configuration for benchmark tests."""


def pytest_configure(config):  # type: ignore[no-untyped-def]
    """Register the benchmark marker."""
    config.addinivalue_line(
        "markers", "benchmark: mark test as a performance benchmark"
    )
