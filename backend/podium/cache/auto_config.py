"""Auto-generate cache configuration from Pydantic models.

This module eliminates manual cache configuration by:
1. Auto-detecting SingleRecordFields from type annotations
2. Auto-generating normalization functions
3. Auto-deriving Airtable index mappings (field → field_id convention)
4. Detecting indexed/sortable fields from Pydantic Field metadata
"""

from typing import Any, Callable, Dict, Set, Type, get_origin, get_type_hints
from pydantic import BaseModel
from annotated_types import Len


def is_single_record_field(annotation) -> bool:
    """Check if a type annotation is a SingleRecordField.
    
    SingleRecordField = Annotated[List[str], Len(min_length=1, max_length=1)]
    
    Handles both direct use (field: SingleRecordField) and inline use.
    """
    # Import here to avoid circular imports
    from podium.constants import SingleRecordField
    
    # Check if it's the SingleRecordField type alias itself
    if annotation is SingleRecordField or annotation == SingleRecordField:
        return True
    
    # Check if it's an Annotated type with Len(1,1) metadata
    if not hasattr(annotation, "__metadata__"):
        return False
    
    # Check for Len(1, 1) in metadata
    for metadata in annotation.__metadata__:
        if isinstance(metadata, Len):
            return metadata.min_length == 1 and metadata.max_length == 1
    
    return False


def is_multi_record_field(annotation) -> bool:
    """Check if a type annotation is a MultiRecordField (List[str] without Len constraint)."""
    origin = get_origin(annotation)
    if origin is not list:
        return False
    
    # It's a list, but not a SingleRecordField
    return not is_single_record_field(annotation)


def detect_single_record_fields(model: Type[BaseModel]) -> Set[str]:
    """Auto-detect all SingleRecordField fields in a Pydantic model."""
    single_fields = set()
    
    # Use get_type_hints to resolve string annotations (from __future__ import annotations)
    try:
        type_hints = get_type_hints(model, include_extras=True)
    except Exception:
        type_hints = {}
    
    for field_name in model.model_fields.keys():
        # First try resolved type hints
        if field_name in type_hints:
            if is_single_record_field(type_hints[field_name]):
                single_fields.add(field_name)
                continue
        
        # Fallback: check annotations in the class hierarchy
        for cls in model.__mro__:
            if hasattr(cls, '__annotations__') and field_name in cls.__annotations__:
                annotation = cls.__annotations__[field_name]
                if is_single_record_field(annotation):
                    single_fields.add(field_name)
                    break
    
    return single_fields


def detect_indexed_fields(model: Type[BaseModel]) -> Set[str]:
    """Auto-detect fields marked for indexing via Field(json_schema_extra={"indexed": True}).
    
    This includes fields using SingleRecordField (which has indexed=True in its metadata).
    """
    indexed = set()
    
    # Use get_type_hints to resolve string annotations
    try:
        type_hints = get_type_hints(model, include_extras=True)
    except Exception:
        type_hints = {}
    
    for field_name, field_info in model.model_fields.items():
        # Check if field itself has indexed metadata
        if field_info.json_schema_extra and field_info.json_schema_extra.get("indexed"):
            indexed.add(field_name)
            continue
        
        # Check resolved type hints first
        if field_name in type_hints:
            annotation = type_hints[field_name]
            if hasattr(annotation, '__metadata__'):
                for metadata in annotation.__metadata__:
                    if hasattr(metadata, 'json_schema_extra') and metadata.json_schema_extra:
                        if metadata.json_schema_extra.get("indexed"):
                            indexed.add(field_name)
                            break
                if field_name in indexed:
                    continue
        
        # Fallback: check class hierarchy annotations
        for cls in model.__mro__:
            if hasattr(cls, '__annotations__') and field_name in cls.__annotations__:
                annotation = cls.__annotations__[field_name]
                if hasattr(annotation, '__metadata__'):
                    for metadata in annotation.__metadata__:
                        if hasattr(metadata, 'json_schema_extra') and metadata.json_schema_extra:
                            if metadata.json_schema_extra.get("indexed"):
                                indexed.add(field_name)
                                break
                if field_name in indexed:
                    break
    
    return indexed


def detect_sortable_fields(model: Type[BaseModel]) -> Set[str]:
    """Auto-detect fields marked for sorting via Field(json_schema_extra={"sortable": True})."""
    sortable = set()
    
    for field_name, field_info in model.model_fields.items():
        if field_info.json_schema_extra and field_info.json_schema_extra.get("sortable"):
            sortable.add(field_name)
    
    return sortable


def make_auto_normalize(single_record_fields: Set[str]) -> Callable[[dict], dict]:
    """Generate a normalization function that flattens all SingleRecordFields."""
    def normalize(data: dict) -> dict:
        for field in single_record_fields:
            if field in data and isinstance(data[field], list) and len(data[field]) > 0:
                data[field] = data[field][0]
        return data
    
    return normalize


def make_auto_airtable_mapping(
    indexed_single_fields: Set[str],
    indexed_non_single_fields: Set[str],
    custom_mappings: Dict[str, str] = None
) -> Dict[str, str]:
    """Auto-generate index_to_airtable mappings using field → field_id convention.
    
    Args:
        indexed_single_fields: Set of SingleRecordField names that are indexed
        indexed_non_single_fields: Set of non-SingleRecordField indexed fields
        custom_mappings: Optional overrides for non-standard mappings
    
    Returns:
        Dict mapping cache field names to Airtable lookup field names
    """
    mappings = {}
    
    # Apply convention: field → field_id for SingleRecordFields
    for field in indexed_single_fields:
        mappings[field] = f"{field}_id"
    
    # Identity mapping for non-SingleRecordFields
    for field in indexed_non_single_fields:
        mappings[field] = field
    
    # Apply custom overrides
    if custom_mappings:
        mappings.update(custom_mappings)
    
    return mappings


def auto_detect_cache_config(
    model: Type[BaseModel],
    custom_indexed: Set[str] = None,
    custom_sortable: Set[str] = None,
    custom_airtable_mappings: Dict[str, str] = None,
) -> Dict[str, Any]:
    """Auto-detect all cache configuration from a Pydantic model.
    
    Args:
        model: Pydantic model to analyze
        custom_indexed: Additional fields to index (beyond auto-detected)
        custom_sortable: Additional fields to make sortable (beyond auto-detected)
        custom_airtable_mappings: Custom Airtable field name mappings
    
    Returns:
        Dict with keys: indexed_fields, sortable_fields, normalize_fn, index_to_airtable
    """
    # Auto-detect SingleRecordFields
    single_record_fields = detect_single_record_fields(model)
    
    # Auto-detect indexed/sortable from Field metadata
    auto_indexed = detect_indexed_fields(model)
    auto_sortable = detect_sortable_fields(model)
    
    # Merge with custom additions
    indexed_fields = auto_indexed | (custom_indexed or set())
    sortable_fields = auto_sortable | (custom_sortable or set())
    
    # Only SingleRecordFields that are indexed need normalization
    indexed_single_fields = single_record_fields & indexed_fields
    indexed_non_single_fields = indexed_fields - single_record_fields
    
    # Generate normalization function for all SingleRecordFields (not just indexed)
    # This ensures data shape is consistent in cache
    normalize_fn = make_auto_normalize(single_record_fields)
    
    # Generate Airtable mappings
    airtable_mapping = make_auto_airtable_mapping(
        indexed_single_fields,
        indexed_non_single_fields,
        custom_airtable_mappings
    )
    
    return {
        "indexed_fields": indexed_fields,
        "sortable_fields": sortable_fields,
        "normalize_fn": normalize_fn,
        "index_to_airtable": airtable_mapping if airtable_mapping else None,
    }
