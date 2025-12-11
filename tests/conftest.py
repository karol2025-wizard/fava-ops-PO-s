# conftest.py
import pytest


def pytest_configure(config):
    """Optional: Add custom markers for different test categories"""
    config.addinivalue_line(
        "markers", "integration: mark test as integration test"
    )
    config.addinivalue_line(
        "markers", "calculation: mark test as calculation validation test"
    )