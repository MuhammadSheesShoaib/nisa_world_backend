from prisma import Prisma
from config import settings

# Create a global Prisma client instance
prisma_client = Prisma()


async def connect_db():
    """Connect to the database"""
    if not prisma_client.is_connected():
        await prisma_client.connect()
    return prisma_client


async def disconnect_db():
    """Disconnect from the database"""
    if prisma_client.is_connected():
        await prisma_client.disconnect()


def get_db() -> Prisma:
    """Get the Prisma client instance"""
    return prisma_client


async def ensure_connected():
    """Ensure database connection is active, reconnect if needed"""
    if not prisma_client.is_connected():
        await prisma_client.connect()
