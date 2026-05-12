# XFAcuorsesystem（学校智能排课）

　　本仓库为 GitHub 项目 **[XFAcuorsesystem](https://github.com/lamasaga/XFAcuorsesystem)** 的源码快照，用于在服务器上部署「前后端分离」的排课系统：Python **FastAPI** 后端 + **Vue 3 + Vite** 前端。克隆后目录名一般为 `XFAcuorsesystem`。

## 仓库内包含什么

- `backend/`：API 与排课引擎（上线必需）
- `frontend/`：管理端 Web 界面源码（上线前需 `npm run build` 生成静态资源）
- `backend/.env.example`：环境变量模板
- `学校的要求.md`：校方需求说明（供实施对照，不参与构建）

　　设计类文档、桌面端（Electron）、本地打包脚本、Obsidian 配置等**不在本仓库**，以减轻部署克隆体积。

## 服务器上获取代码

```bash
git clone https://github.com/lamasaga/XFAcuorsesystem.git
cd XFAcuorsesystem
```

## 运行说明

　　数据库、依赖安装与进程启动步骤见 **`backend/README.md`**。前端开发与构建见 **`frontend/package.json`** 中的脚本（典型流程：`npm install` → `npm run build`，再将 `frontend/dist` 交由 Nginx 等托管并与后端 API 同源或反向代理）。

---

*业务与算法说明请参阅校方文档与内部资料；本 README 仅服务仓库部署。*
