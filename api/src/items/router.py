from fastapi import APIRouter, HTTPException, Query, Response, status

from src.database import DatabaseSession
from src.items import service
from src.items.schemas import ItemCreate, ItemResponse, ItemUpdate

router = APIRouter(prefix="/items", tags=["items"])


@router.post(
    "",
    response_model=ItemResponse,
    status_code=status.HTTP_201_CREATED,
    summary="Create an item",
)
async def create_item(payload: ItemCreate, session: DatabaseSession):
    return await service.create_item(session, payload)


@router.get("", response_model=list[ItemResponse], summary="List items")
async def list_items(
    session: DatabaseSession,
    offset: int = Query(default=0, ge=0),
    limit: int = Query(default=100, ge=1, le=100),
):
    return await service.list_items(session, offset=offset, limit=limit)


@router.get("/{item_id}", response_model=ItemResponse, summary="Get an item")
async def get_item(item_id: int, session: DatabaseSession):
    item = await service.get_item(session, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return item


@router.patch("/{item_id}", response_model=ItemResponse, summary="Update an item")
async def update_item(item_id: int, payload: ItemUpdate, session: DatabaseSession):
    item = await service.get_item(session, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    return await service.update_item(session, item, payload)


@router.delete(
    "/{item_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    summary="Delete an item",
)
async def delete_item(item_id: int, session: DatabaseSession) -> Response:
    item = await service.get_item(session, item_id)
    if item is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Item not found")
    await service.delete_item(session, item)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
