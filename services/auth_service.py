from database import get_db, ensure_connected
from config import settings
from models.schemas import UserResponse
from typing import Optional, Tuple
from fastapi import HTTPException, status
from jose import JWTError, jwt
from datetime import datetime, timedelta


class AuthService:
    def __init__(self):
        self.db = get_db()
    
    def _verify_password(self, plain_password: str, stored_password: str) -> bool:
        """
        Verify a password - handles both plain text and hashed passwords
        Since you're using plain text passwords in Postgres, we do simple comparison
        """
        # Simple plain text comparison (no hashing)
        return plain_password == stored_password
    
    def _create_access_token(self, user_id: str, email: str, role: str) -> str:
        """Create JWT access token"""
        expire = datetime.utcnow() + timedelta(hours=settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS)
        to_encode = {
            "sub": user_id,
            "email": email,
            "role": role,
            "exp": expire
        }
        encoded_jwt = jwt.encode(
            to_encode,
            settings.JWT_SECRET_KEY,
            algorithm=settings.JWT_ALGORITHM
        )
        return encoded_jwt
    
    def _decode_token(self, token: str) -> dict:
        """Decode and verify JWT token"""
        try:
            payload = jwt.decode(
                token,
                settings.JWT_SECRET_KEY,
                algorithms=[settings.JWT_ALGORITHM]
            )
            return payload
        except JWTError:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid or expired token"
            )
    
    def _role_id_to_string(self, role_id: int) -> str:
        """Convert role_id (1=Admin, 2=Staff) to string"""
        return "admin" if role_id == 1 else "staff"
    
    def _role_string_to_id(self, role: str) -> int:
        """Convert role string (admin/staff) to role_id (1/2)"""
        return 1 if role == "admin" else 2
    
    async def admin_login(self, email: str, password: str) -> Tuple[dict, UserResponse]:
        """
        Authenticate admin user from Postgres database
        Returns: (auth_data, user_data)
        """
        # Ensure database connection is active
        await ensure_connected()
        try:
            # Query user from database - role_id 1 = Admin
            user_data_db = await self.db.users.find_first(
                where={
                    "email": email,
                    "role_id": 1
                }
            )
            
            if not user_data_db:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            # Verify password (stored as 'password' column, should be hashed)
            if not self._verify_password(password, user_data_db.password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            # Convert role_id to role string
            role = self._role_id_to_string(user_data_db.role_id)
            
            # Create access token
            access_token = self._create_access_token(
                user_id=str(user_data_db.id),
                email=user_data_db.email,
                role=role
            )
            
            user_data = UserResponse(
                id=str(user_data_db.id),
                name=user_data_db.name,
                email=user_data_db.email,
                role=role,
                created_at=user_data_db.created_at
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS * 3600
            }, user_data
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Authentication failed: {str(e)}"
            )
    
    async def staff_login(self, email: str, password: str) -> Tuple[dict, UserResponse]:
        """
        Authenticate staff user from Postgres database
        Returns: (auth_data, user_data)
        """
        # Ensure database connection is active
        await ensure_connected()
        try:
            # Query user from database
            user_data_db = await self.db.users.find_first(
                where={"email": email}
            )
            
            if not user_data_db:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            # Verify password (stored as 'password' column)
            if not self._verify_password(password, user_data_db.password):
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="Invalid email or password"
                )
            
            # Convert role_id to role string
            role = self._role_id_to_string(user_data_db.role_id)
            
            # Create access token
            access_token = self._create_access_token(
                user_id=str(user_data_db.id),
                email=user_data_db.email,
                role=role
            )
            
            user_data = UserResponse(
                id=str(user_data_db.id),
                name=user_data_db.name,
                email=user_data_db.email,
                role=role,
                created_at=user_data_db.created_at
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS * 3600
            }, user_data
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Authentication failed: {str(e)}"
            )
    
    async def staff_signup(self, name: str, email: str, password: str) -> Tuple[dict, UserResponse]:
        """
        Register new staff user in Postgres database
        Returns: (auth_data, user_data)
        """
        # Ensure database connection is active
        await ensure_connected()
        try:
            # Insert user into database - role_id 2 = Staff
            # Store password as plain text (no hashing)
            user_data_db = await self.db.users.create(
                data={
                    "email": email,
                    "password": password,  # Plain text password
                    "name": name,
                    "role_id": 2  # 2 = Staff
                }
            )
            
            if not user_data_db:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create user"
                )
            
            # Convert role_id to role string
            role = self._role_id_to_string(user_data_db.role_id)
            
            # Create access token
            access_token = self._create_access_token(
                user_id=str(user_data_db.id),
                email=user_data_db.email,
                role=role
            )
            
            user_data = UserResponse(
                id=str(user_data_db.id),
                name=user_data_db.name,
                email=user_data_db.email,
                role=role,
                created_at=user_data_db.created_at
            )
            
            return {
                "access_token": access_token,
                "token_type": "bearer",
                "expires_in": settings.JWT_ACCESS_TOKEN_EXPIRE_HOURS * 3600
            }, user_data
            
        except Exception as e:
            error_str = str(e).lower()
            if "duplicate" in error_str or "unique" in error_str or "already exists" in error_str:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Registration failed: {str(e)}"
            )
    
    async def get_current_user(self, token: str) -> UserResponse:
        """
        Get current user from JWT token
        """
        # Ensure database connection is active
        await ensure_connected()
        try:
            # Decode token
            payload = self._decode_token(token)
            user_id = payload.get("sub")
            email = payload.get("email")
            role = payload.get("role")
            
            # Query user from database to ensure still exists
            user_data_db = await self.db.users.find_unique(
                where={"id": int(user_id)}
            )
            
            if not user_data_db:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            # Convert role_id to role string
            role = self._role_id_to_string(user_data_db.role_id)
            
            return UserResponse(
                id=str(user_data_db.id),
                name=user_data_db.name,
                email=user_data_db.email,
                role=role,
                created_at=user_data_db.created_at
            )
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail=f"Invalid or expired token: {str(e)}"
            )
    
    async def change_password(self, token: str, current_password: str, new_password: str) -> bool:
        """
        Change user password
        """
        try:
            # Get user from token
            payload = self._decode_token(token)
            user_id = payload.get("sub")
            
            # Query user from database
            user_data_db = await self.db.users.find_unique(
                where={"id": int(user_id)}
            )
            
            if not user_data_db:
                raise HTTPException(
                    status_code=status.HTTP_401_UNAUTHORIZED,
                    detail="User not found"
                )
            
            # Verify current password (column is 'password', not 'password_hash')
            if not self._verify_password(current_password, user_data_db.password):
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Current password is incorrect"
                )
            
            # Update password in database (plain text, no hashing)
            await self.db.users.update(
                where={"id": int(user_id)},
                data={"password": new_password}
            )
            
            return True
            
        except HTTPException:
            raise
        except Exception as e:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to change password: {str(e)}"
            )
    
    async def create_user(self, name: str, email: str, password: str, role: str) -> UserResponse:
        """
        Create a new user (admin or staff) - Admin only
        """
        try:
            if role not in ["admin", "staff"]:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Role must be 'admin' or 'staff'"
                )
            
            # Convert role string to role_id
            role_id = self._role_string_to_id(role)
            
            # Insert user into database (plain text password, no hashing)
            user_data_db = await self.db.users.create(
                data={
                    "email": email,
                    "password": password,  # Plain text password
                    "name": name,
                    "role_id": role_id  # 1=Admin, 2=Staff
                }
            )
            
            if not user_data_db:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Failed to create user"
                )
            
            # Convert role_id back to role string for response
            role_str = self._role_id_to_string(user_data_db.role_id)
            
            return UserResponse(
                id=str(user_data_db.id),
                name=user_data_db.name,
                email=user_data_db.email,
                role=role_str,
                created_at=user_data_db.created_at
            )
            
        except Exception as e:
            error_str = str(e).lower()
            if "duplicate" in error_str or "unique" in error_str or "already exists" in error_str:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail="Email already registered"
                )
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail=f"Failed to create user: {str(e)}"
            )
    
    async def logout(self, user_id: str) -> bool:
        """
        Logout user (JWT tokens are stateless, so we just return success)
        """
        # Since we're using JWT, logout is handled client-side by removing the token
        # This endpoint is here for API consistency
        return True


# Create singleton instance
auth_service = AuthService()
