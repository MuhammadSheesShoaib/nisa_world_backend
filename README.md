# Nisa World Furniture Backend API

FastAPI backend for Nisa World Furniture Business Management System with Role-Based Access Control.

## Features

- **Authentication** - JWT-based auth with admin & staff roles
- **Role-Based Access Control** - Admin sees all data, Staff sees only their own
- **Inventory Management** - Products and raw materials tracking
- **Sales Management** - Customer orders with automatic inventory updates
- **Expense Tracking** - Business expense management
- **Dashboard Stats** - Real-time aggregated statistics

## Quick Start

### 1. Database Setup

This project uses **Prisma PostgreSQL**. Your database should already be set up with the schema defined in `backend/prisma/schema.prisma`.

### 2. Environment Configuration

Create `.env` file in `backend` directory:
```env
DATABASE_URL="postgresql://user:password@host:5432/database?sslmode=require"
JWT_SECRET_KEY=your-secret-key-change-in-production
JWT_ACCESS_TOKEN_EXPIRE_HOURS=24
```

### 3. Install Dependencies

```bash
cd backend
pip install -r requirements.txt
```

### 4. Generate Prisma Client

```bash
python -m prisma generate
```

### 5. Run Server

```bash
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

## API Documentation

- **Swagger UI:** http://localhost:8000/docs
- **ReDoc:** http://localhost:8000/redoc
- **Full Documentation:** See `API_DOCUMENTATION.md`

## Project Structure

```
backend/
├── main.py                 # FastAPI app & router registration
├── config.py               # Environment configuration
├── database.py             # Prisma client setup
├── dependencies.py         # Auth dependencies
├── api/
│   ├── auth.py            # Authentication endpoints
│   ├── inventory.py       # Inventory management
│   ├── sales.py           # Sales management
│   ├── expenses.py        # Expense tracking
│   ├── categories.py      # Category management
│   └── dashboard.py       # Dashboard statistics
├── models/
│   └── schemas.py         # Pydantic models
├── services/
│   └── auth_service.py    # Auth business logic
├── prisma/
│   └── schema.prisma      # Prisma database schema
├── requirements.txt
├── .env
└── MIGRATION_GUIDE.md     # Migration from Supabase docs
```

## API Endpoints

### Authentication
- `POST /api/auth/admin/login` - Admin login
- `POST /api/auth/staff/login` - Staff login
- `POST /api/auth/staff/signup` - Staff signup
- `GET /api/auth/me` - Get current user
- `POST /api/auth/logout` - Logout
- `POST /api/auth/change-password` - Change password
- `POST /api/auth/create-user` - Create user (Admin only)

### Inventory
- `POST /api/inventory/products` - Add product
- `GET /api/inventory/products` - Get products
- `POST /api/inventory/raw-materials` - Add raw material
- `GET /api/inventory/raw-materials` - Get raw materials

### Sales
- `POST /api/sales/` - Create sale (auto-updates inventory)
- `GET /api/sales/` - Get sales

### Expenses
- `POST /api/expenses/` - Create expense
- `GET /api/expenses/` - Get expenses

### Dashboard
- `GET /api/dashboard/stats` - Get aggregated statistics

## Role-Based Access

### Admin (`role_id=1`)
✅ View ALL data (sales, inventory, expenses)
✅ Create new users
✅ See business-wide statistics
✅ Add sales, inventory, expenses

### Staff (`role_id=2`)
✅ View ONLY their own data
✅ Add sales, inventory, expenses
✅ See their personal statistics
❌ Cannot create users
❌ Cannot see other staff data

## Testing

### Test Database Connection
```bash
python test_db_connection.py
```

### Check User Credentials
```bash
python check_user.py
```

## Development

1. Make changes to code
2. Server auto-reloads (if using --reload flag)
3. Test via Swagger UI or frontend
4. Check logs in terminal

## Security Notes

⚠️ **Current Implementation:**
- Passwords stored as plain text (for development)
- For production, implement password hashing
- Use strong JWT_SECRET_KEY
- Keep service role key secure

## Support

For detailed API documentation, see `API_DOCUMENTATION.md`

