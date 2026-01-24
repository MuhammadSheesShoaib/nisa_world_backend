from fastapi import APIRouter, Depends, HTTPException
from typing import List, Dict, Any
from datetime import datetime, timezone
from decimal import Decimal

from models.schemas import MonthlyReportResponse, MonthlyData, UserResponse, SalesResponse, InventoryResponse, ExpenseResponse
from dependencies import get_current_user, get_current_admin
from database import get_db
from services.export_service import export_service
from fastapi.responses import StreamingResponse
import io


router = APIRouter()


@router.get("/monthly/{year}", response_model=MonthlyReportResponse)
async def get_monthly_report(
    year: int,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get monthly financial report for a specific year.
    
    Returns:
    - Monthly breakdown of revenue, expenses, and profit
    - Total yearly revenue, expenses, and profit
    """
    db = get_db()
    
    # Month names mapping
    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    
    # Initialize monthly data structure
    monthly_data = []
    total_revenue = 0.0
    total_cogs = 0.0
    total_expenses = 0.0
    
    # Process each month (1-12)
    for month_num in range(1, 13):
        # Calculate revenue from sales for this month
        sales = await db.sales.find_many(
            where={
                'created_at': {
                    'gte': datetime(year, month_num, 1),
                    'lt': datetime(year, month_num + 1, 1) if month_num < 12 else datetime(year + 1, 1, 1)
                }
            }
        )
        
        # Sum up revenue (sale_price * quantity)
        month_revenue = sum(
            float(sale.sale_price) * sale.quantity 
            for sale in sales
        )
        
        # Calculate COGS (Cost of Goods Sold) for this month
        month_cogs = sum(
            float(sale.cost_price) * sale.quantity 
            for sale in sales
        )
        
        # Calculate expenses for this month
        expenses = await db.expenses.find_many(
            where={
                'created_at': {
                    'gte': datetime(year, month_num, 1),
                    'lt': datetime(year, month_num + 1, 1) if month_num < 12 else datetime(year + 1, 1, 1)
                }
            }
        )
        
        # Sum up expenses
        month_expenses = sum(float(expense.amount) for expense in expenses)
        
        # Calculate net profit: Revenue - COGS - Operating Expenses
        month_profit = month_revenue - month_cogs - month_expenses
        
        # Add to totals
        total_revenue += month_revenue
        total_cogs += month_cogs
        total_expenses += month_expenses
        
        # Append monthly data
        monthly_data.append(MonthlyData(
            month=month_names[month_num - 1],
            month_number=month_num,
            revenue=round(month_revenue, 2),
            expenses=round(month_expenses, 2),
            profit=round(month_profit, 2)
        ))
    
    # Calculate total net profit: Revenue - COGS - Operating Expenses
    total_profit = total_revenue - total_cogs - total_expenses
    
    return MonthlyReportResponse(
        months=monthly_data,
        total_revenue=round(total_revenue, 2),
        total_expenses=round(total_expenses, 2),
        total_profit=round(total_profit, 2)
    )


@router.get("/export/monthly/{year}/{month}", response_model=Dict[str, Any])
async def get_monthly_detailed_data(
    year: int,
    month: int,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get detailed data for a specific month (sales, inventory, expenses)
    Includes who added/edited each entry
    """
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
    
    db = get_db()
    
    # Calculate date range for the month
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    # Build where clause based on user role
    sales_where = {
        'created_at': {
            'gte': start_date,
            'lt': end_date
        }
    }
    inventory_where = {
        'created_at': {
            'gte': start_date,
            'lt': end_date
        }
    }
    expenses_where = {
        'created_at': {
            'gte': start_date,
            'lt': end_date
        }
    }
    
    if current_user.role == "staff":
        sales_where['sold_by'] = str(current_user.id)
        inventory_where['added_by'] = str(current_user.id)
        expenses_where['added_by'] = str(current_user.id)
    
    # Fetch sales
    sales_data = await db.sales.find_many(
        where=sales_where,
        order={"created_at": "desc"}
    )
    
    # Fetch inventory
    inventory_data = await db.inventory.find_many(
        where=inventory_where,
        order={"created_at": "desc"}
    )
    
    # Fetch expenses
    expenses_data = await db.expenses.find_many(
        where=expenses_where,
        order={"created_at": "desc"}
    )
    
    # Get all unique user IDs
    user_ids = set()
    for sale in sales_data:
        if sale.sold_by:
            user_ids.add(sale.sold_by)
    for item in inventory_data:
        if item.added_by:
            user_ids.add(item.added_by)
    for expense in expenses_data:
        if expense.added_by:
            user_ids.add(expense.added_by)
    
    # Fetch user info
    user_map = {}
    if user_ids:
        int_user_ids = [int(uid) for uid in user_ids if uid and uid.isdigit()]
        if int_user_ids:
            users_data = await db.users.find_many(
                where={"id": {"in": int_user_ids}}
            )
            for user in users_data:
                user_map[str(user.id)] = user.name
    
    # Format sales
    sales = []
    for sale in sales_data:
        sales.append({
            "id": sale.id,
            "invoice_no": sale.invoice_no or "-",
            "customer_name": sale.customer_name,
            "customer_address": sale.customer_address or "",
            "customer_phone": sale.customer_phone or "",
            "product_name": sale.product_name,
            "category": sale.category,
            "quantity": sale.quantity,
            "cost_price": float(sale.cost_price),
            "sale_price": float(sale.sale_price),
            "total": float(sale.sale_price) * sale.quantity,
            "payment_type": sale.payment_type,
            "sold_by": sale.sold_by,
            "sold_by_name": user_map.get(sale.sold_by, "Unknown"),
            "edited": sale.edited if sale.edited is not None else False,
            "created_at": sale.created_at.isoformat() if sale.created_at else None
        })
    
    # Format inventory
    inventory = []
    for item in inventory_data:
        inventory.append({
            "id": item.id,
            "invoice_no": item.invoice_no or "-",
            "product_name": item.product_name,
            "category": item.category,
            "cost_price": float(item.cost_price),
            "sale_price": float(item.cost_price) * 1.5,  # Calculate 50% markup
            "quantity": item.quantity,
            "total_value": float(item.cost_price) * item.quantity,
            "added_by": item.added_by,
            "added_by_name": user_map.get(item.added_by, "Unknown"),
            "edited": item.edited if item.edited is not None else False,
            "created_at": item.created_at.isoformat() if item.created_at else None
        })
    
    # Format expenses
    expenses = []
    for expense in expenses_data:
        # Split material_name if it contains vendor info
        material_full = expense.material_name
        if " - " in material_full:
            parts = material_full.split(" - ", 1)
            material_name = parts[0]
            vendor_name = parts[1]
        else:
            material_name = material_full
            vendor_name = "Unknown"
        
        expenses.append({
            "id": expense.id,
            "invoice_no": expense.invoice_no or "-",
            "material_name": material_name,
            "vendor_name": vendor_name,
            "amount": float(expense.amount),
            "payment_method": expense.payment_method,
            "added_by": expense.added_by,
            "added_by_name": user_map.get(expense.added_by, "Unknown"),
            "edited": expense.edited if expense.edited is not None else False,
            "created_at": expense.created_at.isoformat() if expense.created_at else None
        })
    
    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    
    return {
        "month": month_names[month - 1],
        "month_number": month,
        "year": year,
        "sales": sales,
        "inventory": inventory,
        "expenses": expenses
    }


@router.get("/export/monthly-pdf/{year}/{month}", response_class=StreamingResponse)
async def export_monthly_pdf(
    year: int,
    month: int,
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Generate detailed PDF report for a specific month with all entries
    """
    if month < 1 or month > 12:
        raise HTTPException(status_code=400, detail="Month must be between 1 and 12")
    
    db = get_db()
    
    # Calculate date range for the month - match the format used in monthly report
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    print(f"DEBUG: Fetching data for month {month} ({year}) - Date range: {start_date} to {end_date}")
    
    # Build where clause based on user role - use same format as monthly report endpoint
    sales_where = {
        'created_at': {
            'gte': start_date,
            'lt': end_date
        }
    }
    inventory_where = {
        'created_at': {
            'gte': start_date,
            'lt': end_date
        }
    }
    expenses_where = {
        'created_at': {
            'gte': start_date,
            'lt': end_date
        }
    }
    
    if current_user.role == "staff":
        sales_where['sold_by'] = str(current_user.id)
        inventory_where['added_by'] = str(current_user.id)
        expenses_where['added_by'] = str(current_user.id)
    
    # Fetch sales
    sales_data = await db.sales.find_many(
        where=sales_where,
        order={"created_at": "desc"}
    )
    
    # Fetch inventory
    inventory_data = await db.inventory.find_many(
        where=inventory_where,
        order={"created_at": "desc"}
    )
    
    # Fetch expenses
    expenses_data = await db.expenses.find_many(
        where=expenses_where,
        order={"created_at": "desc"}
    )
    
    # Get all unique user IDs
    user_ids = set()
    for sale in sales_data:
        if sale.sold_by:
            user_ids.add(sale.sold_by)
    for item in inventory_data:
        if item.added_by:
            user_ids.add(item.added_by)
    for expense in expenses_data:
        if expense.added_by:
            user_ids.add(expense.added_by)
    
    # Fetch user info
    user_map = {}
    if user_ids:
        int_user_ids = [int(uid) for uid in user_ids if uid and uid.isdigit()]
        if int_user_ids:
            users_data = await db.users.find_many(
                where={"id": {"in": int_user_ids}}
            )
            for user in users_data:
                user_map[str(user.id)] = user.name
    
    # Format sales
    sales = []
    for sale in sales_data:
        sales.append({
            "invoice_no": sale.invoice_no or "-",
            "customer_name": sale.customer_name,
            "customer_address": sale.customer_address or "",
            "customer_phone": sale.customer_phone or "",
            "product_name": sale.product_name,
            "category": sale.category,
            "quantity": sale.quantity,
            "cost_price": float(sale.cost_price),
            "sale_price": float(sale.sale_price),
            "total": float(sale.sale_price) * sale.quantity,
            "payment_type": sale.payment_type,
            "sold_by": sale.sold_by,
            "sold_by_name": user_map.get(sale.sold_by, "Unknown"),
            "edited": sale.edited if sale.edited is not None else False,
            "created_at": sale.created_at.isoformat() if sale.created_at else None
        })
    
    # Format inventory
    inventory = []
    for item in inventory_data:
        inventory.append({
            "invoice_no": item.invoice_no or "-",
            "product_name": item.product_name,
            "category": item.category,
            "cost_price": float(item.cost_price),
            "sale_price": float(item.cost_price) * 1.5,
            "quantity": item.quantity,
            "total_value": float(item.cost_price) * item.quantity,
            "added_by": item.added_by,
            "added_by_name": user_map.get(item.added_by, "Unknown"),
            "edited": item.edited if item.edited is not None else False,
            "created_at": item.created_at.isoformat() if item.created_at else None
        })
    
    # Format expenses
    expenses = []
    for expense in expenses_data:
        # Split material_name if it contains vendor info
        material_full = expense.material_name
        if " - " in material_full:
            parts = material_full.split(" - ", 1)
            material_name = parts[0]
            vendor_name = parts[1]
        else:
            material_name = material_full
            vendor_name = "Unknown"
        
        expenses.append({
            "invoice_no": expense.invoice_no or "-",
            "material_name": material_name,
            "vendor_name": vendor_name,
            "amount": float(expense.amount),
            "payment_method": expense.payment_method,
            "added_by": expense.added_by,
            "added_by_name": user_map.get(expense.added_by, "Unknown"),
            "edited": expense.edited if expense.edited is not None else False,
            "created_at": expense.created_at.isoformat() if expense.created_at else None
        })
    
    month_names = [
        "January", "February", "March", "April", "May", "June",
        "July", "August", "September", "October", "November", "December"
    ]
    month_name = month_names[month - 1]
    print(f"DEBUG: Generating PDF for {month_name} {year}")
    
    # Generate PDF
    pdf_buffer = export_service.create_monthly_detailed_report(sales, inventory, expenses, month_name, year)
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Monthly_Report_{month_name}_{year}.pdf"}
    )


@router.get("/export/pdf", response_class=StreamingResponse)
async def export_data_pdf(
    current_admin: UserResponse = Depends(get_current_admin)
):
    """
    Generate AI-powered PDF report of all business data (Admin only)
    """
    db = get_db()
    
    # Fetch all data
    sales = await db.sales.find_many()
    inventory = await db.inventory.find_many()
    expenses = await db.expenses.find_many()
    users = await db.users.find_many()
    
    # Generate PDF
    pdf_buffer = await export_service.create_full_report(sales, inventory, expenses, users)
    
    return StreamingResponse(
        pdf_buffer,
        media_type="application/pdf",
        headers={"Content-Disposition": f"attachment; filename=Nisa_World_Furniture_Report_{datetime.now().strftime('%Y%m%d')}.pdf"}
    )

