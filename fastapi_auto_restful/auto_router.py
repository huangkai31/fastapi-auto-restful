from fastapi import APIRouter, Depends, HTTPException, status, Request

from sqlalchemy import create_engine, MetaData, select, Engine, func  
from sqlalchemy.ext.asyncio import create_async_engine, AsyncEngine, AsyncSession
from sqlalchemy.orm import sessionmaker, Session
from sqlalchemy.ext.asyncio import async_sessionmaker
from sqlalchemy.ext.automap import automap_base
from pydantic import create_model
from typing import List, Any, Optional, Dict, Union, TypeVar
from .query_parser import parse_query_filters
from .schemas import PaginatedResponse
import warnings

T = TypeVar("T")

def infer_python_type(sql_type_str: str):
    upper = str(sql_type_str).upper()
    TYPE_MAP = {
        "INTEGER": int, "BIGINT": int, "SMALLINT": int,
        "FLOAT": float, "REAL": float, "NUMERIC": float, "DECIMAL": float,
        "BOOLEAN": bool,
        "VARCHAR": str, "CHAR": str, "TEXT": str,
        "DATE": str, "DATETIME": str, "TIMESTAMP": str, "UUID": str,
    }
    for k, v in TYPE_MAP.items():
        if k in upper:
            return v
    return str

def sqlalchemy_to_dict(obj, table, visited=None):
    if visited is None:
        visited = set()
    if id(obj) in visited:
        return {}
    visited.add(id(obj))
    d = {}
    for col in table.columns:
        value = getattr(obj, col.name)
        if hasattr(value, '_sa_instance_state'):
            if value is not None:
                related_table = value.__table__
                d[col.name] = sqlalchemy_to_dict(value, related_table, visited.copy())
            else:
                d[col.name] = None
        else:
            d[col.name] = value
    return d

def _create_pydantic_models(table):
    fields = {}
    for col in table.columns:
        py_type = infer_python_type(str(col.type))
        # 判断是否为自增主键
        is_auto_increment_pk = col.primary_key and col.autoincrement
        # 如果是自增主键，或者该列可以为空，或者有默认值，则设为可选
        required = not (is_auto_increment_pk or col.nullable or col.default is not None)
        fields[col.name] = (py_type, ... if required else None)
    CreateModel = create_model(f"{table.name.capitalize()}Create", **fields)
    ResponseModel = create_model(f"{table.name.capitalize()}Response", **fields)
    return CreateModel, ResponseModel

def _build_sync_router(engine, base_url, table_names, metadata, session_factory):
    Base = automap_base(metadata=metadata)
    Base.prepare(engine, reflect=True)
    router = APIRouter(prefix=base_url)

    for table_name in sorted(table_names):
        table = metadata.tables[table_name]
        cls = Base.classes.get(table_name)
        if cls is None:
            continue

        CreateModel, ResponseModel = _create_pydantic_models(table)
        PaginatedResponseModel = PaginatedResponse[ResponseModel]

        path = f"/{table_name}"

        def get_db():
            db = session_factory()
            try:
                yield db
            finally:
                db.close()

        @router.post(path, response_model=ResponseModel, status_code=201)
        def create(item: CreateModel, db: Session = Depends(get_db), _cls=cls, _table=table):
            obj = _cls(**item.model_dump(exclude_none=True))
            db.add(obj)
            db.commit()
            db.refresh(obj)
            return sqlalchemy_to_dict(obj, _table)

        @router.get(path, response_model=PaginatedResponseModel)
        def read_all(
            request: Request,
            skip: int = 0,
            limit: int = 100,
            db: Session = Depends(get_db),
            _cls=cls,
            _table=table,
        ):
            query_params = dict(request.query_params)
            filters = parse_query_filters(query_params, _table)
            stmt = select(_cls)
            for f in filters:
                stmt = stmt.where(f)
            total = db.scalar(select(func.count()).select_from(_cls))
            stmt = stmt.offset(skip).limit(limit)
            rows = db.scalars(stmt).all()
            items = [sqlalchemy_to_dict(row, _table) for row in rows]
            return {"items": items, "total": total, "skip": skip, "limit": limit}

        @router.get(f"{path}/{{item_id}}", response_model=ResponseModel)
        def read_one(item_id: Any, db: Session = Depends(get_db), _cls=cls, _table=table):
            obj = db.get(_cls, item_id)
            if not obj:
                raise HTTPException(404, "Not found")
            return sqlalchemy_to_dict(obj, _table)

        @router.put(f"{path}/{{item_id}}", response_model=ResponseModel)
        def update(
            item_id: Any,
            item: CreateModel,
            db: Session = Depends(get_db),
            _cls=cls,
            _table=table,
        ):
            obj = db.get(_cls, item_id)
            if not obj:
                raise HTTPException(404, "Not found")
            for k, v in item.model_dump(exclude_none=True).items():
                setattr(obj, k, v)
            db.commit()
            db.refresh(obj)
            return sqlalchemy_to_dict(obj, _table)

        @router.delete(f"{path}/{{item_id}}", status_code=204)
        def delete(item_id: Any, db: Session = Depends(get_db), _cls=cls):
            obj = db.get(_cls, item_id)
            if not obj:
                raise HTTPException(404, "Not found")
            db.delete(obj)
            db.commit()

    return router

def _build_async_router(engine, base_url, table_names, metadata, session_factory):
    Base = automap_base(metadata=metadata)
    # Use sync engine for reflection
    sync_engine = getattr(engine, 'sync_engine', None) or engine
    Base.prepare(sync_engine, reflect=True)
    router = APIRouter(prefix=base_url)

    for table_name in sorted(table_names):
        table = metadata.tables[table_name]
        cls = Base.classes.get(table_name)
        if cls is None:
            continue

        CreateModel, ResponseModel = _create_pydantic_models(table)
        PaginatedResponseModel = PaginatedResponse[ResponseModel]

        path = f"/{table_name}"

        async def get_db():
            async with session_factory() as session:
                yield session

        @router.post(path, response_model=ResponseModel, status_code=201)
        async def create(item: CreateModel, db: AsyncSession = Depends(get_db), _cls=cls, _table=table):
            obj = _cls(**item.model_dump(exclude_none=True))
            db.add(obj)
            await db.commit()
            await db.refresh(obj)
            return sqlalchemy_to_dict(obj, _table)

        @router.get(path, response_model=PaginatedResponseModel)
        async def read_all(
            request: Request,
            skip: int = 0,
            limit: int = 100,
            db: AsyncSession = Depends(get_db),
            _cls=cls,
            _table=table,
        ):
            query_params = dict(request.query_params)
            filters = parse_query_filters(query_params, _table)
            stmt = select(_cls)
            for f in filters:
                stmt = stmt.where(f)
            total_result = await db.execute(select(func.count()).select_from(_cls))
            total = total_result.scalar() or 0
            stmt = stmt.offset(skip).limit(limit)
            result = await db.execute(stmt)
            rows = result.scalars().all()
            items = [sqlalchemy_to_dict(row, _table) for row in rows]
            return {"items": items, "total": total, "skip": skip, "limit": limit}

        @router.get(f"{path}/{{item_id}}", response_model=ResponseModel)
        async def read_one(item_id: Any, db: AsyncSession = Depends(get_db), _cls=cls, _table=table):
            obj = await db.get(_cls, item_id)
            if not obj:
                raise HTTPException(404, "Not found")
            return sqlalchemy_to_dict(obj, _table)

        @router.put(f"{path}/{{item_id}}", response_model=ResponseModel)
        async def update(
            item_id: Any,
            item: CreateModel,
            db: AsyncSession = Depends(get_db),
            _cls=cls,
            _table=table,
        ):
            obj = await db.get(_cls, item_id)
            if not obj:
                raise HTTPException(404, "Not found")
            for k, v in item.model_dump(exclude_none=True).items():
                setattr(obj, k, v)
            await db.commit()
            await db.refresh(obj)
            return sqlalchemy_to_dict(obj, _table)

        @router.delete(f"{path}/{{item_id}}", status_code=204)
        async def delete(item_id: Any, db: AsyncSession = Depends(get_db), _cls=cls):
            obj = await db.get(_cls, item_id)
            if not obj:
                raise HTTPException(404, "Not found")
            await db.delete(obj)
            await db.commit()

    return router

def generate_crud_routes(
    database_url: Optional[str] = None,
    engine: Optional[Union[Engine, AsyncEngine]] = None,
    base_url: str = "/api",
    include_tables: Optional[List[str]] = None,
    exclude_tables: Optional[List[str]] = None,
):
    if not database_url and not engine:
        raise ValueError("Provide 'database_url' or 'engine'")
    if database_url and engine:
        raise ValueError("Provide only one of 'database_url' or 'engine'")

    is_async = False
    if database_url:
        if any(x in database_url for x in ("aiosqlite", "asyncpg", "aiomysql")):
            is_async = True
            engine = create_async_engine(database_url)
        else:
            engine = create_engine(
                database_url,
                connect_args={"check_same_thread": False} if "sqlite" in database_url else {}
            )
    else:
        is_async = isinstance(engine, AsyncEngine)

    metadata = MetaData()
    if is_async:
        import asyncio
        try:
            asyncio.run(metadata.reflect(bind=engine))
        except:
            # Fallback: use sync reflection if async fails
            sync_engine = getattr(engine, 'sync_engine', create_engine(str(engine.url).replace("+asyncpg", "").replace("+aiosqlite", "").replace("+aiomysql", "")))
            metadata.reflect(bind=sync_engine)
    else:
        metadata.reflect(bind=engine)

    all_table_names = set(metadata.tables.keys())
    if include_tables:
        table_names = set(include_tables) & all_table_names
    else:
        table_names = all_table_names
    if exclude_tables:
        table_names -= set(exclude_tables)
    if not table_names:
        warnings.warn("No tables to expose")
        table_names = []

    if is_async:
        session_factory = async_sessionmaker(engine, expire_on_commit=False)
        return _build_async_router(engine, base_url, list(table_names), metadata, session_factory)
    else:
        session_factory = sessionmaker(engine, autocommit=False, autoflush=False)
        return _build_sync_router(engine, base_url, list(table_names), metadata, session_factory)