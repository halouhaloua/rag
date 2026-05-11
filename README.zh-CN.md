## 📖 项目简介

zq-platform 是一个功能完善的企业级后台管理系统解决方案，采用前后端分离架构。提供两种后端选择：Django 5.2 + Django Ninja 或 FastAPI + SQLAlchemy 异步 ORM，前端基于 Vue 3 + Vben Admin + Element Plus 打造现代化的管理界面。

### ✨ 核心特性

- 🎯 **完整的 RBAC 权限系统** - 用户、角色、权限、部门、岗位多维度权限控制
- 🔐 **JWT 认证机制** - 安全的 Token 认证，支持 Access Token 和 Refresh Token
- 📊 **系统监控** - 服务器监控、Redis 监控、数据库监控，实时掌握系统状态
- 📁 **文件管理** - 完善的文件上传、下载、预览功能
- 📝 **操作日志** - 详细的登录日志和操作审计
- 🗂️ **数据字典** - 灵活的字典管理，支持多级分类
- ⏰ **任务调度** - 基于 APScheduler 的定时任务管理
- 🔌 **WebSocket 支持** - 实时通信能力
- 🌐 **多数据库支持** - MySQL、PostgreSQL、SQL Server、SQLite
- 🎨 **现代化 UI** - 响应式设计，支持暗黑模式
- 📦 **Monorepo 架构** - 基于 pnpm workspace 的前端工程化方案

## 🏗️ 技术栈

### 后端技术

**FastAPI 后端 (backend-fastapi)**
- **核心框架**: FastAPI 0.115+
- **ORM**: SQLAlchemy 2.0+ (异步)
- **数据库**: PostgreSQL 16+
- **迁移**: Alembic
- **认证**: JWT
- **缓存**: Redis
- **Python**: 3.12+

### 前端技术

- **核心框架**: Vue 3.x
- **构建工具**: Vite 5.x
- **UI 组件库**: Element Plus
- **状态管理**: Pinia
- **路由**: Vue Router
- **HTTP 客户端**: Axios
- **工具库**: VueUse, dayjs, lodash-es
- **代码规范**: ESLint, Prettier, Stylelint
- **包管理**: pnpm 10.14.0
- **Monorepo**: Turbo

## 📁 项目结构

```
zq-platform/
├── backend-fastapi/         # FastAPI 后端（可选）
│   ├── app/                # 核心应用模块
│   ├── core/               # 核心业务模块
│   ├── scheduler/          # 定时任务模块
│   ├── scripts/            # 工具脚本
│   ├── alembic/            # 数据库迁移
│   ├── env/                # 环境配置
│   ├── requirements.txt    # Python 依赖
│   └── main.py            # 应用入口
│
└── web/                    # Vue 前端 (Monorepo)
    ├── apps/
    │   └── web-ele/        # Element Plus 版本主应用
    │       ├── src/
    │       │   ├── api/    # API 接口
    │       │   ├── views/  # 页面组件
    │       │   ├── router/ # 路由配置
    │       │   └── store/  # 状态管理
    │       └── package.json
    ├── packages/           # 共享包
    │   ├── @core/          # 核心包
    │   ├── effects/        # 副作用包
    │   ├── hooks/          # Hooks
    │   ├── icons/          # 图标
    │   ├── locales/        # 国际化
    │   ├── stores/         # 状态管理
    │   └── utils/          # 工具函数
    ├── internal/           # 内部工具
    └── package.json        # 根配置
```

## 🚀 快速开始

### 环境要求

- **后端**
  - Python >= 3.10
  - MySQL >= 5.7 / PostgreSQL >= 12 / SQL Server
  - Redis >= 5.0

- **前端**
  - Node.js >= 20.10.0
  - pnpm >= 9.12.0

### 后端安装
1. **进入目录**
```bash
cd zq-platform/backend
```

1. **创建虚拟环境**
```bash
conda create -n zq-fastapi python=3.12
conda activate zq-fastapi
```

1. **安装依赖**
```bash
pip install -r requirements.txt
```

1. **配置环境变量**
```bash
cp env/example.env env/dev.env
# 编辑 env/dev.env 配置数据库连接
```

1. **数据库迁移**
```bash
alembic revision --autogenerate -m "init tables"
alembic upgrade head

# 导入初始数据（可选）
python scripts/loaddata.py db_init.json
```

6. **启动服务**
```bash
python main.py
# 或
uvicorn main:app --reload --host 0.0.0.0 --port 8000
```

7. **访问 API 文档**
- Swagger UI: http://localhost:8000/docs
- ReDoc: http://localhost:8000/redoc

### 前端安装

1. **进入前端目录**
```bash
cd zq-platform/web
```

2. **安装依赖**
```bash
pnpm install
```

3. **配置环境变量**
```bash
cd apps/web-ele
cp .env.development .env
# 编辑 .env 文件，配置后端 API 地址
```

4. **启动开发服务器**
```bash
# 在 web 根目录下
pnpm dev
```

5. **构建生产版本**
```bash
pnpm build:ele
```

## 📝 默认账号

初始化数据后，可使用以下账号登录：

- 账号: `superadmin`
- 密码: 请查看 `123456` 或联系管理员

## 🔧 主要功能模块

### 系统管理
- **用户管理**: 用户的增删改查、密码重置、状态管理
- **角色管理**: 角色权限分配、数据权限控制
- **权限管理**: 接口权限、按钮权限细粒度控制
- **部门管理**: 树形部门结构管理
- **岗位管理**: 岗位信息维护
- **菜单管理**: 动态菜单配置、路由管理
- **字典管理**: 系统字典维护

### 系统监控
- **服务器监控**: CPU、内存、磁盘、网络实时监控
- **Redis 监控**: Redis 性能指标、键值管理
- **数据库监控**: 数据库连接、性能监控
- **登录日志**: 用户登录记录、IP 地理位置

### 任务调度
- **定时任务**: Cron 表达式配置
- **任务日志**: 执行历史、结果查看
- **任务管理**: 启动、停止、立即执行

### 文件管理
- **文件上传**: 支持多文件上传
- **文件预览**: 图片、文档在线预览
- **文件下载**: 批量下载功能

## 🔐 API 文档

**FastAPI 后端**
- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

## 🛠️ 开发指南

### 后端开发
## 开发指南

### 新建业务模块

按照以下步骤创建新的业务模块（以 `example` 为例）：

#### 1. 创建模块目录

```bash
mkdir -p core/example
touch core/example/__init__.py
touch core/example/model.py
touch core/example/schema.py
touch core/example/service.py
touch core/example/api.py
```

#### 2. 定义模型 (model.py)

```python
from sqlalchemy import Column, String, Boolean
from app.base_model import BaseModel

class Example(BaseModel):
    __tablename__ = "core_example"
    
    name = Column(String(100), nullable=False, comment="名称")
    description = Column(String(500), comment="描述")
    is_active = Column(Boolean, default=True, comment="是否激活")
```

#### 3. 定义 Schema (schema.py)

```python
from pydantic import BaseModel, ConfigDict
from typing import Optional
from datetime import datetime

class ExampleBase(BaseModel):
    name: str
    description: Optional[str] = None
    is_active: bool = True

class ExampleCreate(ExampleBase):
    pass

class ExampleUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    is_active: Optional[bool] = None

class ExampleResponse(ExampleBase):
    id: str
    sort: int = 0
    is_deleted: bool = False
    sys_create_datetime: Optional[datetime] = None
    sys_update_datetime: Optional[datetime] = None
    
    model_config = ConfigDict(from_attributes=True)
```

#### 4. 定义服务 (service.py)

```python
from app.base_service import BaseService
from core.example.model import Example
from core.example.schema import ExampleCreate, ExampleUpdate

class ExampleService(BaseService[Example, ExampleCreate, ExampleUpdate]):
    model = Example
```

#### 5. 定义 API (api.py)

```python
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from app.database import get_db
from app.base_schema import PaginatedResponse, ResponseModel
from core.example.schema import ExampleCreate, ExampleUpdate, ExampleResponse
from core.example.service import ExampleService

router = APIRouter(prefix="/example", tags=["示例管理"])

@router.post("", response_model=ExampleResponse, summary="创建")
async def create(data: ExampleCreate, db: AsyncSession = Depends(get_db)):
    return await ExampleService.create(db=db, data=data)

@router.get("", response_model=PaginatedResponse[ExampleResponse], summary="获取列表")
async def get_list(
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=20, ge=1, le=100, alias="pageSize"),
    db: AsyncSession = Depends(get_db)
):
    items, total = await ExampleService.get_list(db, page=page, page_size=page_size)
    return PaginatedResponse(items=items, total=total)

@router.get("/{record_id}", response_model=ExampleResponse, summary="获取详情")
async def get_by_id(record_id: str, db: AsyncSession = Depends(get_db)):
    result = await ExampleService.get_by_id(db, record_id=record_id)
    if not result:
        raise HTTPException(status_code=404, detail="记录不存在")
    return result

@router.put("/{record_id}", response_model=ExampleResponse, summary="更新")
async def update(record_id: str, data: ExampleUpdate, db: AsyncSession = Depends(get_db)):
    result = await ExampleService.update(db, record_id=record_id, data=data)
    if not result:
        raise HTTPException(status_code=404, detail="记录不存在")
    return result

@router.delete("/{record_id}", response_model=ResponseModel, summary="删除")
async def delete(record_id: str, db: AsyncSession = Depends(get_db)):
    success = await ExampleService.delete(db, record_id=record_id)
    if not success:
        raise HTTPException(status_code=404, detail="记录不存在")
    return ResponseModel(message="删除成功")
```

#### 6. 注册路由

在 `core/router.py` 中添加：

```python
from core.example.api import router as example_router

router.include_router(example_router)
```

#### 7. 生成数据库迁移

```bash
alembic revision --autogenerate -m "add example table"
alembic upgrade head
```

## 核心功能

### BaseModel

所有模型继承自 `BaseModel`，自动包含以下字段：

- `id`: UUID 主键
- `sort`: 排序字段
- `is_deleted`: 软删除标记
- `sys_create_datetime`: 创建时间
- `sys_update_datetime`: 更新时间
- `sys_creator_id`: 创建人ID
- `sys_modifier_id`: 修改人ID

### BaseService

提供通用 CRUD 操作：

- `create()`: 创建记录
- `get_by_id()`: 根据ID获取
- `get_list()`: 分页查询
- `update()`: 更新记录
- `delete()`: 删除记录（软删除/硬删除）
- `check_unique()`: 唯一性检查
- `export_to_excel()`: 导出Excel
- `import_from_excel()`: 导入Excel

### 缓存支持

使用 Redis 缓存，继承 `CacheService` 获得缓存功能：

```python
from app.cache_service import CacheService

class ExampleService(CacheService[Example, ExampleCreate, ExampleUpdate]):
    model = Example
    cache_prefix = "example"
    cache_ttl = 3600  # 1小时
```

## 环境配置

项目支持多环境配置：

- `env/dev.env`: 开发环境
- `env/uat.env`: UAT环境
- `env/prod.env`: 生产环境

通过环境变量 `ENV` 切换：

```bash
export ENV=prod  # 使用生产环境配置
python main.py
```

## API 规范

### 响应格式

成功响应：

```json
{
  "code": 200,
  "message": "success",
  "data": {...}
}
```

分页响应：

```json
{
  "items": [...],
  "total": 100
}
```

错误响应：

```json
{
  "detail": "错误信息"
}
```

### 路由命名规范

- 使用小写短横线：`/api/core/user-profile`
- 静态路由在前：`/api/core/menu/check/name`
- 动态路由在后：`/api/core/menu/{menu_id}`


### 前端开发

1. **添加新页面**
   - 在 `src/views/` 创建页面组件
   - 在 `src/router/routes/modules/` 添加路由
   - 在 `src/api/` 添加接口定义

2. **组件开发规范**
   - 使用 Element Plus 组件
   - 优先使用 Tailwind CSS
   - 支持暗黑模式
   - 图标从 `@vben/icons` 导入

## 📦 部署
1. **后端部署**
   - 使用 Gunicorn + Nginx
   - 配置 Supervisor 进程守护
   - 配置 SSL 证书

2. **前端部署**
   - 执行 `pnpm build` 构建
   - 将 `dist` 目录部署到 Nginx
   - 配置反向代理

