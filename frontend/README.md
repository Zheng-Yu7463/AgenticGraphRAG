# AgenticGraphRAG Frontend

Vue 3 + Vite + TypeScript 脚手架，后续用于对接 FastAPI LangGraph 后端。目前仅保留默认示例页面，可在此基础上接入 `/api/v1/chat` 等接口。

## 环境要求
- Node.js 20.19+ 或 22.12+
- 推荐 VS Code + Volar（关闭 Vetur）

## 常用命令
```bash
npm install          # 安装依赖
npm run dev          # 本地开发
npm run build        # 生产构建
npm run lint         # ESLint + Oxlint
npm run test:unit    # Vitest
npm run test:e2e     # Playwright（需先 npx playwright install）
```

## 开发提示
- API Base URL 可通过 Vite 环境变量自行添加（例如 `.env.local` 中配置 `VITE_API_BASE=http://localhost:8000`），然后在请求封装里读取。
- 现有页面是 Vite 默认模版，接入后端时可直接替换 `src/views/HomeView.vue`、`src/App.vue` 等。
