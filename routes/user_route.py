from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, status
from sqlmodel.ext.asyncio.session import AsyncSession

from db import get_session
from schema.response import ApiResponse
from schema.user import UserCreate, UserUpdate
from service.user_service import UserService

router = APIRouter(prefix="/users", tags=["users"])
user_service = UserService()


@router.get("/")
async def list_users(
    keyword: str | None = None,
    created_by: str | None = None,
    start_at: datetime | None = None,
    end_at: datetime | None = None,
    skip: int = 0,
    limit: int = 100,
    session: AsyncSession = Depends(get_session),
):
    if keyword or created_by or start_at or end_at:
        result = await user_service.search_users(
            session,
            keyword=keyword,
            created_by=created_by,
            start_at=start_at,
            end_at=end_at,
            skip=skip,
            limit=limit,
        )
    else:
        result = await user_service.list_users(session, skip=skip, limit=limit)
    
    return ApiResponse.success(data=result)


@router.get("/{user_id}")
async def get_user(user_id: int, session: AsyncSession = Depends(get_session)):
    user = await user_service.get_user(session, user_id)
    if user is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
    return ApiResponse.success(data=user)


@router.post("/", status_code=status.HTTP_201_CREATED)
async def create_user(payload: UserCreate, session: AsyncSession = Depends(get_session)):
    try:
        result = await user_service.create_user(session, payload)
        return ApiResponse.success(data=result, msg="创建成功")
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.put("/{user_id}")
async def update_user(
    user_id: int,
    payload: UserUpdate,
    session: AsyncSession = Depends(get_session),
):
    try:
        user = await user_service.update_user(session, user_id, payload)
        if user is None:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")
        return ApiResponse.success(data=user, msg="更新成功")
    except ValueError as error:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=str(error))


@router.delete("/{user_id}", status_code=status.HTTP_204_NO_CONTENT)
async def delete_user(user_id: int, session: AsyncSession = Depends(get_session)):
    success = await user_service.delete_user(session, user_id)
    if not success:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="用户不存在")

