from pydantic import BaseModel, EmailStr
from typing import Optional, List
from datetime import datetime


# Auth Schemas
class AdminLoginRequest(BaseModel):
    email: EmailStr
    password: str


class StaffLoginRequest(BaseModel):
    email: EmailStr
    password: str


class StaffSignupRequest(BaseModel):
    name: str
    email: EmailStr
    password: str


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class UserPasswordUpdate(BaseModel):
    password: str



class CreateUserRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    role: str  # 'admin' or 'staff'


class UserResponse(BaseModel):
    id: str
    name: str
    email: str
    role: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class UserResponseWithPassword(BaseModel):
    """User response including password - for admin user management only"""
    id: str
    name: str
    email: str
    password: str
    role: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse


# Category Schemas
class CategoryBase(BaseModel):
    category_name: str


class CreateCategoryRequest(BaseModel):
    name: str  # Accept 'name' in request for simplicity


class CategoryResponse(BaseModel):
    category_id: int
    category_name: str
    created_at: Optional[datetime] = None

    class Config:
        from_attributes = True


class MessageResponse(BaseModel):
    message: str


# Inventory Schemas
class InventoryCreate(BaseModel):
    product_name: str
    category: str
    cost_price: float
    sale_price: float = 0  # Optional, can be 0
    quantity: int


class InventoryResponse(BaseModel):
    id: int
    invoice_no: Optional[str] = None
    product_name: str
    category: str
    cost_price: float
    sale_price: Optional[float] = None  # Not stored in DB, calculated
    quantity: int
    added_by: str
    added_by_name: Optional[str] = None
    added_by_role: Optional[str] = None
    edited: Optional[bool] = False
    created_at: Optional[str] = None


class InventoryUpdate(BaseModel):
    product_name: Optional[str] = None
    category: Optional[str] = None
    cost_price: Optional[float] = None
    sale_price: Optional[float] = None
    quantity: Optional[int] = None


# Bulk Inventory Schemas (for multi-item inventory)
class InventoryItem(BaseModel):
    product_name: str
    category: str
    cost_price: float
    sale_price: Optional[float] = None
    quantity: int


class BulkInventoryCreate(BaseModel):
    items: List[InventoryItem]  # List of inventory items



# Raw Material Schemas
class RawMaterialCreate(BaseModel):
    material_name: str
    amount: float
    payment_method: str  # "1" or "2" (stored as text in DB)
    advance_paid: float = 0
    used: bool = False  # True=Yes, False=No


class RawMaterialResponse(BaseModel):
    id: int
    material_name: str
    amount: float
    payment_method: str
    advance_paid: float
    used: bool
    added_by: str
    added_by_name: Optional[str] = None
    created_at: Optional[str] = None


# Sales Schemas
class SalesCreate(BaseModel):
    customer_name: str
    customer_address: str
    customer_phone: str
    product_id: int
    quantity: int
    sale_price: float
    payment_type: str  # "1" or "2" (stored as text in DB)
    advance_amount: float = 0


class SalesResponse(BaseModel):
    id: int
    invoice_no: Optional[str] = None
    customer_name: str
    customer_address: str
    customer_phone: str
    product_id: Optional[int] = None
    product_name: str
    category: str
    quantity: int
    cost_price: float
    sale_price: float
    payment_type: str
    advance_amount: Optional[float] = 0
    sold_by: str
    sold_by_name: Optional[str] = None
    sold_by_role: Optional[str] = None
    edited: Optional[bool] = False
    created_at: Optional[str] = None


class SalesUpdate(BaseModel):
    customer_name: Optional[str] = None
    customer_address: Optional[str] = None
    customer_phone: Optional[str] = None
    quantity: Optional[int] = None
    sale_price: Optional[float] = None
    payment_type: Optional[str] = None
    advance_amount: Optional[float] = None


# Bulk Sales Schemas (for multi-product sales)
class SaleItem(BaseModel):
    product_id: int
    quantity: int
    sale_price: float


class BulkSalesCreate(BaseModel):
    customer_name: str
    customer_address: Optional[str] = None
    customer_phone: Optional[str] = None
    payment_type: str  # "1" or "2"
    advance_amount: float = 0
    items: List[SaleItem]  # List of products in this sale



# Expense Schemas
class ExpenseCreate(BaseModel):
    material_name: str
    vendor_name: str
    amount: float
    payment_method: str  # "1" or "2" (stored as text in DB)
    advance_amount: float = 0


# Bulk Expense Schemas (for multi-item expenses)
class ExpenseItem(BaseModel):
    material_name: str
    vendor_name: str
    amount: float


class BulkExpenseCreate(BaseModel):
    payment_method: str  # "1" or "2"
    advance_amount: float = 0
    items: List[ExpenseItem]  # List of expense items


class ExpenseUpdate(BaseModel):
    material_name: Optional[str] = None
    vendor_name: Optional[str] = None
    amount: Optional[float] = None
    payment_method: Optional[str] = None
    advance_amount: Optional[float] = None
    used: Optional[bool] = None
    description: Optional[str] = None



class ExpenseResponse(BaseModel):
    id: int
    invoice_no: Optional[str] = None
    material_name: str
    vendor_name: str
    amount: float
    payment_method: str
    advance_amount: Optional[float] = 0
    used: Optional[bool] = False
    description: Optional[str] = None
    added_by: str
    added_by_name: Optional[str] = None
    added_by_role: Optional[str] = None
    edited: Optional[bool] = False
    created_at: Optional[str] = None


# Dashboard Stats Schemas
class DashboardStats(BaseModel):
    total_sales: float
    total_profit: float
    total_expenses: float
    total_pending: float
    inventory_value: float
    sales_count: int
    expenses_count: int
    inventory_count: int


# Reports Schemas
class MonthlyData(BaseModel):
    """Monthly financial data"""
    month: str
    month_number: int
    revenue: float
    expenses: float
    profit: float

    class Config:
        from_attributes = True


class MonthlyReportResponse(BaseModel):
    """Complete monthly report for a year"""
    months: list[MonthlyData]
    total_revenue: float
    total_expenses: float
    total_profit: float

    class Config:
        from_attributes = True
