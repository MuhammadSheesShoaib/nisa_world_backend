from fastapi import APIRouter, Depends, HTTPException, status
from models.schemas import DashboardStats, UserResponse
from dependencies import get_current_user
from database import get_db

router = APIRouter(prefix="/dashboard", tags=["Dashboard"])


@router.get("/stats", response_model=DashboardStats)
async def get_dashboard_stats(
    current_user: UserResponse = Depends(get_current_user)
):
    """
    Get dashboard statistics
    - Admin: sees all aggregated data
    - Staff: sees only their own aggregated data
    """
    try:
        db = get_db()
        
        # Build where clause based on user role
        sales_where = {}
        expenses_where = {}
        
        if current_user.role == "staff":
            sales_where["sold_by"] = str(current_user.id)
            expenses_where["added_by"] = str(current_user.id)
        
        # Get sales data
        sales_data = await db.sales.find_many(
            where=sales_where if sales_where else None
        )
        
        # Calculate sales metrics
        total_sales = sum((float(sale.sale_price) * sale.quantity) for sale in sales_data)
        total_cogs = sum((float(sale.cost_price) * sale.quantity) for sale in sales_data)  # Cost of Goods Sold
        total_pending = sum(
            ((float(sale.sale_price) * sale.quantity) - (float(sale.advance_amount) if sale.advance_amount else 0))
            for sale in sales_data if str(sale.payment_type) == "2"
        )
        sales_count = len(sales_data)
        
        # Get expenses data
        expenses_data = await db.expenses.find_many(
            where=expenses_where if expenses_where else None
        )
        
        total_expenses = sum(float(expense.amount) for expense in expenses_data)
        expenses_count = len(expenses_data)
        
        # Calculate net profit: Revenue - COGS - Operating Expenses
        total_profit = total_sales - total_cogs - total_expenses
        
        # Get inventory data (shared - all users see all inventory)
        inventory_data = await db.inventory.find_many()
        
        inventory_value = sum((float(item.cost_price) * item.quantity) for item in inventory_data)
        inventory_count = len(inventory_data)
        
        return DashboardStats(
            total_sales=total_sales,
            total_profit=total_profit,
            total_expenses=total_expenses,
            total_pending=total_pending,
            inventory_value=inventory_value,
            sales_count=sales_count,
            expenses_count=expenses_count,
            inventory_count=inventory_count
        )
    except Exception as e:
        import traceback
        error_trace = traceback.format_exc()
        print(f"❌ Dashboard Error: {str(e)}")
        print(f"Full trace:\n{error_trace}")
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to fetch dashboard stats: {str(e)}"
        )
