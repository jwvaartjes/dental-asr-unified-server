"""
FastAPI router for lexicon management endpoints.

This module provides all the lexicon and protected words endpoints
that were previously in the main server_windows_spsc.py file.
"""
import re
import logging
from typing import Any, Dict, List, Optional
from fastapi import APIRouter, HTTPException, status, Request, Query, Depends

from .schemas import LexiconTermRequest, LexiconCategoryRequest, ProtectedWordsRequest, VariantRequest, MultiWordVariantRequest, AutoVariantRequest, AutoMultiWordVariantRequest, CanonicalTermInfoRequest
from ..data.registry import DataRegistry

logger = logging.getLogger(__name__)

# Create router
router = APIRouter(prefix="/api", tags=["lexicon"])


def get_data_registry(request: Request) -> DataRegistry:
    """Dependency to get data registry from app state."""
    return request.app.state.data_registry


def get_admin_user_id(request: Request) -> str:
    """Dependency to get admin user ID."""
    data_registry = get_data_registry(request)
    return data_registry.loader.get_admin_id()

async def get_authenticated_admin_user_id(request: Request) -> str:
    """Get admin user ID after verifying user is actually admin via httpOnly cookie"""
    from ..pairing.security import JWTHandler
    
    # 1. Extract token from httpOnly cookie
    token = request.cookies.get("session_token")
    if not token:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Authentication required"
        )
    
    # 2. Verify token and get user email
    payload = JWTHandler.verify_token(token)
    if not payload:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid or expired token"
        )
    
    user_email = payload.get("user") or payload.get("email") or payload.get("user_id")
    if not user_email:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid token format"
        )
    
    # 3. Get user from Supabase and check admin role
    try:
        from ..users.auth import user_auth
        user = await user_auth.get_user_by_email(user_email)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="User not found"
            )
        
        if user.role not in ["admin", "super_admin"]:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Admin privileges required for lexicon management"
            )
        
        # 4. Return actual user ID (user-specific data)
        return user.id
        
    except ImportError:
        # Fallback if user_auth not available - use hardcoded admin
        data_registry = get_data_registry(request)
        return data_registry.loader.get_admin_id()
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error in admin authentication: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Authentication check failed"
        )


# Lexicon Endpoints
@router.post("/lexicon/add-canonical")
async def add_canonical_term(
    request: LexiconTermRequest,
    admin_user_id: str = Depends(get_authenticated_admin_user_id),
    data_registry: DataRegistry = Depends(get_data_registry)
):
    """Add a canonical term to the lexicon (Supabase cloud storage)"""
    term = request.term  # Validated with case preservation
    category = request.category
    
    # Normalize for comparison: remove punctuation and spaces, lowercase
    def normalize_for_comparison(text):
        return re.sub(r'[^a-z0-9]', '', text.lower())
    
    normalized_term = normalize_for_comparison(term)
    
    try:
        # Load current lexicon from Supabase
        lexicon = await data_registry.get_lexicon(admin_user_id)
        
        # Add category if it doesn't exist
        if category not in lexicon:
            lexicon[category] = []
        
        # Check for duplicates across ALL categories
        duplicate_found = None
        for cat_name, cat_terms in lexicon.items():
            # Skip abbreviation categories
            if cat_name.endswith('_abbr') or cat_name.startswith('element'):
                continue
            
            # Check each term in this category
            if isinstance(cat_terms, list):
                for existing_term in cat_terms:
                    if normalize_for_comparison(existing_term) == normalized_term:
                        duplicate_found = (cat_name, existing_term)
                        break
            
            if duplicate_found:
                break
        
        if not duplicate_found:
            # PRESERVE USER INPUT CAPITALIZATION for ALL canonical terms
            term_to_add = term.strip()  # Keep exact user input capitalization
            
            lexicon[category].append(term_to_add)
            
            # Save updated lexicon to Supabase
            success = await data_registry.save_lexicon(admin_user_id, lexicon)
            if not success:
                raise Exception("Failed to save lexicon to Supabase")
            
            return {"success": True, "message": f"Added '{term_to_add}' to category '{category}'"}
        else:
            found_category, found_term = duplicate_found
            if found_category == category:
                return {"success": False, "message": f"Term '{term}' already exists in this category as '{found_term}'"}
            else:
                return {"success": False, "message": f"Term '{term}' already exists in category '{found_category}' as '{found_term}'. Terms must be unique across all categories."}
    
    except Exception as e:
        logger.error(f"Error adding canonical term: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.delete("/lexicon/remove-canonical")
async def remove_canonical_term(
    request: LexiconTermRequest,
    admin_user_id: str = Depends(get_authenticated_admin_user_id),
    data_registry: DataRegistry = Depends(get_data_registry)
):
    """Remove a canonical term from the lexicon"""
    term = request.term
    category = request.category
    
    try:
        # Load current lexicon from Supabase
        lexicon = await data_registry.get_lexicon(admin_user_id)
        
        if category not in lexicon:
            return {"success": False, "message": f"Category '{category}' not found"}
        
        # Find the term case-insensitively
        term_to_remove = None
        for existing_term in lexicon[category]:
            if existing_term.lower() == term.lower():
                term_to_remove = existing_term
                break
        
        if term_to_remove:
            lexicon[category].remove(term_to_remove)
            
            # Save updated lexicon to Supabase
            success = await data_registry.save_lexicon(admin_user_id, lexicon)
            if not success:
                raise Exception("Failed to save lexicon to Supabase")
            
            return {"success": True, "message": f"Removed '{term_to_remove}' from category '{category}'"}
        else:
            return {"success": False, "message": f"Term '{term}' not found in category '{category}'"}
    
    except Exception as e:
        logger.error(f"Error removing canonical term: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lexicon/categories")
async def get_lexicon_categories(
    admin_user_id: str = Depends(get_authenticated_admin_user_id),
    data_registry: DataRegistry = Depends(get_data_registry)
):
    """Get all lexicon categories from Supabase"""
    try:
        # Load current lexicon from Supabase
        lexicon = await data_registry.get_lexicon(admin_user_id)
        
        # Filter to only show non-abbreviation categories
        categories = [k for k in lexicon.keys() if not k.endswith('_abbr') and not k.startswith('element')]
        return {"categories": sorted(categories)}
    
    except Exception as e:
        logger.error(f"Error getting categories from Supabase: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lexicon/terms/{category}")
async def get_category_terms(
    category: str,
    admin_user_id: str = Depends(get_authenticated_admin_user_id),
    data_registry: DataRegistry = Depends(get_data_registry)
):
    """Get all terms in a specific category from Supabase"""
    try:
        # Load current lexicon from Supabase
        lexicon = await data_registry.get_lexicon(admin_user_id)
        
        if category not in lexicon:
            raise HTTPException(status_code=404, detail=f"Category '{category}' not found")
        
        terms = lexicon[category]
        return {"category": category, "terms": sorted(terms), "count": len(terms)}
    
    except Exception as e:
        logger.error(f"Error getting terms for category {category}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lexicon/full")
async def get_full_lexicon(
    admin_user_id: str = Depends(get_authenticated_admin_user_id),
    data_registry: DataRegistry = Depends(get_data_registry)
):
    """Get the complete lexicon from cache - SUPER FAST!"""
    try:
        # Get from cache/data registry
        lexicon = await data_registry.get_lexicon(admin_user_id)
        protect_data = await data_registry.get_protected_words(admin_user_id)
        
        # Include abbreviations/variants if they exist
        full_lexicon = {}
        for key, value in lexicon.items():
            # Include main categories and their abbreviation variants
            if isinstance(value, list):
                full_lexicon[key] = value
            elif isinstance(value, dict) and key.endswith('_abbr'):
                # Include abbreviation mappings
                full_lexicon[key] = value
        
        # Also include protected words as a special category
        if protect_data and 'categories' in protect_data:
            full_lexicon['protected_words'] = []
            for category, items in protect_data['categories'].items():
                if isinstance(items, list):
                    for item in items:
                        if isinstance(item, dict) and 'word' in item:
                            full_lexicon['protected_words'].append(item['word'])
                        elif isinstance(item, str):
                            full_lexicon['protected_words'].append(item)
        
        return {
            "lexicon": full_lexicon,
            "categories": [k for k in lexicon.keys() if not k.endswith('_abbr')],
            "source": "memory_cache"  # Indicate data is from cache - INSTANT!
        }
    except Exception as e:
        logger.error(f"Error fetching full lexicon: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lexicon/search")
async def search_lexicon(
    q: str = Query(..., min_length=1),
    admin_user_id: str = Depends(get_authenticated_admin_user_id),
    data_registry: DataRegistry = Depends(get_data_registry)
):
    """
    Search for terms in the lexicon and protected words
    Returns matching terms with their category and source
    """
    try:
        search_term = q.lower()
        results = []
        
        # Use cached lexicon data
        lexicon = await data_registry.get_lexicon(admin_user_id)
        
        # Search in lexicon categories
        for category, terms in lexicon.items():
            # Skip abbreviation categories (internal use)
            if category.endswith('_abbr'):
                continue
                
            if isinstance(terms, list):
                for term in terms:
                    if search_term in term.lower():
                        results.append({
                            "term": term,
                            "category": category,
                            "source": "lexicon",
                            "protected": False
                        })
        
        # Use cached protected words data
        protect_data = await data_registry.get_protected_words(admin_user_id)
        if protect_data and 'categories' in protect_data:
            for category, items in protect_data['categories'].items():
                if isinstance(items, list):
                    for item in items:
                        # Protected words can be strings or dicts with 'word' key
                        word = item if isinstance(item, str) else item.get('word', '')
                        if search_term in word.lower():
                            results.append({
                                "term": word,
                                "category": category,
                                "source": "protected",
                                "protected": True
                            })
        
        # Sort results by relevance (exact match first, then alphabetical)
        results.sort(key=lambda x: (
            not x['term'].lower().startswith(search_term),  # Exact prefix matches first
            x['term'].lower()  # Then alphabetical
        ))
        
        return {
            "query": q,
            "count": len(results),
            "results": results[:100]  # Limit to 100 results
        }
        
    except Exception as e:
        logger.error(f"Error searching lexicon: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lexicon/add-category")
async def add_lexicon_category(
    request: LexiconCategoryRequest,
    admin_user_id: str = Depends(get_authenticated_admin_user_id),
    data_registry: DataRegistry = Depends(get_data_registry)
):
    """Add a new category to the lexicon"""
    category = request.category
    
    try:
        # Load current lexicon from Supabase
        lexicon = await data_registry.get_lexicon(admin_user_id)
        
        if category not in lexicon:
            lexicon[category] = []
            lexicon[f"{category}_abbr"] = {}
            
            # Save updated lexicon to Supabase
            success = await data_registry.save_lexicon(admin_user_id, lexicon)
            if not success:
                raise Exception("Failed to save lexicon to Supabase")
            
            return {"success": True, "message": f"Added category '{category}'"}
        else:
            return {"success": False, "message": f"Category '{category}' already exists"}
    
    except Exception as e:
        logger.error(f"Error adding category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lexicon/delete-category")
async def delete_lexicon_category(
    request: LexiconCategoryRequest,
    admin_user_id: str = Depends(get_authenticated_admin_user_id),
    data_registry: DataRegistry = Depends(get_data_registry)
):
    """Delete a category from the lexicon"""
    category = request.category
    
    try:
        # Load current lexicon from Supabase
        lexicon = await data_registry.get_lexicon(admin_user_id)
        
        if category in lexicon:
            del lexicon[category]
            # Also remove abbreviations if they exist
            if f"{category}_abbr" in lexicon:
                del lexicon[f"{category}_abbr"]
            
            # Save updated lexicon to Supabase
            success = await data_registry.save_lexicon(admin_user_id, lexicon)
            if not success:
                raise Exception("Failed to save lexicon to Supabase")
            
            return {"success": True, "message": f"Deleted category '{category}'"}
        else:
            return {"success": False, "message": f"Category '{category}' not found"}
    
    except Exception as e:
        logger.error(f"Error deleting category: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Protected Words Endpoints
@router.get("/protect_words")
async def get_protect_words(
    admin_user_id: str = Depends(get_authenticated_admin_user_id),
    data_registry: DataRegistry = Depends(get_data_registry)
):
    """Get protected words from Supabase"""
    try:
        protect_data = await data_registry.get_protected_words(admin_user_id)
        return protect_data
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error loading protected words: {str(e)}")


@router.post("/protect_words")
async def save_protect_words(
    protect_data: dict,
    admin_user_id: str = Depends(get_authenticated_admin_user_id),
    data_registry: DataRegistry = Depends(get_data_registry)
):
    """Save protected words to Supabase"""
    try:
        # Validate new structure with protected_words array
        if not isinstance(protect_data.get('protected_words'), list):
            raise HTTPException(status_code=400, detail="Invalid protect_words structure - expected 'protected_words' array")
        
        # Validate that protected_words contains strings
        words = protect_data['protected_words']
        if not all(isinstance(word, str) for word in words):
            raise HTTPException(status_code=400, detail="All protected_words must be strings")
        
        # Save to Supabase
        success = await data_registry.save_protected_words(admin_user_id, protect_data)
        if not success:
            raise Exception("Failed to save protected words to Supabase")
        
        return {
            "message": "Protected words saved successfully", 
            "count": len(words),
            "words_saved": words
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error saving protected words: {str(e)}")


@router.delete("/protect_words/{word}")
async def delete_protect_word(
    word: str,
    admin_user_id: str = Depends(get_authenticated_admin_user_id),
    data_registry: DataRegistry = Depends(get_data_registry)
):
    """Delete a single protected word"""
    try:
        # Load current protected words
        protect_data = await data_registry.get_protected_words(admin_user_id)
        current_words = protect_data.get('protected_words', [])
        
        # Check if word exists
        if word not in current_words:
            raise HTTPException(status_code=404, detail=f"Protected word '{word}' not found")
        
        # Remove the word
        updated_words = [w for w in current_words if w != word]
        updated_protect_data = {'protected_words': updated_words}
        
        # Save updated list
        success = await data_registry.save_protected_words(admin_user_id, updated_protect_data)
        if not success:
            raise Exception("Failed to save updated protected words to Supabase")
        
        return {
            "message": f"Protected word '{word}' deleted successfully",
            "deleted_word": word,
            "remaining_count": len(updated_words)
        }
        
    except HTTPException:
        raise  # Re-raise HTTP exceptions as-is
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error deleting protected word: {str(e)}")


# Variant Management Endpoints
@router.post("/lexicon/add-variant")
async def add_variant(
    request: VariantRequest,
    admin_user_id: str = Depends(get_authenticated_admin_user_id),
    data_registry: DataRegistry = Depends(get_data_registry)
):
    """Add a variant/abbreviation to a canonical term."""
    canonical_term = request.canonical_term
    variant = request.variant
    category = request.category
    
    try:
        # Load current lexicon from Supabase
        lexicon = await data_registry.get_lexicon(admin_user_id)
        
        # Check if category exists
        if category not in lexicon:
            return {"success": False, "message": f"Category '{category}' not found"}
        
        # Check if canonical term exists in the category
        if canonical_term not in lexicon[category]:
            return {"success": False, "message": f"Canonical term '{canonical_term}' not found in category '{category}'"}
        
        # Ensure abbreviation category exists
        abbr_category = f"{category}_abbr"
        if abbr_category not in lexicon:
            lexicon[abbr_category] = {}
        
        # Add the variant mapping
        if isinstance(lexicon[abbr_category], dict):
            lexicon[abbr_category][variant] = canonical_term
        else:
            # Convert to dict if it's not already
            lexicon[abbr_category] = {variant: canonical_term}
        
        # Save updated lexicon to Supabase
        success = await data_registry.save_lexicon(admin_user_id, lexicon)
        if not success:
            raise Exception("Failed to save lexicon to Supabase")
        
        return {"success": True, "message": f"Added variant '{variant}' → '{canonical_term}' in category '{category}'"}
    
    except Exception as e:
        logger.error(f"Error adding variant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lexicon/remove-variant")
async def remove_variant(
    request: VariantRequest,
    admin_user_id: str = Depends(get_authenticated_admin_user_id),
    data_registry: DataRegistry = Depends(get_data_registry)
):
    """Remove a variant/abbreviation from a canonical term."""
    canonical_term = request.canonical_term
    variant = request.variant
    category = request.category
    
    try:
        # Load current lexicon from Supabase
        lexicon = await data_registry.get_lexicon(admin_user_id)
        
        # Check abbreviation category
        abbr_category = f"{category}_abbr"
        if abbr_category not in lexicon:
            return {"success": False, "message": f"No variants found for category '{category}'"}
        
        # Check if variant exists and maps to the canonical term
        if variant not in lexicon[abbr_category]:
            return {"success": False, "message": f"Variant '{variant}' not found"}
        
        if lexicon[abbr_category][variant] != canonical_term:
            return {"success": False, "message": f"Variant '{variant}' maps to '{lexicon[abbr_category][variant]}', not '{canonical_term}'"}
        
        # Remove the variant
        del lexicon[abbr_category][variant]
        
        # Save updated lexicon to Supabase
        success = await data_registry.save_lexicon(admin_user_id, lexicon)
        if not success:
            raise Exception("Failed to save lexicon to Supabase")
        
        return {"success": True, "message": f"Removed variant '{variant}' from '{canonical_term}' in category '{category}'"}
    
    except Exception as e:
        logger.error(f"Error removing variant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lexicon/add-multiword-variant")
async def add_multiword_variant(
    request: MultiWordVariantRequest,
    admin_user_id: str = Depends(get_authenticated_admin_user_id),
    data_registry: DataRegistry = Depends(get_data_registry)
):
    """Add a multi-word variant phrase to a canonical term."""
    canonical_term = request.canonical_term
    variant_phrase = request.variant_phrase
    category = request.category
    
    try:
        # Load current lexicon from Supabase
        lexicon = await data_registry.get_lexicon(admin_user_id)
        
        # Check if category exists
        if category not in lexicon:
            return {"success": False, "message": f"Category '{category}' not found"}
        
        # Check if canonical term exists in the category
        if canonical_term not in lexicon[category]:
            return {"success": False, "message": f"Canonical term '{canonical_term}' not found in category '{category}'"}
        
        # Ensure abbreviation category exists
        abbr_category = f"{category}_abbr"
        if abbr_category not in lexicon:
            lexicon[abbr_category] = {}
        
        # Add the multi-word variant mapping
        if isinstance(lexicon[abbr_category], dict):
            lexicon[abbr_category][variant_phrase] = canonical_term
        else:
            # Convert to dict if it's not already
            lexicon[abbr_category] = {variant_phrase: canonical_term}
        
        # Save updated lexicon to Supabase
        success = await data_registry.save_lexicon(admin_user_id, lexicon)
        if not success:
            raise Exception("Failed to save lexicon to Supabase")
        
        return {"success": True, "message": f"Added multi-word variant '{variant_phrase}' → '{canonical_term}' in category '{category}'"}
    
    except Exception as e:
        logger.error(f"Error adding multi-word variant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lexicon/remove-multiword-variant")
async def remove_multiword_variant(
    request: MultiWordVariantRequest,
    admin_user_id: str = Depends(get_authenticated_admin_user_id),
    data_registry: DataRegistry = Depends(get_data_registry)
):
    """Remove a multi-word variant phrase from a canonical term."""
    canonical_term = request.canonical_term
    variant_phrase = request.variant_phrase
    category = request.category
    
    try:
        # Load current lexicon from Supabase
        lexicon = await data_registry.get_lexicon(admin_user_id)
        
        # Check abbreviation category
        abbr_category = f"{category}_abbr"
        if abbr_category not in lexicon:
            return {"success": False, "message": f"No variants found for category '{category}'"}
        
        # Check if variant phrase exists and maps to the canonical term
        if variant_phrase not in lexicon[abbr_category]:
            return {"success": False, "message": f"Multi-word variant '{variant_phrase}' not found"}
        
        if lexicon[abbr_category][variant_phrase] != canonical_term:
            return {"success": False, "message": f"Multi-word variant '{variant_phrase}' maps to '{lexicon[abbr_category][variant_phrase]}', not '{canonical_term}'"}
        
        # Remove the variant phrase
        del lexicon[abbr_category][variant_phrase]
        
        # Save updated lexicon to Supabase
        success = await data_registry.save_lexicon(admin_user_id, lexicon)
        if not success:
            raise Exception("Failed to save lexicon to Supabase")
        
        return {"success": True, "message": f"Removed multi-word variant '{variant_phrase}' from '{canonical_term}' in category '{category}'"}
    
    except Exception as e:
        logger.error(f"Error removing multi-word variant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/lexicon/variants/{category}")
async def get_category_variants(
    category: str,
    admin_user_id: str = Depends(get_authenticated_admin_user_id),
    data_registry: DataRegistry = Depends(get_data_registry)
):
    """Get all variants/abbreviations for a specific category."""
    try:
        # Load current lexicon from Supabase
        lexicon = await data_registry.get_lexicon(admin_user_id)
        
        # Check abbreviation category
        abbr_category = f"{category}_abbr"
        if abbr_category not in lexicon:
            return {"category": category, "variants": {}, "count": 0}
        
        variants = lexicon[abbr_category] if isinstance(lexicon[abbr_category], dict) else {}
        return {"category": category, "variants": variants, "count": len(variants)}
    
    except Exception as e:
        logger.error(f"Error getting variants for category {category}: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# Auto-detection Endpoints (Smart Variant Management)
@router.post("/lexicon/find-canonical")
async def find_canonical_term(
    request: CanonicalTermInfoRequest,
    admin_user_id: str = Depends(get_authenticated_admin_user_id),
    data_registry: DataRegistry = Depends(get_data_registry)
):
    """Find which category a canonical term belongs to."""
    canonical_term = request.canonical_term
    
    try:
        # Load current lexicon from Supabase
        lexicon = await data_registry.get_lexicon(admin_user_id)
        
        # Search for the canonical term across all categories
        found_category = None
        for category, terms in lexicon.items():
            # Skip abbreviation categories
            if category.endswith('_abbr') or category.startswith('element'):
                continue
            
            if isinstance(terms, list):
                # Check for exact match (case-insensitive)
                for term in terms:
                    if term.lower() == canonical_term.lower():
                        found_category = category
                        break
            
            if found_category:
                break
        
        if found_category:
            # Also get existing variants for this term
            abbr_category = f"{found_category}_abbr"
            variants = {}
            if abbr_category in lexicon and isinstance(lexicon[abbr_category], dict):
                # Find variants that map to this canonical term
                for variant, mapped_term in lexicon[abbr_category].items():
                    if mapped_term.lower() == canonical_term.lower():
                        variants[variant] = mapped_term
            
            return {
                "success": True, 
                "canonical_term": canonical_term,
                "category": found_category,
                "existing_variants": variants,
                "variant_count": len(variants)
            }
        else:
            return {
                "success": False, 
                "message": f"Canonical term '{canonical_term}' not found in any category"
            }
    
    except Exception as e:
        logger.error(f"Error finding canonical term: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lexicon/add-variant-auto")
async def add_variant_auto(
    request: AutoVariantRequest,
    admin_user_id: str = Depends(get_authenticated_admin_user_id),
    data_registry: DataRegistry = Depends(get_data_registry)
):
    """Add a variant with automatic category detection."""
    canonical_term = request.canonical_term
    variant = request.variant
    
    try:
        # First find the category of the canonical term
        lexicon = await data_registry.get_lexicon(admin_user_id)
        
        found_category = None
        for category, terms in lexicon.items():
            # Skip abbreviation categories
            if category.endswith('_abbr') or category.startswith('element'):
                continue
            
            if isinstance(terms, list):
                # Check for exact match (case-insensitive)
                for term in terms:
                    if term.lower() == canonical_term.lower():
                        found_category = category
                        canonical_term = term  # Use the exact case from lexicon
                        break
            
            if found_category:
                break
        
        if not found_category:
            return {"success": False, "message": f"Canonical term '{canonical_term}' not found in any category"}
        
        # Ensure abbreviation category exists
        abbr_category = f"{found_category}_abbr"
        if abbr_category not in lexicon:
            lexicon[abbr_category] = {}
        
        # Check if variant already exists
        if isinstance(lexicon[abbr_category], dict) and variant in lexicon[abbr_category]:
            existing_mapping = lexicon[abbr_category][variant]
            if existing_mapping.lower() == canonical_term.lower():
                return {"success": False, "message": f"Variant '{variant}' already maps to '{existing_mapping}'"}
            else:
                return {"success": False, "message": f"Variant '{variant}' already exists and maps to '{existing_mapping}'"}
        
        # Add the variant mapping
        if isinstance(lexicon[abbr_category], dict):
            lexicon[abbr_category][variant] = canonical_term
        else:
            # Convert to dict if it's not already
            lexicon[abbr_category] = {variant: canonical_term}
        
        # Save updated lexicon to Supabase
        success = await data_registry.save_lexicon(admin_user_id, lexicon)
        if not success:
            raise Exception("Failed to save lexicon to Supabase")
        
        return {
            "success": True, 
            "message": f"Added variant '{variant}' → '{canonical_term}' in category '{found_category}'",
            "category": found_category,
            "canonical_term": canonical_term,
            "variant": variant
        }
    
    except Exception as e:
        logger.error(f"Error adding auto variant: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/lexicon/add-multiword-variant-auto")
async def add_multiword_variant_auto(
    request: AutoMultiWordVariantRequest,
    admin_user_id: str = Depends(get_authenticated_admin_user_id),
    data_registry: DataRegistry = Depends(get_data_registry)
):
    """Add a multi-word variant with automatic category detection."""
    canonical_term = request.canonical_term
    variant_phrase = request.variant_phrase
    
    try:
        # First find the category of the canonical term
        lexicon = await data_registry.get_lexicon(admin_user_id)
        
        found_category = None
        for category, terms in lexicon.items():
            # Skip abbreviation categories
            if category.endswith('_abbr') or category.startswith('element'):
                continue
            
            if isinstance(terms, list):
                # Check for exact match (case-insensitive)
                for term in terms:
                    if term.lower() == canonical_term.lower():
                        found_category = category
                        canonical_term = term  # Use the exact case from lexicon
                        break
            
            if found_category:
                break
        
        if not found_category:
            return {"success": False, "message": f"Canonical term '{canonical_term}' not found in any category"}
        
        # Ensure abbreviation category exists
        abbr_category = f"{found_category}_abbr"
        if abbr_category not in lexicon:
            lexicon[abbr_category] = {}
        
        # Check if variant phrase already exists
        if isinstance(lexicon[abbr_category], dict) and variant_phrase in lexicon[abbr_category]:
            existing_mapping = lexicon[abbr_category][variant_phrase]
            if existing_mapping.lower() == canonical_term.lower():
                return {"success": False, "message": f"Multi-word variant '{variant_phrase}' already maps to '{existing_mapping}'"}
            else:
                return {"success": False, "message": f"Multi-word variant '{variant_phrase}' already exists and maps to '{existing_mapping}'"}
        
        # Add the multi-word variant mapping
        if isinstance(lexicon[abbr_category], dict):
            lexicon[abbr_category][variant_phrase] = canonical_term
        else:
            # Convert to dict if it's not already
            lexicon[abbr_category] = {variant_phrase: canonical_term}
        
        # Save updated lexicon to Supabase
        success = await data_registry.save_lexicon(admin_user_id, lexicon)
        if not success:
            raise Exception("Failed to save lexicon to Supabase")
        
        return {
            "success": True, 
            "message": f"Added multi-word variant '{variant_phrase}' → '{canonical_term}' in category '{found_category}'",
            "category": found_category,
            "canonical_term": canonical_term,
            "variant_phrase": variant_phrase
        }
    
    except Exception as e:
        logger.error(f"Error adding auto multi-word variant: {e}")
        raise HTTPException(status_code=500, detail=str(e))