from fastapi import APIRouter, Depends, HTTPException, status
from typing import List
from models.schemas import CategoryResponse, CreateCategoryRequest, UserResponse
from dependencies import get_current_user, get_current_admin
from database import get_db

router = APIRouter(prefix="/categories", tags=["categories"])


@router.get("/", response_model=List[CategoryResponse])
async def get_categories(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get all categories (accessible to both admin and staff)
    """
    try:
        db = get_db()
        categories_data = await db.categories.find_many(
            order={"category_name": "asc"}
        )
        
        categories = []
        for cat in categories_data:
            categories.append(CategoryResponse(
                category_id=cat.category_id,
                category_name=cat.category_name,
                created_at=cat.created_at
            ))
        
        return categories
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch categories: {str(e)}"
        )


@router.post("/", response_model=CategoryResponse, status_code=status.HTTP_201_CREATED)
async def create_category(
    category: CreateCategoryRequest,
    current_user: UserResponse = Depends(get_current_admin)
):
    """
    Create a new category (admin only)
    """
    try:
        db = get_db()
        created_category = await db.categories.create(
            data={"category_name": category.name}
        )
        
        if not created_category:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create category"
            )
        
        return CategoryResponse(
            category_id=created_category.category_id,
            category_name=created_category.category_name,
            created_at=created_category.created_at
        )
    except Exception as e:
        # Check for unique constraint violation
        if "duplicate key" in str(e).lower() or "unique constraint" in str(e).lower():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Category already exists"
            )
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create category: {str(e)}"
        )


@router.delete("/{category_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_category(
    category_id: int,
    current_user: UserResponse = Depends(get_current_admin)
):
    """
    Delete a category (admin only)
    """
    try:
        db = get_db()
        deleted_category = await db.categories.delete(
            where={"category_id": category_id}
        )
        
        if not deleted_category:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Category not found"
            )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete category: {str(e)}"
        )
