"""
Consultation Template API Routes
"""
import logging
from fastapi import APIRouter, HTTPException, Depends, status
from typing import List, Dict, Any

from .schemas import (
    ConsultationTemplate, CreateTemplateRequest, UpdateTemplateRequest,
    TemplateListResponse, TemplateSettings
)
from .service import TemplateService
from ..deps import get_template_service, get_admin_user_id

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/consultation-templates", tags=["templates"])


@router.get("/", response_model=TemplateListResponse)
async def get_templates(
    admin_user_id: str = Depends(get_admin_user_id),
    template_service: TemplateService = Depends(get_template_service)
):
    """Get all consultation templates for the user"""
    try:
        templates = await template_service.get_templates(admin_user_id)
        active_template = await template_service.get_active_template(admin_user_id)
        active_template_id = active_template["id"] if active_template else None

        return TemplateListResponse(
            templates=templates,
            active_template_id=active_template_id
        )

    except Exception as e:
        logger.error(f"Failed to get templates: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get templates: {str(e)}"
        )


@router.get("/{template_id}", response_model=ConsultationTemplate)
async def get_template(
    template_id: str,
    admin_user_id: str = Depends(get_admin_user_id),
    template_service: TemplateService = Depends(get_template_service)
):
    """Get specific consultation template"""
    try:
        template = await template_service.get_template(template_id, admin_user_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )

        return ConsultationTemplate(**template)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get template: {str(e)}"
        )


@router.post("/", response_model=ConsultationTemplate)
async def create_template(
    request: CreateTemplateRequest,
    admin_user_id: str = Depends(get_admin_user_id),
    template_service: TemplateService = Depends(get_template_service)
):
    """Create new consultation template"""
    try:
        result = await template_service.create_template(
            admin_user_id,
            request.dict()
        )

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )

        return ConsultationTemplate(**result["template"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to create template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create template: {str(e)}"
        )


@router.put("/{template_id}", response_model=ConsultationTemplate)
async def update_template(
    template_id: str,
    request: UpdateTemplateRequest,
    admin_user_id: str = Depends(get_admin_user_id),
    template_service: TemplateService = Depends(get_template_service)
):
    """Update consultation template"""
    try:
        # Get the current template first
        current = await template_service.get_template(template_id, admin_user_id)
        if not current:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )

        # Update with only provided fields
        updates = {k: v for k, v in request.dict().items() if v is not None}

        success = await template_service.update_template(template_id, admin_user_id, updates)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update template"
            )

        # Return updated template
        updated = await template_service.get_template(template_id, admin_user_id)
        return ConsultationTemplate(**updated)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to update template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update template: {str(e)}"
        )


@router.delete("/{template_id}")
async def delete_template(
    template_id: str,
    admin_user_id: str = Depends(get_admin_user_id),
    template_service: TemplateService = Depends(get_template_service)
):
    """Delete consultation template"""
    try:
        # Check if template exists
        template = await template_service.get_template(template_id, admin_user_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )

        # Don't allow deleting the last template
        templates = await template_service.get_templates(admin_user_id)
        if len(templates) <= 1:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Cannot delete the last template"
            )

        success = await template_service.delete_template(template_id, admin_user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to delete template"
            )

        return {"message": "Template deleted successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to delete template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete template: {str(e)}"
        )


@router.post("/{template_id}/activate")
async def activate_template(
    template_id: str,
    admin_user_id: str = Depends(get_admin_user_id),
    template_service: TemplateService = Depends(get_template_service)
):
    """Set template as active"""
    try:
        # Check if template exists
        template = await template_service.get_template(template_id, admin_user_id)
        if not template:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Template not found"
            )

        success = await template_service.set_active_template(template_id, admin_user_id)
        if not success:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to activate template"
            )

        return {"message": "Template activated successfully"}

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to activate template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to activate template: {str(e)}"
        )


@router.post("/{template_id}/duplicate", response_model=ConsultationTemplate)
async def duplicate_template(
    template_id: str,
    new_name: str,
    admin_user_id: str = Depends(get_admin_user_id),
    template_service: TemplateService = Depends(get_template_service)
):
    """Duplicate an existing template"""
    try:
        result = await template_service.duplicate_template(template_id, admin_user_id, new_name)

        if not result["success"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=result["error"]
            )

        return ConsultationTemplate(**result["template"])

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to duplicate template {template_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to duplicate template: {str(e)}"
        )


@router.get("/active/current", response_model=ConsultationTemplate)
async def get_active_template(
    admin_user_id: str = Depends(get_admin_user_id),
    template_service: TemplateService = Depends(get_template_service)
):
    """Get the currently active template"""
    try:
        template = await template_service.get_active_template(admin_user_id)
        if not template:
            # Ensure user has a default template
            result = await template_service.ensure_default_template(admin_user_id)
            if result["success"] and "template" in result:
                template = result["template"]
            else:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail="No active template found"
                )

        return ConsultationTemplate(**template)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Failed to get active template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active template: {str(e)}"
        )


@router.get("/default/settings", response_model=TemplateSettings)
async def get_default_settings(
    admin_user_id: str = Depends(get_admin_user_id),
    template_service: TemplateService = Depends(get_template_service)
):
    """Get default settings for creating new templates"""
    try:
        settings = await template_service.get_default_settings(admin_user_id)
        return TemplateSettings(**settings)

    except Exception as e:
        logger.error(f"Failed to get default settings: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get default settings: {str(e)}"
        )


@router.post("/ensure-default")
async def ensure_default_template(
    admin_user_id: str = Depends(get_admin_user_id),
    template_service: TemplateService = Depends(get_template_service)
):
    """Ensure user has a default template (for migration/setup)"""
    try:
        result = await template_service.ensure_default_template(admin_user_id)
        return result

    except Exception as e:
        logger.error(f"Failed to ensure default template: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to ensure default template: {str(e)}"
        )