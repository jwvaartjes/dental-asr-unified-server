#!/usr/bin/env python3
"""
Pytest configuration and fixtures for normalization tests

This module provides session-scoped fixtures that load data once from Supabase
and create NormalizationPipeline instances for testing.
"""

import pytest
import pytest_asyncio
import sys
import os
from typing import Dict, Any

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../'))
sys.path.insert(0, project_root)

from app.data.registry import DataRegistry
from app.data.cache.cache_memory import InMemoryCache
from app.data.loaders.loader_supabase import SupabaseLoader
from app.ai.normalization import NormalizationFactory, NormalizationPipeline


@pytest_asyncio.fixture(scope="session")
async def data_registry():
    """Session-scoped DataRegistry fixture - loads data once for entire test session"""
    cache = InMemoryCache()
    loader = SupabaseLoader()
    registry = DataRegistry(cache=cache, loader=loader)
    return registry


@pytest_asyncio.fixture(scope="session") 
async def normalization_pipeline(data_registry):
    """Session-scoped NormalizationPipeline fixture using admin user data"""
    pipeline = await NormalizationFactory.create_for_admin(data_registry)
    return pipeline


@pytest_asyncio.fixture(scope="session")
async def test_config(data_registry):
    """Session-scoped configuration fixture"""
    admin_id = data_registry.loader.get_admin_id()
    config = await data_registry.get_config(admin_id)
    return config


@pytest_asyncio.fixture(scope="session")
async def test_lexicon_data(data_registry):
    """Session-scoped lexicon data fixture"""
    admin_id = data_registry.loader.get_admin_id()
    lexicon = await data_registry.get_lexicon(admin_id)
    return lexicon


@pytest_asyncio.fixture
async def user_pipeline(data_registry):
    """Function-scoped fixture for creating user-specific pipelines"""
    async def _create_user_pipeline(user_id: str, config: Dict[str, Any] = None):
        return await NormalizationFactory.create(data_registry, user_id, config)
    return _create_user_pipeline