# OpenDF 具身采标平台

本地闭环的具身智能数据采集与标注平台。后端是 FastAPI + SQLite，前端是 Vue 3 + Element Plus，按若依风格布局。不需要 MySQL、Redis 或 Docker。

## 后端

```bash
cd backend
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python run.py
```

接口文档：http://localhost:8000/docs

数据库文件是 `backend/opendf.db`。视频和轨迹写到 `backend/storage/raw/`，导出包写到 `backend/storage/export/`。

生成一条模拟样本（正弦末端轨迹，夹爪在 3–7 秒闭合，并带一段对齐测试视频）：

```bash
curl -X POST http://localhost:8000/api/v1/sessions/mock-sample
```

## 前端

```bash
cd frontend
npm install
npm run dev
```

打开 http://127.0.0.1:4280 。开发服务器把 `/api` 和 `/storage` 代理到 `127.0.0.1:8000`。

演示账号密码都是 `opendf`：`admin`（超级管理员）、`collector`（采集人员）、`qa`（标注与质检员）。首页可以直接进入，不必先登录。

## 演示路径

1. 首页查看「多源异构数采平台」六步流程和四张指标卡。
2. 采集会话里点击「生成模拟样本」。
3. 打开标注模块：播放视频，红色游标沿波形移动；点击波形跳转；拖拽区间后选择 Approach / Grasp / Place。
4. 在审核模块通过或驳回切片。
5. 在数据模块导出 LeRobot 包并下载。
