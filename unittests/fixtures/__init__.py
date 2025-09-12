"""
Test fixtures for normalization unit tests
"""

from .test_data_registry import (
    MockDataRegistry,
    create_mock_data_registry,
    get_test_config
)

__all__ = [
    'MockDataRegistry',
    'create_mock_data_registry', 
    'get_test_config'
]