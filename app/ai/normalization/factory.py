#!/usr/bin/env python3
"""
NormalizationFactory - Async factory for creating sync NormalizationPipeline instances

This factory loads all data asynchronously from Supabase and creates a synchronous
pipeline with in-memory data for optimal performance.
"""

import logging
from typing import Dict, Any, Optional

from .pipeline import NormalizationPipeline

logger = logging.getLogger(__name__)


class NormalizationFactory:
    """
    Factory for creating NormalizationPipeline instances with async data loading.
    
    This pattern allows us to:
    1. Load all data async from Supabase once
    2. Create a pure sync pipeline with in-memory data
    3. Avoid async/await in the actual normalization logic
    """
    
    @staticmethod
    async def create(data_registry, user_id: str, extra_config: Optional[Dict[str, Any]] = None) -> NormalizationPipeline:
        """
        Create a NormalizationPipeline by loading all data asynchronously.
        
        Args:
            data_registry: DataRegistry instance for loading data from Supabase
            user_id: User ID to load data for
            extra_config: Optional configuration override
            
        Returns:
            NormalizationPipeline: Fully initialized sync pipeline with in-memory data
        """
        logger.info(f"🏭 Creating NormalizationPipeline for user {user_id}")
        
        try:
            # Load all data asynchronously from Supabase
            logger.debug("Loading lexicon data...")
            lexicon_data = await data_registry.get_lexicon(user_id)
            if not lexicon_data:
                raise RuntimeError(f"Lexicon ontbreekt voor user_id={user_id}")
            
            logger.debug("Loading configuration...")
            config = await data_registry.get_config(user_id) or {}
            if extra_config:
                config.update(extra_config)
            
            # Load custom patterns from Supabase
            logger.debug("Loading custom patterns...")
            try:
                custom_patterns = await data_registry.get_custom_patterns(user_id)
                if custom_patterns:
                    lexicon_data["custom_patterns"] = custom_patterns
                    logger.info(f"✅ Loaded custom patterns for user {user_id}")
                else:
                    logger.info(f"No custom patterns found for user {user_id}")
            except Exception as e:
                logger.warning(f"⚠️ Failed to load custom patterns: {e}")
                # Continue without custom patterns
            
            logger.debug("Loading protected words...")
            protected_words = await data_registry.get_protected_words(user_id)
            
            # Merge all data into a single lexicon structure
            combined_lexicon = {
                **lexicon_data,
                'protect_words': protected_words.get('words', [])
            }
            
            # Pass pipeline flags to learnable normalizer config
            # This enables the pipeline's enable_phonetic_matching flag to control 
            # the phonetic matching in DentalNormalizerLearnable
            if 'matching' not in config:
                config['matching'] = {}
            # Use the pipeline's enable_phonetic_matching flag if available
            pipeline_phonetic_flag = config.get('normalization', {}).get('enable_phonetic_matching', True)
            config['matching']['phonetic_enabled'] = pipeline_phonetic_flag
            
            # Validate required configuration
            vg = (config.get("variant_generation") or {})
            if vg.get("separators") is None or vg.get("element_separators") is None:
                raise RuntimeError("variant_generation.separators/element_separators ontbreken in config")
            
            # Create sync pipeline with all data in memory
            pipeline = NormalizationPipeline(
                lexicon_data=combined_lexicon,
                config=config
            )
            
            logger.info(f"✅ NormalizationPipeline created successfully for user {user_id}")
            return pipeline
            
        except Exception as e:
            logger.error(f"❌ Failed to create NormalizationPipeline: {e}")
            raise
    
    @staticmethod
    async def create_for_admin(data_registry, extra_config: Optional[Dict[str, Any]] = None) -> NormalizationPipeline:
        """
        Convenience method to create pipeline for admin user.
        
        Args:
            data_registry: DataRegistry instance
            extra_config: Optional configuration override
            
        Returns:
            NormalizationPipeline: Pipeline initialized with admin data
        """
        # Get admin ID from the loader
        admin_id = data_registry.loader.get_admin_id()
        return await NormalizationFactory.create(data_registry, admin_id, extra_config)