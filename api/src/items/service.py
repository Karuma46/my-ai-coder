from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from src.items.models import Item
from src.items.schemas import ItemCreate, ItemUpdate


async def create_item(session: AsyncSession, payload: ItemCreate) -> Item:
    item = Item(**payload.model_dump())
    session.add(item)
    await session.commit()
    await session.refresh(item)
    return item


async def list_items(session: AsyncSession, *, offset: int, limit: int) -> list[Item]:
    result = await session.scalars(select(Item).order_by(Item.id).offset(offset).limit(limit))
    return list(result)


async def get_item(session: AsyncSession, item_id: int) -> Item | None:
    return await session.get(Item, item_id)


async def update_item(session: AsyncSession, item: Item, payload: ItemUpdate) -> Item:
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(item, field, value)

    await session.commit()
    await session.refresh(item)
    return item


async def delete_item(session: AsyncSession, item: Item) -> None:
    await session.delete(item)
    await session.commit()
