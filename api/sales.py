from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import List
from models.schemas import (
    SalesCreate,
    SalesUpdate,
    SalesResponse,
    BulkSalesCreate,
    SaleItem,
    UserResponse
)
from dependencies import get_current_user
from database import get_db
from services.export_service import export_service

router = APIRouter(prefix="/sales", tags=["Sales"])


@router.post("/", response_model=SalesResponse)
async def create_sale(
    sale: SalesCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Create a new sale (Admin and Staff can add)
    """
    try:
        db = get_db()
        
        # Get product details
        product = await db.inventory.find_unique(
            where={"id": sale.product_id}
        )
        
        if not product:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Product not found"
            )
        
        # Check if enough quantity available
        if product.quantity < sale.quantity:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Insufficient quantity. Available: {product.quantity}"
            )
        
        # Create sale
        created_sale = await db.sales.create(
            data={
                "customer_name": sale.customer_name,
                "customer_address": sale.customer_address,
                "customer_phone": sale.customer_phone,
                "product_name": product.product_name,
                "category": product.category,
                "quantity": sale.quantity,
                "cost_price": product.cost_price,
                "sale_price": sale.sale_price,
                "entry_date": sale.entry_date,
                "payment_type": str(sale.payment_type),
                "advance_amount": sale.advance_amount if sale.advance_amount else 0,
                "sold_by": str(current_user.id)
            }
        )
        
        if not created_sale:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create sale"
            )
        
        # Update inventory quantity
        new_quantity = product.quantity - sale.quantity
        await db.inventory.update(
            where={"id": sale.product_id},
            data={"quantity": new_quantity}
        )
        
        return SalesResponse(
            id=created_sale.id,
            invoice_no=created_sale.invoice_no,
            customer_name=created_sale.customer_name,
            customer_address=created_sale.customer_address or "",
            customer_phone=created_sale.customer_phone or "",
            product_id=sale.product_id,
            product_name=created_sale.product_name,
            category=created_sale.category,
            quantity=created_sale.quantity,
            cost_price=float(created_sale.cost_price),
            sale_price=float(created_sale.sale_price),
            payment_type=created_sale.payment_type,
            advance_amount=sale.advance_amount,
            sold_by=created_sale.sold_by,
            sold_by_name=current_user.name,
            sold_by_role=current_user.role,
            edited=created_sale.edited if created_sale.edited is not None else False,
            created_at=str(created_sale.created_at) if created_sale.created_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create sale: {str(e)}"
        )


@router.post("/bulk", response_model=List[SalesResponse])
async def create_bulk_sale(
    sale_data: BulkSalesCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Create a sale with multiple products (bulk sale)
    - Generates ONE invoice_no for all products
    - Creates multiple sale rows with same invoice_no
    - Updates inventory for each product
    """
    try:
        db = get_db()
        
        # Validate items
        if not sale_data.items or len(sale_data.items) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one product is required"
            )
        
        # Validate each item
        for item in sale_data.items:
            if not item.product_id or item.product_id <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid product_id: {item.product_id}"
                )
            if not item.quantity or item.quantity <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid quantity: {item.quantity}"
                )
            if not item.sale_price or item.sale_price <= 0:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Invalid sale_price: {item.sale_price}"
                )
        
        # Generate ONE invoice_no for all items
        try:
            invoice_result = await db.query_raw("SELECT nextval('invoice_seq') as next_val")
            # Handle different return formats
            if invoice_result and len(invoice_result) > 0:
                if isinstance(invoice_result[0], dict):
                    next_val = invoice_result[0].get('next_val', 1)
                else:
                    next_val = getattr(invoice_result[0], 'next_val', 1)
            else:
                next_val = 1
        except Exception as e:
            print(f"Error getting invoice sequence: {e}")
            # Fallback: use timestamp-based invoice number
            import time
            next_val = int(time.time()) % 1000000
        invoice_no = f"INV-{str(next_val).zfill(6)}"
        
        created_sales = []
        
        # Process each item
        for item in sale_data.items:
            # Get product details
            product = await db.inventory.find_unique(
                where={"id": item.product_id}
            )
            
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with ID {item.product_id} not found"
                )
            
            # Check if enough quantity available
            if product.quantity < item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient quantity for {product.product_name}. Available: {product.quantity}, Requested: {item.quantity}"
                )
            
            # Create sale with the same invoice_no
            created_sale = await db.sales.create(
                data={
                    "invoice_no": invoice_no,
                    "customer_name": sale_data.customer_name,
                    "customer_address": sale_data.customer_address,
                    "customer_phone": sale_data.customer_phone,
                    "product_name": product.product_name,
                    "category": product.category,
                    "quantity": item.quantity,
                    "cost_price": product.cost_price,
                    "sale_price": item.sale_price,
                    "entry_date": sale_data.entry_date,
                    "payment_type": str(sale_data.payment_type),
                    "advance_amount": sale_data.advance_amount if sale_data.advance_amount else 0,
                    "sold_by": str(current_user.id)
                }
            )
            
            # Update inventory quantity
            new_quantity = product.quantity - item.quantity
            await db.inventory.update(
                where={"id": item.product_id},
                data={"quantity": new_quantity}
            )
            
            created_sales.append(created_sale)
        
        # Return all created sales
        response_sales = []
        for sale in created_sales:
            # Get product_id from the first item (for backward compatibility)
            product_id = sale_data.items[0].product_id if sale_data.items else None
            response_sales.append(SalesResponse(
                id=sale.id,
                invoice_no=sale.invoice_no,
                customer_name=sale.customer_name,
                customer_address=sale.customer_address or "",
                customer_phone=sale.customer_phone or "",
                product_id=product_id,
                product_name=sale.product_name,
                category=sale.category,
                quantity=sale.quantity,
                cost_price=float(sale.cost_price),
                sale_price=float(sale.sale_price),
                payment_type=sale.payment_type,
                advance_amount=float(sale.advance_amount) if sale.advance_amount else 0,
                sold_by=sale.sold_by,
                sold_by_name=current_user.name,
                sold_by_role=current_user.role,
                edited=sale.edited if sale.edited is not None else False,
                created_at=str(sale.created_at) if sale.created_at else None
            ))
        
        return response_sales
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Bulk Sale Error: {str(e)}")
        print(f"Full trace:\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create bulk sale: {str(e)}"
        )


@router.post("/invoice/{invoice_no}/items", response_model=List[SalesResponse])
async def add_sale_items_to_invoice(
    invoice_no: str,
    sale_data: BulkSalesCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Append sale items to an existing invoice_no
    - Does NOT generate a new invoice_no
    - Creates new sale rows with the provided invoice_no
    - Updates inventory for each new item
    """
    try:
        db = get_db()

        if not sale_data.items or len(sale_data.items) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one product is required"
            )

        # Permission: staff can only append to their own invoice
        if current_user.role == "staff":
            existing = await db.sales.find_first(
                where={"invoice_no": invoice_no, "sold_by": str(current_user.id)}
            )
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to add items to this invoice"
                )

        created_sales: List[SalesResponse] = []

        # Normalize advance for full payment
        final_advance = sale_data.advance_amount if str(sale_data.payment_type) != "1" else 0

        for item in sale_data.items:
            product = await db.inventory.find_unique(where={"id": item.product_id})
            if not product:
                raise HTTPException(
                    status_code=status.HTTP_404_NOT_FOUND,
                    detail=f"Product with ID {item.product_id} not found"
                )

            if product.quantity < item.quantity:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=f"Insufficient quantity for {product.product_name}. Available: {product.quantity}, Requested: {item.quantity}"
                )

            created_sale = await db.sales.create(
                data={
                    "invoice_no": invoice_no,
                    "customer_name": sale_data.customer_name,
                    "customer_address": sale_data.customer_address,
                    "customer_phone": sale_data.customer_phone,
                    "product_name": product.product_name,
                    "category": product.category,
                    "quantity": item.quantity,
                    "cost_price": product.cost_price,
                    "sale_price": item.sale_price,
                    "entry_date": sale_data.entry_date,
                    "payment_type": str(sale_data.payment_type),
                    "advance_amount": final_advance if final_advance else 0,
                    "sold_by": str(current_user.id),
                    "edited": True,
                }
            )

            # Update inventory quantity
            await db.inventory.update(
                where={"id": item.product_id},
                data={"quantity": product.quantity - item.quantity}
            )

            created_sales.append(SalesResponse(
                id=created_sale.id,
                invoice_no=created_sale.invoice_no,
                customer_name=created_sale.customer_name,
                customer_address=created_sale.customer_address or "",
                customer_phone=created_sale.customer_phone or "",
                product_id=item.product_id,
                product_name=created_sale.product_name,
                category=created_sale.category,
                quantity=created_sale.quantity,
                cost_price=float(created_sale.cost_price),
                sale_price=float(created_sale.sale_price),
                payment_type=created_sale.payment_type,
                advance_amount=float(created_sale.advance_amount) if created_sale.advance_amount is not None else 0,
                sold_by=created_sale.sold_by,
                sold_by_name=current_user.name,
                sold_by_role=current_user.role,
                edited=True,
                created_at=str(created_sale.created_at) if created_sale.created_at else None
            ))

        return created_sales
    except HTTPException:
        raise
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"❌ Add Sale Items Error: {str(e)}")
        print(f"Full trace:\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add sale items: {str(e)}"
        )


@router.put("/{sale_id}", response_model=SalesResponse)
async def update_sale(
    sale_id: int,
    sale: SalesUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Update a sale
    - Admin: can update any sale
    - Staff: can only update their own sales
    """
    try:
        db = get_db()
        
        # Get existing sale
        existing_sale = await db.sales.find_unique(
            where={"id": sale_id}
        )
        
        if not existing_sale:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sale not found"
            )
        
        # Check permissions
        if current_user.role != "admin" and existing_sale.sold_by != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to edit this sale"
            )
        
        # Build update data
        update_data = {"edited": True}
        if sale.customer_name is not None:
            update_data["customer_name"] = sale.customer_name
        if sale.customer_address is not None:
            update_data["customer_address"] = sale.customer_address
        if sale.customer_phone is not None:
            update_data["customer_phone"] = sale.customer_phone
        if sale.sale_price is not None:
            update_data["sale_price"] = sale.sale_price
        if sale.entry_date is not None:
            update_data["entry_date"] = sale.entry_date
        if sale.payment_type is not None:
            update_data["payment_type"] = str(sale.payment_type)
        if sale.advance_amount is not None:
            update_data["advance_amount"] = sale.advance_amount
        
        # Handle quantity change (adjust inventory)
        if sale.quantity is not None and sale.quantity != existing_sale.quantity:
            # Note: We can't easily reverse inventory changes without product_id
            # For now, just update the quantity
            update_data["quantity"] = sale.quantity
        
        # Update sale
        updated_sale = await db.sales.update(
            where={"id": sale_id},
            data=update_data
        )
        
        if not updated_sale:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update sale"
            )
        
        return SalesResponse(
            id=updated_sale.id,
            invoice_no=updated_sale.invoice_no,
            customer_name=updated_sale.customer_name,
            customer_address=updated_sale.customer_address or "",
            customer_phone=updated_sale.customer_phone or "",
            product_id=None,
            product_name=updated_sale.product_name,
            category=updated_sale.category,
            quantity=updated_sale.quantity,
            cost_price=float(updated_sale.cost_price),
            sale_price=float(updated_sale.sale_price),
            payment_type=updated_sale.payment_type,
            advance_amount=float(updated_sale.advance_amount) if updated_sale.advance_amount is not None else (sale.advance_amount or 0),
            sold_by=updated_sale.sold_by,
            sold_by_name=current_user.name,
            sold_by_role=current_user.role,
            edited=updated_sale.edited if updated_sale.edited is not None else False,
            created_at=str(updated_sale.created_at) if updated_sale.created_at else None,
            entry_date=str(updated_sale.entry_date) if updated_sale.entry_date else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update sale: {str(e)}"
        )





@router.delete("/{sale_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_sale(
    sale_id: int,
    restore_inventory: bool = False,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Delete a sale
    - Admin: can delete any sale
    - Staff: can only delete their own sales
    - restore_inventory: If True, add the quantity back to inventory
    """
    try:
        db = get_db()
        
        # Get existing sale
        existing_sale = await db.sales.find_unique(
            where={"id": sale_id}
        )
        
        if not existing_sale:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sale not found"
            )
        
        # Check permissions
        if current_user.role != "admin" and existing_sale.sold_by != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You don't have permission to delete this sale"
            )
        
        # If restore_inventory is True, find the product and restore quantity
        if restore_inventory:
            # Find product by name and category
            product = await db.inventory.find_first(
                where={
                    "product_name": existing_sale.product_name,
                    "category": existing_sale.category
                }
            )
            
            if product:
                # Add the quantity back to inventory
                new_quantity = product.quantity + existing_sale.quantity
                await db.inventory.update(
                    where={"id": product.id},
                    data={"quantity": new_quantity}
                )
        
        # Delete sale
        deleted_sale = await db.sales.delete(
            where={"id": sale_id}
        )
        
        if not deleted_sale:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Sale not found"
            )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete sale: {str(e)}"
        )


@router.get("/", response_model=List[SalesResponse])

async def get_sales(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get sales records
    - Admin: sees all sales
    - Staff: sees only their own sales
    """
    try:
        db = get_db()
        
        # Build where clause based on user role
        where_clause = {}
        if current_user.role == "staff":
            where_clause["sold_by"] = str(current_user.id)
        
        sales_data = await db.sales.find_many(
            where=where_clause if where_clause else None,
            order={"created_at": "desc"}
        )
        
        # Get all unique user IDs to fetch user names and roles
        user_ids = list(set([item.sold_by for item in sales_data if item.sold_by]))
        
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
        
        sales = []
        for item in sales_data:
            # Get user name and role
            user_info = user_map.get(item.sold_by, {"name": "Unknown", "role": "staff"})
            user_name = user_info.get("name", "Unknown")
            user_role = user_info.get("role", "staff")
            
            sales.append(SalesResponse(
                id=item.id,
                invoice_no=item.invoice_no,
                customer_name=item.customer_name,
                customer_address=item.customer_address or "",
                customer_phone=item.customer_phone or "",
                product_id=None,  # Not stored in sales table
                product_name=item.product_name,
                category=item.category,
                quantity=item.quantity,
                cost_price=float(item.cost_price),
                sale_price=float(item.sale_price),
                payment_type=item.payment_type,
                advance_amount=float(item.advance_amount) if item.advance_amount is not None else 0,
                sold_by=item.sold_by,
                sold_by_name=user_name,
                sold_by_role=user_role,
                edited=item.edited if item.edited is not None else False,
                created_at=str(item.created_at) if item.created_at else None,
                entry_date=str(item.entry_date) if item.entry_date else None
            ))
        
        return sales
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Sales GET Error: {str(e)}")
        print(f"Full trace:\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch sales: {str(e)}"
        )


@router.get("/invoice/{invoice_no}", response_class=StreamingResponse)
async def generate_invoice(
    invoice_no: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Generate PDF invoice for a specific invoice_no
    - Fetches all sales with the given invoice_no
    - Generates a professional invoice PDF with logo
    """
    try:
        db = get_db()
        
        # Build where clause based on user role
        where_clause = {"invoice_no": invoice_no}
        if current_user.role == "staff":
            where_clause["sold_by"] = str(current_user.id)
        
        # Fetch all sales with this invoice_no
        sales_data = await db.sales.find_many(
            where=where_clause,
            order={"created_at": "asc"}
        )
        
        if not sales_data or len(sales_data) == 0:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Invoice {invoice_no} not found"
            )
        
        # Generate PDF invoice
        pdf_buffer = export_service.create_invoice_pdf(sales_data, invoice_no)
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Invoice_{invoice_no}.pdf"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Invoice Generation Error: {str(e)}")
        print(f"Full trace:\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate invoice: {str(e)}"
        )
