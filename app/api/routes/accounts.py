from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update
from typing import List, Optional
import logging
from datetime import datetime

from app.database.db_session import async_session_factory
from app.database.models import Account, AccountStatus
from app.api.schemas.account import (
    AccountCreate,
    AccountUpdate,
    AccountResponse,
    AccountHealthResponse
)
from app.utils.security import encrypt_credentials, decrypt_credentials
from app.utils.session_manager import check_account_health

router = APIRouter()
logger = logging.getLogger(__name__)

# Get database session dependency
async def get_db():
    db = async_session_factory()
    try:
        yield db
    finally:
        await db.close()

@router.get("/", response_model=List[AccountResponse])
async def get_accounts(
    status: Optional[str] = None,
    active_only: bool = False,
    db: AsyncSession = Depends(get_db)
):
    """
    Get all accounts with optional filtering
    """
    query = select(Account)
    
    if status:
        try:
            account_status = AccountStatus(status)
            query = query.where(Account.status == account_status)
        except ValueError:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid account status: {status}"
            )
    
    if active_only:
        query = query.where(Account.is_active == True)
    
    result = await db.execute(query)
    accounts = result.scalars().all()
    
    # Mask sensitive fields
    for account in accounts:
        account.api_hash = "***masked***"
    
    return accounts

@router.post("/", response_model=AccountResponse, status_code=status.HTTP_201_CREATED)
async def create_account(
    account_data: AccountCreate,
    db: AsyncSession = Depends(get_db)
):
    """
    Create a new account
    """
    try:
        # Check if account with this phone already exists
        query = select(Account).where(Account.phone == account_data.phone)
        result = await db.execute(query)
        existing_account = result.scalar_one_or_none()
        
        if existing_account:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Account with phone {account_data.phone} already exists"
            )
        
        # Encrypt sensitive data
        api_hash_encrypted = encrypt_credentials(account_data.api_hash)
        
        # Create new account
        new_account = Account(
            user_id=account_data.user_id,
            phone=account_data.phone,
            api_id=account_data.api_id,
            api_hash=api_hash_encrypted,
            is_active=True,
            status=AccountStatus.ACTIVE,
            reset_counts_at=datetime.utcnow()
        )
        
        db.add(new_account)
        await db.commit()
        await db.refresh(new_account)
        
        # Mask sensitive data in response
        new_account.api_hash = "***masked***"
        return new_account
        
    except Exception as e:
        await db.rollback()
        logger.error(f"Error creating account: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error creating account: {str(e)}"
        )

@router.get("/{account_id}", response_model=AccountResponse)
async def get_account(
    account_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Get account details by ID
    """
    try:
        query = select(Account).where(Account.id == account_id)
        result = await db.execute(query)
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account with ID {account_id} not found"
            )
        
        # Mask sensitive data
        account.api_hash = "***masked***"
        return account
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error retrieving account {account_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error retrieving account: {str(e)}"
        )

@router.put("/{account_id}", response_model=AccountResponse)
async def update_account(
    account_id: int,
    account_data: AccountUpdate,
    db: AsyncSession = Depends(get_db)
):
    """
    Update an account
    """
    try:
        # Check if account exists
        query = select(Account).where(Account.id == account_id)
        result = await db.execute(query)
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account with ID {account_id} not found"
            )
        
        # Update account fields
        update_data = account_data.dict(exclude_unset=True)
        
        # If updating API hash, encrypt it
        if "api_hash" in update_data:
            update_data["api_hash"] = encrypt_credentials(update_data["api_hash"])
            
        # If updating status, validate it
        if "status" in update_data:
            try:
                update_data["status"] = AccountStatus(update_data["status"])
            except ValueError:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid account status: {update_data['status']}"
                )
        
        # Apply updates
        for key, value in update_data.items():
            setattr(account, key, value)
        
        await db.commit()
        await db.refresh(account)
        
        # Mask sensitive data
        account.api_hash = "***masked***"
        return account
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error updating account {account_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error updating account: {str(e)}"
        )

@router.delete("/{account_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_account(
    account_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Delete an account
    """
    try:
        # Check if account exists
        query = select(Account).where(Account.id == account_id)
        result = await db.execute(query)
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account with ID {account_id} not found"
            )
        
        # Delete account
        await db.delete(account)
        await db.commit()
        
        return None
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error deleting account {account_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error deleting account: {str(e)}"
        )

@router.post("/{account_id}/check", response_model=AccountHealthResponse)
async def check_account(
    account_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Check account health and status
    """
    try:
        # Get account
        query = select(Account).where(Account.id == account_id)
        result = await db.execute(query)
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account with ID {account_id} not found"
            )
        
        # Check account health
        health_status = await check_account_health(account)
        
        # Update account status based on health check
        account.status = health_status["status"]
        await db.commit()
        
        return health_status
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error checking account {account_id}: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error checking account health: {str(e)}"
        )

@router.post("/{account_id}/reset", response_model=AccountResponse)
async def reset_account_limits(
    account_id: int,
    db: AsyncSession = Depends(get_db)
):
    """
    Reset account usage limits
    """
    try:
        # Get account
        query = select(Account).where(Account.id == account_id)
        result = await db.execute(query)
        account = result.scalar_one_or_none()
        
        if not account:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Account with ID {account_id} not found"
            )
        
        # Reset limits
        account.daily_parse_count = 0
        account.daily_invite_count = 0
        account.daily_like_count = 0
        account.reset_counts_at = datetime.utcnow()
        
        # If in cooldown and cooldown is due to limits, remove it
        if account.status == AccountStatus.COOLING_DOWN:
            account.status = AccountStatus.ACTIVE
            account.cooldown_until = None
        
        await db.commit()
        await db.refresh(account)
        
        # Mask sensitive data
        account.api_hash = "***masked***"
        return account
        
    except HTTPException:
        raise
    except Exception as e:
        await db.rollback()
        logger.error(f"Error resetting account {account_id} limits: {e}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Error resetting account limits: {str(e)}"
        )