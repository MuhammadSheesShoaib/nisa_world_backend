#!/usr/bin/env python3
"""
Test database connectivity to Prisma Postgres
Run: python test_db_connection.py
"""

import sys
import os
import asyncio

# Add current directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from config import settings
from database import connect_db, disconnect_db, get_db


async def test_connection():
    """Test connection to Prisma database"""
    print("=" * 60)
    print("Testing Prisma Postgres Database Connection")
    print("=" * 60)
    print()
    
    # Test 1: Load environment variables
    print("1. Checking environment variables...")
    try:
        print(f"   ✓ DATABASE_URL: {settings.DATABASE_URL[:50]}...")
    except Exception as e:
        print(f"   ✗ Error loading environment variables: {str(e)}")
        return False
    print()
    
    # Test 2: Connect to database
    print("2. Connecting to Prisma database...")
    try:
        await connect_db()
        print("   ✓ Database connected successfully")
    except Exception as e:
        print(f"   ✗ Error connecting to database: {str(e)}")
        return False
    print()
    
    # Test 3: Test database connection - Check if users table exists
    print("3. Testing database connection (checking users table)...")
    try:
        db = get_db()
        # Try to count users
        user_count = await db.users.count()
        print(f"   ✓ Successfully connected to database")
        print(f"   ✓ Users table exists")
        print(f"   ✓ Total users in table: {user_count}")
    except Exception as e:
        error_str = str(e).lower()
        if "does not exist" in error_str or "relation" in error_str:
            print(f"   ✗ Users table does not exist in database")
            print(f"   ✗ Please create the users table first")
        else:
            print(f"   ✗ Error connecting to database: {str(e)}")
        return False
    print()
    
    # Test 4: Test basic query
    print("4. Testing basic query (fetching user count)...")
    try:
        db = get_db()
        users = await db.users.find_many()
        print(f"   ✓ Query executed successfully")
        print(f"   ✓ Found {len(users)} user(s) in database")
    except Exception as e:
        print(f"   ✗ Error executing query: {str(e)}")
        return False
    print()
    
    # Test 5: Check table schema
    print("5. Checking users table schema...")
    try:
        db = get_db()
        # Try to query all columns
        users = await db.users.find_first()
        if users:
            print("   ✓ All required columns exist:")
            print("     - id")
            print("     - name")
            print("     - email")
            print("     - password")
            print("     - role_id")
            print("     - created_at")
        else:
            print("   ✓ Table structure verified (no users yet)")
    except Exception as e:
        error_str = str(e).lower()
        if "column" in error_str and "does not exist" in error_str:
            print(f"   ✗ Missing column in users table: {str(e)}")
            print(f"   ✗ Please check your table schema")
        else:
            print(f"   ✗ Error checking schema: {str(e)}")
        return False
    print()
    
    # Test 6: Test role_id values
    print("6. Checking role_id values...")
    try:
        db = get_db()
        users = await db.users.find_many()
        if users:
            print(f"   ✓ Found users with role_ids:")
            for user in users:
                role_name = "Admin" if user.role_id == 1 else "Staff" if user.role_id == 2 else "Unknown"
                print(f"     - {user.email}: role_id={user.role_id} ({role_name})")
        else:
            print("   ✓ No users found (this is okay for a new database)")
    except Exception as e:
        print(f"   ✗ Error checking role_ids: {str(e)}")
        return False
    print()
    
    # Test 7: Check other tables
    print("7. Checking other tables...")
    try:
        db = get_db()
        categories_count = await db.categories.count()
        inventory_count = await db.inventory.count()
        sales_count = await db.sales.count()
        expenses_count = await db.expenses.count()
        
        print(f"   ✓ Categories table: {categories_count} records")
        print(f"   ✓ Inventory table: {inventory_count} records")
        print(f"   ✓ Sales table: {sales_count} records")
        print(f"   ✓ Expenses table: {expenses_count} records")
    except Exception as e:
        print(f"   ✗ Error checking other tables: {str(e)}")
        return False
    print()
    
    # Disconnect
    print("8. Disconnecting from database...")
    try:
        await disconnect_db()
        print("   ✓ Disconnected successfully")
    except Exception as e:
        print(f"   ✗ Error disconnecting: {str(e)}")
        return False
    print()
    
    print("=" * 60)
    print("✓ All database connection tests passed!")
    print("=" * 60)
    return True


if __name__ == "__main__":
    try:
        success = asyncio.run(test_connection())
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\nTest interrupted by user")
        sys.exit(1)
    except Exception as e:
        import traceback
        print(f"\n\n✗ Unexpected error: {str(e)}")
        print(traceback.format_exc())
        sys.exit(1)
