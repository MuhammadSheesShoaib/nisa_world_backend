from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from models.schemas import UserResponse, UserResponseWithPassword, UserPasswordUpdate
from dependencies import get_current_admin
from database import get_db

router = APIRouter(prefix="/users", tags=["Users"])


@router.get("/", response_model=List[UserResponseWithPassword])
async def get_all_users(
    current_admin: UserResponse = Depends(get_current_admin)
):
    """
    Get all users (Admin only)
    Returns all admin and staff users with their details including passwords
    """
    try:
        db = get_db()
        users_data = await db.users.find_many(
            order={"created_at": "desc"}
        )
        
        users = []
        for user in users_data:
            role = "admin" if user.role_id == 1 else "staff"
            users.append(UserResponseWithPassword(
                id=str(user.id),
                name=user.name,
                email=user.email,
                password=user.password,  # Include password for admin viewing
                role=role,
                created_at=user.created_at
            ))
        
        return users
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch users: {str(e)}"
        )


@router.get("/{user_id}", response_model=UserResponse)
async def get_user(
    user_id: int,
    current_admin: UserResponse = Depends(get_current_admin)
):
    """
    Get a specific user by ID (Admin only)
    """
    try:
        db = get_db()
        user = await db.users.find_unique(
            where={"id": user_id}
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        role = "admin" if user.role_id == 1 else "staff"
        return UserResponse(
            id=str(user.id),
            name=user.name,
            email=user.email,
            role=role,
            created_at=user.created_at
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch user: {str(e)}"
        )


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(
    user_id: int,
    current_admin: UserResponse = Depends(get_current_admin)
):
    """
    Delete a user (Admin only)
    Cannot delete yourself
    """
    try:
        # Prevent admin from deleting themselves
        if int(current_admin.id) == user_id:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="You cannot delete your own account"
            )
        
        db = get_db()
        
        # Check if user exists
        user = await db.users.find_unique(
            where={"id": user_id}
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Delete the user
        await db.users.delete(
            where={"id": user_id}
        )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete user: {str(e)}"
        )


@router.put("/{user_id}/password", status_code=status.HTTP_200_OK)
async def update_user_password(
    user_id: int,
    password_data: UserPasswordUpdate,
    current_admin: UserResponse = Depends(get_current_admin)
):
    """
    Update a user's password (Admin only)
    """
    try:
        db = get_db()
        
        # Check if user exists
        user = await db.users.find_unique(
            where={"id": user_id}
        )
        
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found"
            )
        
        # Update the password (plain text)
        await db.users.update(
            where={"id": user_id},
            data={"password": password_data.password}
        )
        
        return {"message": "Password updated successfully"}
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update password: {str(e)}"
        )

