"""
Loaders module for the data layer.
"""
from .loader_interface import LoaderInterface
from .loader_supabase import SupabaseLoader

__all__ = ["LoaderInterface", "SupabaseLoader"]