#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
@Author: 臧成龙
@Contact: 939589097@qq.com
@Time: 2025-12-31
@File: database.py
@Desc: 获取数据库会话的依赖函数 - async with AsyncSessionLocal() as session:
"""
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from sqlalchemy.orm import declarative_base

from app.config import settings

# 创建异步引擎
engine = create_async_engine(
    settings.DATABASE_URL,
    echo=settings.DEBUG,
)

# 创建异步会话工厂
AsyncSessionLocal = async_sessionmaker(
    bind=engine,
    class_=AsyncSession,
    expire_on_commit=False,
    autocommit=False,
    autoflush=False,
)

# 声明基类
Base = declarative_base()


async def get_db() -> AsyncSession:
    """获取数据库会话的依赖函数"""
    async with AsyncSessionLocal() as session:
        try:
            yield session
        finally:
            await session.close()


async def get_db_transaction() -> AsyncSession:
    """
    获取带事务的数据库会话依赖函数
    
    使用方式：
    @router.post("/")
    async def create_something(db: AsyncSession = Depends(get_db_transaction)):
        # 所有数据库操作在同一事务中
        # 如果发生异常，自动回滚
        # 如果成功完成，自动提交
        ...
    
    注意：使用此依赖时，Service层的方法不应调用commit()，
    因为事务会在API结束时统一提交或回滚。
    可以使用BaseService的_no_commit版本方法，或手动控制。
    """
    async with AsyncSessionLocal() as session:
        try:
            yield session
            await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()


@asynccontextmanager
async def transaction(db: AsyncSession):
    """
    事务上下文管理器，用于在API中包装多个操作
    
    使用方式：
    @router.post("/")
    async def create_something(db: AsyncSession = Depends(get_db)):
        async with transaction(db):
            # 所有操作在同一事务中
            await SomeService.create_no_commit(db, data1)
            await OtherService.create_no_commit(db, data2)
            # 如果发生异常，自动回滚
            # 如果成功完成，自动提交
    """
    try:
        yield db
        await db.commit()
    except Exception:
        await db.rollback()
        raise
