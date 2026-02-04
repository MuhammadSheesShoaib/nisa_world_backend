from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import List
from models.schemas import (
    InventoryCreate,
    InventoryUpdate,
    InventoryResponse,
    BulkInventoryCreate,
    InventoryItem,
    RawMaterialCreate,
    RawMaterialResponse,
    UserResponse
)
from dependencies import get_current_user
from database import get_db
from services.export_service import export_service
import traceback

router = APIRouter(prefix="/inventory", tags=["Inventory"])


@router.post("/products", response_model=InventoryResponse)
async def create_inventory_product(
    product: InventoryCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Create a new inventory product (Admin and Staff can add)
    """
    try:
        db = get_db()
        created_product = await db.inventory.create(
            data={
                "product_name": product.product_name,
                "category": product.category,
                "cost_price": product.cost_price,
                "quantity": product.quantity,
                "added_by": str(current_user.id)
            }
        )
        
        if not created_product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create inventory product"
            )
        
        return InventoryResponse(
            id=created_product.id,
            invoice_no=created_product.invoice_no,
            product_name=created_product.product_name,
            category=created_product.category,
            cost_price=float(created_product.cost_price),
            sale_price=float(product.sale_price) if product.sale_price > 0 else float(created_product.cost_price) * 1.5,
            quantity=created_product.quantity,
            added_by=created_product.added_by,
            added_by_name=current_user.name,
            added_by_role=current_user.role,
            edited=created_product.edited if created_product.edited is not None else False,
            created_at=str(created_product.created_at) if created_product.created_at else None
        )
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create inventory product: {str(e)}"
        )


@router.post("/products/bulk", response_model=List[InventoryResponse])
async def create_bulk_inventory(
    inventory_data: BulkInventoryCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Create inventory with multiple items (bulk inventory)
    - Generates ONE invoice_no for all items
    - Creates multiple inventory rows with same invoice_no
    """
    try:
        db = get_db()
        
        if not inventory_data.items or len(inventory_data.items) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one inventory item is required"
            )
        
        # Generate ONE invoice_no for all items
        try:
            invoice_result = await db.query_raw("SELECT nextval('invoice_seq') as next_val")
            if invoice_result and len(invoice_result) > 0:
                if isinstance(invoice_result[0], dict):
                    next_val = invoice_result[0].get('next_val', 1)
                else:
                    next_val = getattr(invoice_result[0], 'next_val', 1)
            else:
                next_val = 1
        except Exception as e:
            print(f"Error getting invoice sequence: {e}")
            import time
            next_val = int(time.time()) % 1000000
        invoice_no = f"INV-{str(next_val).zfill(6)}"
        
        created_items = []
        
        # Process each item
        for item in inventory_data.items:
            # Create inventory item
            created_item = await db.inventory.create(
                data={
                    "invoice_no": invoice_no,
                    "product_name": item.product_name,
                    "category": item.category,
                    "cost_price": item.cost_price,
                    "quantity": item.quantity,
                    "added_by": str(current_user.id),
                }
            )
            
            if not created_item:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create inventory item for one of the products"
                )
            
            # Calculate sale_price (default to 1.5x cost_price if not provided)
            sale_price = item.sale_price if item.sale_price and item.sale_price > 0 else float(created_item.cost_price) * 1.5
            
            created_items.append(InventoryResponse(
                id=created_item.id,
                invoice_no=created_item.invoice_no,
                product_name=created_item.product_name,
                category=created_item.category,
                cost_price=float(created_item.cost_price),
                sale_price=sale_price,
                quantity=created_item.quantity,
                added_by=created_item.added_by,
                added_by_name=current_user.name,
                edited=False,
                created_at=str(created_item.created_at) if created_item.created_at else None
            ))
        
        return created_items
    except HTTPException:
        raise
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"❌ Bulk Inventory Error: {str(e)}")
        print(f"Full trace:\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create bulk inventory: {str(e)}"
        )


@router.post("/products/invoice/{invoice_no}/items", response_model=List[InventoryResponse])
async def add_inventory_items_to_invoice(
    invoice_no: str,
    inventory_data: BulkInventoryCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Append inventory items to an existing invoice_no
    - Does NOT generate a new invoice_no
    - Creates new inventory rows with the provided invoice_no
    """
    try:
        db = get_db()

        if not inventory_data.items or len(inventory_data.items) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one inventory item is required"
            )

        created_items: List[InventoryResponse] = []

        for item in inventory_data.items:
            created_item = await db.inventory.create(
                data={
                    "invoice_no": invoice_no,
                    "product_name": item.product_name,
                    "category": item.category,
                    "cost_price": item.cost_price,
                    "quantity": item.quantity,
                    "added_by": str(current_user.id),
                    "edited": True,
                }
            )

            if not created_item:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to add inventory item"
                )

            sale_price = item.sale_price if item.sale_price and item.sale_price > 0 else float(created_item.cost_price) * 1.5

            created_items.append(InventoryResponse(
                id=created_item.id,
                invoice_no=created_item.invoice_no,
                product_name=created_item.product_name,
                category=created_item.category,
                cost_price=float(created_item.cost_price),
                sale_price=sale_price,
                quantity=created_item.quantity,
                added_by=created_item.added_by,
                added_by_name=current_user.name,
                added_by_role=current_user.role,
                edited=True,
                created_at=str(created_item.created_at) if created_item.created_at else None
            ))

        return created_items
    except HTTPException:
        raise
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"❌ Add Inventory Items Error: {str(e)}")
        print(f"Full trace:\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add inventory items: {str(e)}"
        )


@router.get("/products", response_model=List[InventoryResponse])
async def get_inventory_products(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get inventory products
    - All users (admin and staff) see all products - inventory is shared
    """
    try:
        db = get_db()
        
        products_data = await db.inventory.find_many(
            order={"created_at": "desc"}
        )
        
        # Get all unique user IDs to fetch user names and roles
        user_ids = list(set([item.added_by for item in products_data if item.added_by]))
        
        # Fetch user info for all users
        user_map = {}
        if user_ids:
            try:
                # Convert string IDs to integers, skip non-numeric ones
                int_user_ids = []
                for uid in user_ids:
                    if uid and uid.isdigit():
                        int_user_ids.append(int(uid))
                
                if int_user_ids:
                    users_data = await db.users.find_many(
                        where={"id": {"in": int_user_ids}}
                    )
                    for user in users_data:
                        user_map[str(user.id)] = {
                            "name": user.name,
                            "role": "admin" if user.role_id == 1 else "staff"
                        }
            except Exception as e:
                print(f"Error fetching users: {e}")
                # Continue without user names
        
        products = []
        for item in products_data:
            # Get user name and role
            user_info = user_map.get(item.added_by, {"name": "Unknown", "role": "staff"})
            user_name = user_info.get("name", "Unknown")
            user_role = user_info.get("role", "staff")
            
            products.append(InventoryResponse(
                id=item.id,
                invoice_no=item.invoice_no,
                product_name=item.product_name,
                category=item.category,
                cost_price=float(item.cost_price),
                sale_price=float(item.cost_price) * 1.5,  # Calculate 50% markup
                quantity=item.quantity,
                added_by=item.added_by,
                added_by_name=user_name,
                added_by_role=user_role,
                edited=item.edited if item.edited is not None else False,
                created_at=str(item.created_at) if item.created_at else None
            ))
        
        return products
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch inventory products: {str(e)}"
        )


@router.put("/products/{product_id}", response_model=InventoryResponse)
async def update_inventory_product(
    product_id: int,
    product: InventoryUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Update an inventory product
    - All users can update any product (inventory is shared)
    """
    try:
        db = get_db()
        
        # Get existing product
        existing_product = await db.inventory.find_unique(
            where={"id": product_id}
        )
        
        if not existing_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Build update data (only include fields that were provided)
        update_data = {"edited": True}
        if product.product_name is not None:
            update_data["product_name"] = product.product_name
        if product.category is not None:
            update_data["category"] = product.category
        if product.cost_price is not None:
            update_data["cost_price"] = product.cost_price
        if product.quantity is not None:
            update_data["quantity"] = product.quantity
        
        # Update product
        updated_product = await db.inventory.update(
            where={"id": product_id},
            data=update_data
        )
        
        if not updated_product:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update product"
            )
        
        return InventoryResponse(
            id=updated_product.id,
            invoice_no=updated_product.invoice_no,
            product_name=updated_product.product_name,
            category=updated_product.category,
            cost_price=float(updated_product.cost_price),
            sale_price=float(updated_product.cost_price) * 1.5,
            quantity=updated_product.quantity,
            added_by=updated_product.added_by,
            added_by_name=current_user.name,
            edited=updated_product.edited if updated_product.edited is not None else False,
            created_at=str(updated_product.created_at) if updated_product.created_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update inventory product: {str(e)}"
        )





@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_inventory_product(
    product_id: int,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Delete an inventory product
    - All users can delete any product (inventory is shared)
    """
    try:
        db = get_db()
        
        # Get existing product
        existing_product = await db.inventory.find_unique(
            where={"id": product_id}
        )
        
        if not existing_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Delete product
        deleted_product = await db.inventory.delete(
            where={"id": product_id}
        )
        
        if not deleted_product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete inventory product: {str(e)}"
        )


@router.get("/products/invoice/{invoice_no}", response_class=StreamingResponse)
async def generate_inventory_invoice_pdf(
    invoice_no: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Generate PDF invoice for a specific inventory invoice_no
    - All users can generate invoices for any inventory (inventory is shared)
    """
    try:
        db = get_db()
        
        # Fetch all inventory items related to this invoice_no
        inventory_data = await db.inventory.find_many(
            where={"invoice_no": invoice_no},
            order={"created_at": "asc"}
        )
        
        if not inventory_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found or you do not have permission to view it."
            )
        
        pdf_buffer = export_service.create_inventory_invoice_pdf(inventory_data, invoice_no)
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Inventory_Invoice_{invoice_no}.pdf"}
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Inventory Invoice Generation Error: {str(e)}")
        print(f"Full trace:\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate inventory invoice: {str(e)}"
        )


@router.post("/raw-materials", response_model=RawMaterialResponse)

async def create_raw_material(
    material: RawMaterialCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Create a new raw material (Admin and Staff can add)
    Note: This endpoint is kept for compatibility but raw_materials table doesn't exist in schema
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Raw materials functionality has been migrated to expenses"
    )


@router.get("/raw-materials", response_model=List[RawMaterialResponse])
async def get_raw_materials(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get raw materials
    Note: This endpoint is kept for compatibility but raw_materials table doesn't exist in schema
    """
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="Raw materials functionality has been migrated to expenses"
    )
