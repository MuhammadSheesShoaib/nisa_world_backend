from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from models.schemas import (
    AdminLoginRequest,
    StaffLoginRequest,
    StaffSignupRequest,
    ChangePasswordRequest,
    CreateUserRequest,
    TokenResponse,
    UserResponse,
    MessageResponse
)
from services.auth_service import auth_service
from dependencies import get_current_user, get_current_admin

security = HTTPBearer()

router = APIRouter(prefix="/auth", tags=["Authentication"])


@router.post("/admin/login", response_model=TokenResponse)
async def admin_login(request: AdminLoginRequest):
    """
    Admin login endpoint
    """
    auth_data, user = await auth_service.admin_login(
        email=request.email,
        password=request.password
    )
    
    return TokenResponse(
        access_token=auth_data["access_token"],
        token_type="bearer",
        user=user
    )


@router.post("/staff/login", response_model=TokenResponse)
async def staff_login(request: StaffLoginRequest):
    """
    Staff login endpoint
    """
    auth_data, user = await auth_service.staff_login(
        email=request.email,
        password=request.password
    )
    
    return TokenResponse(
        access_token=auth_data["access_token"],
        token_type="bearer",
        user=user
    )


@router.post("/staff/signup", response_model=TokenResponse)
async def staff_signup(request: StaffSignupRequest):
    """
    Staff signup endpoint
    """
    auth_data, user = await auth_service.staff_signup(
        name=request.name,
        email=request.email,
        password=request.password
    )
    
    # If email confirmation is required, auth_data might be empty
    if not auth_data:
        raise HTTPException(
            status_code=status.HTTP_201_CREATED,
            detail="User created. Please check your email for confirmation."
        )
    
    return TokenResponse(
        access_token=auth_data.get("access_token", ""),
        token_type="bearer",
        user=user
    )


@router.post("/logout", response_model=MessageResponse)
async def logout(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Logout endpoint
    """
    # Note: For JWT tokens, logout is typically handled client-side
    # by removing the token. This endpoint can be used for server-side
    # token blacklisting if needed.
    await auth_service.logout(current_user.id)
    return MessageResponse(message="Logged out successfully")


@router.get("/me", response_model=UserResponse)
async def get_me(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get current authenticated user
    """
    return current_user


@router.post("/change-password", response_model=MessageResponse)
async def change_password(
    request: ChangePasswordRequest,
    credentials: HTTPAuthorizationCredentials = Depends(security),
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Change user password
    """
    token = credentials.credentials
    await auth_service.change_password(
        token=token,
        current_password=request.current_password,
        new_password=request.new_password
    )
    return MessageResponse(message="Password changed successfully")


@router.post("/create-user", response_model=UserResponse)
async def create_user(
    request: CreateUserRequest,
    current_admin: UserResponse = Depends(get_current_admin)
):
    """
    Create a new user (admin or staff) - Admin only
    """
    user = await auth_service.create_user(
        name=request.name,
        email=request.email,
        password=request.password,
        role=request.role
    )
    return user

