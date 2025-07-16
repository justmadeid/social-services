from typing import Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from sqlalchemy.exc import NoResultFound
from datetime import datetime

from app.crud.base import CRUDBase
from app.db.models import TwitterCredentials
from app.schemas.settings import CredentialCreate, CredentialUpdate
from app.core.security import security_manager


class CRUDCredentials(CRUDBase[TwitterCredentials, CredentialCreate, CredentialUpdate]):
    async def get_by_name(
        self, db: AsyncSession, *, credential_name: str
    ) -> Optional[TwitterCredentials]:
        result = await db.execute(
            select(self.model).where(self.model.credential_name == credential_name)
        )
        return result.scalar_one_or_none()

    async def create_with_encryption(
        self, db: AsyncSession, *, obj_in: CredentialCreate
    ) -> TwitterCredentials:
        # Encrypt password
        encrypted_password, salt = security_manager.encrypt_password(obj_in.password)
        
        # Create credential object
        db_obj = TwitterCredentials(
            credential_name=obj_in.credential_name,
            username=obj_in.username,
            encrypted_password=encrypted_password,
            salt=salt,
        )
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def update_with_encryption(
        self,
        db: AsyncSession,
        *,
        db_obj: TwitterCredentials,
        obj_in: CredentialUpdate
    ) -> TwitterCredentials:
        update_data = obj_in.model_dump(exclude_unset=True)
        
        # If password is being updated, encrypt it
        if "password" in update_data:
            encrypted_password, salt = security_manager.encrypt_password(
                update_data["password"]
            )
            update_data["encrypted_password"] = encrypted_password
            update_data["salt"] = salt
            del update_data["password"]
        
        for field, value in update_data.items():
            setattr(db_obj, field, value)
        
        db.add(db_obj)
        await db.commit()
        await db.refresh(db_obj)
        return db_obj

    async def get_decrypted_password(
        self, db: AsyncSession, *, credential_name: str
    ) -> Optional[str]:
        credential = await self.get_by_name(db, credential_name=credential_name)
        if not credential:
            return None
        
        return security_manager.decrypt_password(
            credential.encrypted_password, credential.salt
        )

    async def update_login_attempt(
        self, 
        db: AsyncSession, 
        *, 
        credential_name: str, 
        success: bool = True
    ) -> Optional[TwitterCredentials]:
        credential = await self.get_by_name(db, credential_name=credential_name)
        if not credential:
            return None
        
        credential.last_login_attempt = datetime.utcnow()
        if success:
            credential.login_success_count += 1
        else:
            credential.login_failure_count += 1
        
        db.add(credential)
        await db.commit()
        await db.refresh(credential)
        return credential

    async def get_active_credentials(
        self, db: AsyncSession
    ) -> List[TwitterCredentials]:
        result = await db.execute(
            select(self.model).where(self.model.is_active == True)
        )
        return result.scalars().all()


credentials = CRUDCredentials(TwitterCredentials)
settings_crud = credentials  # Alias for backward compatibility
