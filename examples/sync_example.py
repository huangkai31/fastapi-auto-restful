# examples/sync_example.py
from fastapi import FastAPI
from fastapi_auto_restful import generate_crud_routes
import os

# 创建数据库文件（如果存在则先删除，确保结构正确）
db_path = "./example.db"
# 先删除现有数据库文件，确保使用最新的表结构
if os.path.exists(db_path):
    os.remove(db_path)

# 初始化一个简单数据库（仅用于演示）
from sqlalchemy import create_engine, text
engine = create_engine(f"sqlite:///{db_path}")
with engine.connect() as conn:
    conn.execute(text("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT 
        )
    """))
    conn.commit()

app = FastAPI(title="Sync Auto CRUD Example")

# 挂载自动生成的 CRUD 路由
app.include_router(
    generate_crud_routes(
        database_url=f"sqlite:///{db_path}",
        base_url="/api",
    )
)

# 可选：根路径提示
@app.get("/")
def root():
    return {"message": "Go to /docs to see the API"}