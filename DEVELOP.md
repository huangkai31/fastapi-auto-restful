# FastAPI 自动 CRUD API 生成器开发与使用指南

本文档介绍如何使用 `fastapi-auto-crud` —— 一个能**自动为数据库表生成完整 RESTful CRUD API** 的 FastAPI 扩展库。支持同步/异步、分页、查询过滤、外键嵌套响应，并提供完整的开发、测试、打包流程。使用现代工具链 `uv` 进行高效开发。

---

## 一、核心功能

✅ **全自动反射**：只需提供数据库连接，自动为所有表生成 API  
✅ **同步 & 异步支持**：兼容 SQLAlchemy 2.0（`sqlite`/`postgresql`/`mysql`）  
✅ **分页响应**：返回 `{"items": [...], "total": N, "skip": 0, "limit": 100}`  
✅ **查询过滤**：支持 `?name=John&age__gt=18&email__ilike=%@gmail.com`  
✅ **外键嵌套**：自动加载关联对象，返回嵌套 JSON  
✅ **零代码集成**：返回 `APIRouter`，可挂载到任意 FastAPI 应用  
✅ **可打包发布**：支持 `pip install` 安装

---

## 二、项目结构

```
fastapi-auto-crud/
├── fastapi_auto_crud/       # 核心代码
│   ├── __init__.py
│   ├── auto_router.py      # CRUD 路由生成器（支持 sync/async）
│   ├── query_parser.py     # 查询参数解析
│   └── schemas.py          # 分页响应模型
├── tests/                  # 测试套件
│   ├── conftest.py
│   ├── test_sync.py
│   └── test_async.py
├── examples/               # 使用示例
│   ├── sync_example.py
│   └── async_example.py
├── pyproject.toml          # 项目元数据与依赖
├── README.md
└── .github/workflows/ci.yml # GitHub CI 配置
```

---

## 三、使用方式

### 1. 安装

```bash
pip install fastapi-auto-crud
```

> 或从源码安装（开发模式）：
> ```bash
> pip install -e .
> ```

### 2. 基本用法（同步）

```python
# main.py
from fastapi import FastAPI
from fastapi_auto_crud import generate_crud_routes

app = FastAPI()

# 自动生成所有表的 CRUD API，挂载在 /api 前缀下
app.include_router(
    generate_crud_routes(
        database_url="sqlite:///./app.db",
        base_url="/api",
        exclude_tables=["alembic_version"]  # 可选：排除某些表
    )
)
```

### 3. 高级用法（传入已有 Engine）

```python
from sqlalchemy import create_engine
from fastapi_auto_crud import generate_crud_routes

engine = create_engine("postgresql://user:pass@localhost/mydb", pool_size=10)

app.include_router(
    generate_crud_routes(engine=engine, base_url="/api/v1")
)
```

### 4. 异步用法

```python
app.include_router(
    generate_crud_routes(
        database_url="sqlite+aiosqlite:///./async.db",
        base_url="/api"
    )
)
```

> 支持的异步 URL 前缀：
> - `sqlite+aiosqlite://`
> - `postgresql+asyncpg://`
> - `mysql+aiomysql://`

---

## 四、API 特性

### 1. 自动生成的端点（以 `/users` 为例）

| 方法 | 路径 | 功能 |
|------|------|------|
| POST | `/api/users/` | 创建用户 |
| GET | `/api/users/` | 分页查询（支持过滤） |
| GET | `/api/users/{id}` | 获取单个用户（含外键嵌套） |
| PUT | `/api/users/{id}` | 更新用户 |
| DELETE | `/api/users/{id}` | 删除用户 |

### 2. 分页响应格式

```json
{
  "items": [
    {"id": 1, "name": "Alice", "email": "alice@example.com"},
    {"id": 2, "name": "Bob", "email": "bob@example.com"}
  ],
  "total": 2,
  "skip": 0,
  "limit": 100
}
```

### 3. 查询过滤语法

| 示例 | 说明 |
|------|------|
| `?name=Alice` | 等于 |
| `?age__gt=18` | 大于 |
| `?age__ge=18` | 大于等于 |
| `?name__like=%Ali%` | 模糊匹配 |
| `?name__ilike=%ali%` | 忽略大小写模糊匹配 |

---

## 五、开发与测试（使用 `uv`）

> **`uv` 是由 Astral 开发的超快 Python 工具链，用于替代 pip/virtualenv**

### 1. 安装 `uv`

```bash
# Linux / macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows (PowerShell)
irm https://astral.sh/uv/install.ps1 | iex
```

验证：
```bash
uv --version
```

### 2. 开发流程

```bash
# 克隆或创建项目
git clone https://github.com/yourname/fastapi-auto-crud
cd fastapi-auto-crud

# 创建虚拟环境
uv venv

# 安装项目（开发模式）
uv pip install -e .[dev]

# 运行测试
uv run pytest

# 启动示例（同步）
uv run uvicorn examples.sync_example:app --reload

# 启动示例（异步）
uv run uvicorn examples.async_example:app --reload
```

### 3. `uv` 优势

- **速度极快**：依赖解析比 pip 快 10-100 倍
- **自动隔离**：`uv run` 自动使用项目虚拟环境
- **准确可靠**：基于 PubGrub 依赖解析算法

---

## 六、测试套件

### 1. 同步测试

```python
# tests/test_sync.py
def test_sync_read_all(sync_engine):
    app = FastAPI()
    app.include_router(generate_crud_routes(engine=sync_engine))
    client = TestClient(app)
    resp = client.get("/api/users/")
    assert resp.json()["total"] == 1
```

### 2. 异步测试

```python
# tests/test_async.py
@pytest.mark.asyncio
async def test_async_create(async_engine):
    app = FastAPI()
    app.include_router(generate_crud_routes(engine=async_engine))
    async with AsyncClient(app=app, base_url="http://test") as ac:
        resp = await ac.post("/api/users/", json={"name": "Bob"})
        assert resp.status_code == 201
```

运行测试：
```bash
uv run pytest tests/ -v
```

---

## 七、打包与发布

### 1. 构建分发包

```bash
uv pip install build
uv run python -m build
```

生成文件：
- `dist/fastapi_auto_crud-0.3.0-py3-none-any.whl`
- `dist/fastapi-auto-crud-0.3.0.tar.gz`

### 2. 发布到 PyPI（可选）

```bash
uv pip install twine
uv run twine upload dist/*
```

---

## 八、注意事项

1. **外键嵌套**：要求数据库中外键关系正确定义
2. **主键假设**：默认使用第一个主键列（支持单列主键）
3. **类型推断**：简化版映射（int/str/bool/float），特殊类型可扩展
4. **生产安全**：默认无认证，建议在路由前加 middleware（如 JWT）
5. **异步反射**：SQLAlchemy 异步反射有限，库内部已做兼容处理

---

## 九、示例：完整应用

```python
# app.py
from fastapi import FastAPI
from fastapi_auto_crud import generate_crud_routes

app = FastAPI(title="Auto CRUD API")

# 支持 URL 或 Engine
app.include_router(
    generate_crud_routes(
        database_url="postgresql://user:pass@localhost/myapp",
        base_url="/api/v1",
        include_tables=["users", "orders"]  # 只暴露指定表
    )
)

@app.get("/")
def root():
    return {"docs": "/docs"}
```

启动：
```bash
uv run uvicorn app:app --reload
```

访问：http://localhost:8000/docs

---

## 十、未来扩展建议

- 添加 JWT 认证中间件
- 支持自定义字段校验
- 添加 OpenAPI tag 分组优化
- 支持批量操作（bulk create/update）
- 集成 Alembic 迁移



---

**作者**：huangkai  
**版本**：0.3.0  
**许可证**：MIT  
**仓库**：https://github.com/huangkai31/fastapi-auto-crud