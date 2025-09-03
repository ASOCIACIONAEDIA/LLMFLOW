from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.ext.asyncio import AsyncSession

from app.api import deps
from app.schemas.auth import UserLoginRequest, TokenResponse, TwoFactorCodeRequest, UserRegisterRequest
from app.services.auth_services import AuthService
from app.repositories.user_repo import UserRepository
from app.models import User
from app.services.user_service import UserService

router = APIRouter()
auth_service = AuthService()

@router.post("/login", response_model=TokenResponse)
async def login(
    user_in: UserLoginRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_db),
):
    user_repo = UserRepository(db)
    user_id, is_2fa_enabled = await auth_service.login_user(
        user_repo, user_in.email, user_in.password, user_in.remember_me
    )
    
    if is_2fa_enabled:
        await auth_service.send_2fa_code(user_repo, user_id, background_tasks)
        raise HTTPException(
            status_code=status.HTTP_202_ACCEPTED,
            detail={"message": "2FA required", "user_id": user_id},
        )
        
    # If 2FA is not enabled, issue token directly
    access_token = await auth_service.issue_token(user_repo, user_id)
    return TokenResponse(access_token=access_token)

@router.post("/verify-2fa", response_model=TokenResponse)
async def verify_2fa(
    tfa_in: TwoFactorCodeRequest,
    db: AsyncSession = Depends(deps.get_db)
) -> TokenResponse:
    user_repo = UserRepository(db)
    user = await user_repo.get_by_id(tfa_in.user_id)
    if not user:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="User not found")
    
    is_valid = await auth_service.verify_2fa_code(user.id, tfa_in.code)
    if not is_valid:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail="Invalid 2FA code")
    
    access_token = await auth_service.issue_token(user_repo, user.id)
    return TokenResponse(access_token=access_token)

@router.post("/register", status_code=status.HTTP_201_CREATED)
async def register_user(
    user_in: UserRegisterRequest,
    background_tasks: BackgroundTasks,
    db: AsyncSession = Depends(deps.get_db),
):
    user_repo = UserRepository(db)
    # Create UserService with the user_repo
    user_service = UserService(user_repo)
    
    new_user = await user_service.create_user(
        user_repo=user_repo,
        name=user_in.name,
        email=user_in.email,
        password=user_in.password,
        send_verification=True,
        background_tasks=background_tasks
    )
    return {"message": "User registered successfully. Please check your email to verify your account."}
