"""Database testing utilities."""
from typing import List, Type, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.db.base import Base


async def create_test_data(session: AsyncSession, model: Type[Base], data_list: List[dict]) -> List[Any]:
    """Create multiple test records."""
    instances = []
    for data in data_list:
        instance = model(**data)
        session.add(instance)
        instances.append(instance)
    
    await session.commit()
    
    for instance in instances:
        await session.refresh(instance)
    
    return instances


async def count_records(session: AsyncSession, model: Type[Base]) -> int:
    """Count records in a table."""
    result = await session.execute(select(model))
    return len(result.scalars().all())


async def clear_table(session: AsyncSession, model: Type[Base]):
    """Clear all records from a table."""
    await session.execute(f"DELETE FROM {model.__tablename__}")
    await session.commit()


async def get_record_by_id(session: AsyncSession, model: Type[Base], record_id: int):
    """Get a record by ID."""
    result = await session.execute(select(model).where(model.id == record_id))
    return result.scalar_one_or_none()