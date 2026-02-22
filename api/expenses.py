from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.responses import StreamingResponse
from typing import List
from models.schemas import (
    ExpenseCreate,
    ExpenseUpdate,
    ExpenseResponse,
    BulkExpenseCreate,
    ExpenseItem,
    UserResponse
)
from dependencies import get_current_user
from database import get_db
from services.export_service import export_service
import traceback

router = APIRouter(prefix="/expenses", tags=["Expenses"])


@router.post("/", response_model=ExpenseResponse)
async def create_expense(
    expense: ExpenseCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Create a new expense (Admin and Staff can add) - Uses expenses table
    """
    try:
        db = get_db()
        
        # Combine material_name and vendor_name
        combined_name = f"{expense.material_name} - {expense.vendor_name}"
        
        insert_data = {
            "material_name": combined_name,
            "amount": expense.amount,
            "payment_method": str(expense.payment_method),
            "advance_amount": expense.advance_amount if expense.advance_amount else 0,
            "entry_date": expense.entry_date,
            "added_by": str(current_user.id),
            "used": False,
        }
        
        print(f"📝 Creating expense with data: {insert_data}")
        
        created_expense = await db.expenses.create(data=insert_data)
        
        print(f"✅ Created expense: {created_expense}")
        
        if not created_expense:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to create expense"
            )
        
        # Split back the material_name for response
        if " - " in created_expense.material_name:
            parts = created_expense.material_name.split(" - ", 1)
            material_name = parts[0]
            vendor_name = parts[1]
        else:
            material_name = created_expense.material_name
            vendor_name = "Unknown"
        
        return ExpenseResponse(
            id=created_expense.id,
            invoice_no=created_expense.invoice_no,
            material_name=material_name,
            vendor_name=vendor_name,
            amount=float(created_expense.amount),
            payment_method=created_expense.payment_method,
            advance_amount=float(created_expense.advance_amount) if created_expense.advance_amount is not None else 0,
            used=created_expense.used if created_expense.used is not None else False,
            description=created_expense.description,
            added_by=created_expense.added_by,
            added_by_name=current_user.name,
            added_by_role=current_user.role,
            edited=False,  # New entries are not edited
            created_at=str(created_expense.created_at) if created_expense.created_at else None,
            entry_date=str(created_expense.entry_date) if created_expense.entry_date else None
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Expense Error: {str(e)}")
        print(f"Full trace:\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create expense: {str(e)}"
        )


@router.post("/bulk", response_model=List[ExpenseResponse])
async def create_bulk_expense(
    expense_data: BulkExpenseCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Create an expense with multiple items (bulk expense)
    - Generates ONE invoice_no for all items
    - Creates multiple expense rows with same invoice_no
    """
    try:
        db = get_db()
        
        if not expense_data.items or len(expense_data.items) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one expense item is required"
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
        
        created_expenses = []
        
        # Process each item
        for item in expense_data.items:
            # Combine material_name and vendor_name
            combined_name = f"{item.material_name} - {item.vendor_name}"
            
            # Create expense
            created_expense = await db.expenses.create(
                data={
                    "invoice_no": invoice_no,
                    "material_name": combined_name,
                    "amount": item.amount,
                    "payment_method": str(expense_data.payment_method),
                    "advance_amount": expense_data.advance_amount if expense_data.advance_amount else 0,
                    "entry_date": expense_data.entry_date,
                    "added_by": str(current_user.id),
                    "used": False,
                }
            )
            
            if not created_expense:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create expense for one of the items"
                )
            
            # Split back the material_name for response
            if " - " in created_expense.material_name:
                parts = created_expense.material_name.split(" - ", 1)
                material_name = parts[0]
                vendor_name = parts[1]
            else:
                material_name = created_expense.material_name
                vendor_name = "Unknown"
            
            created_expenses.append(ExpenseResponse(
                id=created_expense.id,
                invoice_no=created_expense.invoice_no,
                material_name=material_name,
                vendor_name=vendor_name,
                amount=float(created_expense.amount),
                payment_method=created_expense.payment_method,
                advance_amount=float(created_expense.advance_amount) if created_expense.advance_amount is not None else 0,
                used=created_expense.used if created_expense.used is not None else False,
                description=created_expense.description,
                added_by=created_expense.added_by,
                added_by_name=current_user.name,
                added_by_role=current_user.role,
                edited=False,
                created_at=str(created_expense.created_at) if created_expense.created_at else None,
                entry_date=str(created_expense.entry_date) if created_expense.entry_date else None
            ))
        
        return created_expenses
    except HTTPException:
        raise
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"❌ Bulk Expense Error: {str(e)}")
        print(f"Full trace:\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to create bulk expense: {str(e)}"
        )


@router.post("/invoice/{invoice_no}/items", response_model=List[ExpenseResponse])
async def add_expense_items_to_invoice(
    invoice_no: str,
    expense_data: BulkExpenseCreate,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Append expense items to an existing invoice_no
    - Does NOT generate a new invoice_no
    - Creates new expense rows with the provided invoice_no
    """
    try:
        db = get_db()

        if not expense_data.items or len(expense_data.items) == 0:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="At least one expense item is required"
            )

        # Permission: staff can only append to their own invoice
        if current_user.role == "staff":
            existing = await db.expenses.find_first(
                where={"invoice_no": invoice_no, "added_by": str(current_user.id)}
            )
            if not existing:
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="You don't have permission to add items to this invoice"
                )

        final_advance = expense_data.advance_amount if str(expense_data.payment_method) != "1" else 0

        created_expenses: List[ExpenseResponse] = []

        for item in expense_data.items:
            combined_name = f"{item.material_name} - {item.vendor_name}"

            created_expense = await db.expenses.create(
                data={
                    "invoice_no": invoice_no,
                    "material_name": combined_name,
                    "amount": item.amount,
                    "payment_method": str(expense_data.payment_method),
                    "advance_amount": final_advance if final_advance else 0,
                    "entry_date": expense_data.entry_date,
                    "added_by": str(current_user.id),
                    "used": False,
                    "edited": True,
                }
            )

            if " - " in created_expense.material_name:
                parts = created_expense.material_name.split(" - ", 1)
                material_name = parts[0]
                vendor_name = parts[1]
            else:
                material_name = created_expense.material_name
                vendor_name = "Unknown"

            created_expenses.append(ExpenseResponse(
                id=created_expense.id,
                invoice_no=created_expense.invoice_no,
                material_name=material_name,
                vendor_name=vendor_name,
                amount=float(created_expense.amount),
                payment_method=created_expense.payment_method,
                advance_amount=float(created_expense.advance_amount) if created_expense.advance_amount is not None else 0,
                used=created_expense.used if created_expense.used is not None else False,
                description=created_expense.description,
                added_by=created_expense.added_by,
                added_by_name=current_user.name,
                added_by_role=current_user.role,
                edited=True,
                created_at=str(created_expense.created_at) if created_expense.created_at else None,
                entry_date=str(created_expense.entry_date) if created_expense.entry_date else None
            ))

        return created_expenses
    except HTTPException:
        raise
    except Exception as e:
        error_trace = traceback.format_exc()
        print(f"❌ Add Expense Items Error: {str(e)}")
        print(f"Full trace:\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to add expense items: {str(e)}"
        )


@router.get("/", response_model=List[ExpenseResponse])
async def get_expenses(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get expenses records
    - Admin: sees all expenses with user info
    - Staff: sees only their own expenses
    """
    try:
        db = get_db()
        
        # Build where clause based on user role
        where_clause = {}
        if current_user.role == "staff":
            where_clause["added_by"] = str(current_user.id)
        
        expenses_data = await db.expenses.find_many(
            where=where_clause if where_clause else None,
            order={"created_at": "desc"}
        )
        
        # Get all unique user IDs to fetch user info
        user_ids = list(set([item.added_by for item in expenses_data if item.added_by]))
        
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
        
        expenses = []
        for item in expenses_data:
            # Try to split material_name back into name and vendor
            material_full = item.material_name
            if " - " in material_full:
                parts = material_full.split(" - ", 1)
                material_name = parts[0]
                vendor_name = parts[1]
            else:
                material_name = material_full
                vendor_name = "Unknown"
            
            # Get user info
            user_id = item.added_by
            user_info = user_map.get(user_id, {"name": "Unknown", "role": "staff"})
            
            expenses.append(ExpenseResponse(
                id=item.id,
                invoice_no=item.invoice_no,
                material_name=material_name,
                vendor_name=vendor_name,
                amount=float(item.amount),
                payment_method=item.payment_method,
                advance_amount=float(item.advance_amount) if item.advance_amount is not None else 0,
                used=item.used if item.used is not None else False,
                description=item.description,
                added_by=user_id,
                added_by_name=user_info["name"],
                added_by_role=user_info["role"],
                edited=item.edited if item.edited is not None else False,
                created_at=str(item.created_at) if item.created_at else None,
                entry_date=str(item.entry_date) if item.entry_date else None
            ))
        
        return expenses
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch expenses: {str(e)}"
        )


@router.put("/{expense_id}", response_model=ExpenseResponse)
async def update_expense(
    expense_id: int,
    expense_update: ExpenseUpdate,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Update an expense
    - Staff: can only update their own expenses
    - Admin: can update any expense
    """
    try:
        db = get_db()
        
        # First, get the expense to check ownership
        expense_data = await db.expenses.find_unique(
            where={"id": expense_id}
        )
        
        if not expense_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expense not found"
            )
        
        # Check permissions: staff can only edit their own
        if current_user.role == "staff" and expense_data.added_by != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only edit your own expenses"
            )
        
        # Prepare update data
        update_data = {"edited": True}  # Mark as edited
        
        # Handle material_name and vendor_name combination
        current_material = expense_data.material_name
        if " - " in current_material:
            parts = current_material.split(" - ", 1)
            current_material_name = parts[0]
            current_vendor_name = parts[1]
        else:
            current_material_name = current_material
            current_vendor_name = "Unknown"
        
        # Update material_name or vendor_name if provided
        new_material_name = expense_update.material_name if expense_update.material_name else current_material_name
        new_vendor_name = expense_update.vendor_name if expense_update.vendor_name else current_vendor_name
        update_data["material_name"] = f"{new_material_name} - {new_vendor_name}"
        
        if expense_update.amount is not None:
            update_data["amount"] = expense_update.amount
        
        if expense_update.payment_method is not None:
            update_data["payment_method"] = str(expense_update.payment_method)
        
        if expense_update.advance_amount is not None:
            update_data["advance_amount"] = expense_update.advance_amount
        
        if expense_update.used is not None:
            update_data["used"] = expense_update.used
        
        if expense_update.description is not None:
            update_data["description"] = expense_update.description
        
        if expense_update.entry_date is not None:
            update_data["entry_date"] = expense_update.entry_date
        
        # Update the expense
        updated_expense = await db.expenses.update(
            where={"id": expense_id},
            data=update_data
        )
        
        if not updated_expense:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Failed to update expense"
            )
        
        # Split back for response
        if " - " in updated_expense.material_name:
            parts = updated_expense.material_name.split(" - ", 1)
            material_name = parts[0]
            vendor_name = parts[1]
        else:
            material_name = updated_expense.material_name
            vendor_name = "Unknown"
        
        # Get user info
        user_data = await db.users.find_unique(
            where={"id": int(updated_expense.added_by)}
        )
        user_info = {"name": "Unknown", "role_id": 2}
        if user_data:
            user_info = {"name": user_data.name, "role_id": user_data.role_id}
        
        return ExpenseResponse(
            id=updated_expense.id,
            invoice_no=updated_expense.invoice_no,
            material_name=material_name,
            vendor_name=vendor_name,
            amount=float(updated_expense.amount),
            payment_method=updated_expense.payment_method,
            advance_amount=float(updated_expense.advance_amount) if updated_expense.advance_amount is not None else 0,
            used=updated_expense.used if updated_expense.used is not None else False,
            description=updated_expense.description,
            added_by=updated_expense.added_by,
            added_by_name=user_info["name"],
            added_by_role="admin" if user_info["role_id"] == 1 else "staff",
            edited=updated_expense.edited if updated_expense.edited is not None else False,
            entry_date=str(updated_expense.entry_date) if updated_expense.entry_date else None,
            created_at=str(updated_expense.created_at) if updated_expense.created_at else None
        )
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to update expense: {str(e)}"
        )


@router.delete("/{expense_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_expense(
    expense_id: int,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Delete an expense
    - Staff: can only delete their own expenses
    - Admin: can delete any expense
    """
    try:
        db = get_db()
        
        # First, get the expense to check ownership
        expense_data = await db.expenses.find_unique(
            where={"id": expense_id}
        )
        
        if not expense_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expense not found"
            )
        
        # Check permissions: staff can only delete their own
        if current_user.role == "staff" and expense_data.added_by != str(current_user.id):
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="You can only delete your own expenses"
            )
        
        # Delete the expense
        deleted_expense = await db.expenses.delete(
            where={"id": expense_id}
        )
        
        if not deleted_expense:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Expense not found"
            )
        
        return None
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to delete expense: {str(e)}"
        )


@router.get("/invoice/{invoice_no}", response_class=StreamingResponse)
async def generate_expense_invoice_pdf(
    invoice_no: str,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Generate PDF invoice for a specific expense invoice_no
    - Fetches all expenses with this invoice_no
    - Staff can only generate invoices for their own expenses
    - Admin can generate any invoice
    """
    try:
        db = get_db()
        
        # Fetch all expenses related to this invoice_no
        expenses_where = {"invoice_no": invoice_no}
        if current_user.role == "staff":
            expenses_where["added_by"] = str(current_user.id)
        
        expenses_data = await db.expenses.find_many(
            where=expenses_where,
            order={"created_at": "asc"}
        )
        
        if not expenses_data:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Invoice not found or you do not have permission to view it."
            )
        
        pdf_buffer = export_service.create_expense_invoice_pdf(expenses_data, invoice_no)
        
        return StreamingResponse(
            pdf_buffer,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=Expense_Invoice_{invoice_no}.pdf"}
        )
    except HTTPException:
        raise
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Expense Invoice Generation Error: {str(e)}")
        print(f"Full trace:\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to generate expense invoice: {str(e)}"
        )
