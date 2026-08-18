# SC-Link 供应链协同分析中台

B300 服务器供应链上下游协同管理系统(内部 3-5 人)。设计方案见 `供应链中台设计方案.html`(v0.2)。

## 端口约定

| 服务 | 端口 |
|---|---|
| MySQL(Docker) | 3306 |
| 后端 FastAPI | 8100 |
| 前端 Vite | 5573 |

## 目录结构

```
B300/
├── backend/        # Python FastAPI 后端
├── frontend/       # Vue 3 + TS + Tailwind 前端
├── docker-compose.yml   # 本地 MySQL 8(开发环境)
└── 供应链中台设计方案.html
```

## 本地开发

1. 启动数据库:`docker compose up -d`
2. 后端: `cd backend && python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt && uvicorn app.main:app --reload --port 8100`
3. 前端: `cd frontend && npm install && npm run dev`(5573)

默认管理员账号:`admin`(密码见 backend/.env 中 ADMIN_PASSWORD,首次登录后请修改)。

## 约定

- 起服务前先 `lsof -nP -iTCP:<端口> -sTCP:LISTEN` 检查端口冲突
- 密钥(Gemini API key 等)只放 `backend/.env`(已 gitignore),绝不提交
