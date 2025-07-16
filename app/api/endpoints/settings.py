from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from typing import List

from app.api.dependencies import rate_limit
from app.crud.crud_settings import settings_crud
from app.db.session import get_async_session
from app.schemas.settings import SettingsCreate, SettingsResponse, SettingsUpdate
from app.schemas.common import StandardResponse

router = APIRouter()


@router.post(
    "",
    response_model=StandardResponse[SettingsResponse],
    status_code=status.HTTP_201_CREATED,
    summary="Save Twitter credentials",
    description="Save or update Twitter credentials in the database with encryption"
)
async def create_settings(
    settings_in: SettingsCreate,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(rate_limit)
):
    """Save Twitter credentials to database."""
    try:
        # Check if credential name already exists
        existing = await settings_crud.get_by_name(db, credential_name=settings_in.credential_name)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Credential with name '{settings_in.credential_name}' already exists"
            )
        
        # Create new credentials
        settings_obj = await settings_crud.create_with_encryption(db, obj_in=settings_in)
        
        return StandardResponse(
            status="success",
            message="Credentials saved successfully",
            data=SettingsResponse.model_validate(settings_obj)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to save credentials: {str(e)}"
        )


@router.get(
    "",
    response_model=StandardResponse[List[SettingsResponse]],
    summary="List saved credentials",
    description="Get all saved Twitter credentials (passwords excluded)"
)
async def get_settings(
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(rate_limit)
):
    """Get all saved credentials without passwords."""
    try:
        settings_list = await settings_crud.get_multi(db)
        return StandardResponse(
            status="success",
            data=[SettingsResponse.model_validate(settings) for settings in settings_list]
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve credentials: {str(e)}"
        )


@router.put(
    "/{credential_name}",
    response_model=StandardResponse[SettingsResponse],
    summary="Update Twitter credentials",
    description="Update existing Twitter credentials"
)
async def update_settings(
    credential_name: str,
    settings_update: SettingsUpdate,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(rate_limit)
):
    """Update existing credentials."""
    try:
        settings_obj = await settings_crud.get_by_name(db, credential_name=credential_name)
        if not settings_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Credential '{credential_name}' not found"
            )
        
        updated_settings = await settings_crud.update_with_encryption(db, db_obj=settings_obj, obj_in=settings_update)
        
        return StandardResponse(
            status="success",
            message="Credentials updated successfully",
            data=SettingsResponse.model_validate(updated_settings)
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update credentials: {str(e)}"
        )


@router.delete(
    "/{credential_name}",
    response_model=StandardResponse[dict],
    summary="Delete Twitter credentials",
    description="Delete Twitter credentials by credential name"
)
async def delete_settings(
    credential_name: str,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(rate_limit)
):
    """Delete credentials."""
    try:
        settings_obj = await settings_crud.get_by_name(db, credential_name=credential_name)
        if not settings_obj:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Credential '{credential_name}' not found"
            )
        
        await settings_crud.remove(db, id=settings_obj.id)
        
        return StandardResponse(
            status="success",
            message=f"Credential '{credential_name}' deleted successfully",
            data={"credential_name": credential_name}
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete credentials: {str(e)}"
        )
