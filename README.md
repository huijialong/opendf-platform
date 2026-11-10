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

`python run.py` 默认监听 `http://127.0.0.1:8000`，终端打印 `Uvicorn running on http://127.0.0.1:8000`。第一次启动会创建 `opendf.db`。即使仓库里还没有 `storage/`，启动时也会创建 `storage/raw` 和 `storage/export`。

主机和端口来自 `OPENDF_HOST`、`OPENDF_PORT`（默认 `127.0.0.1` 和 `8000`）：

```bash
OPENDF_PORT=8001 python run.py
OPENDF_HOST=0.0.0.0 OPENDF_PORT=8000 python run.py
```

端口已被占用时（macOS 上常见 Errno 48，Linux 上常见 Errno 98），进程会说明如何换端口，例如 `OPENDF_PORT=8001 python run.py`，并以非 0 状态退出。

其他可选环境变量：

| 变量 | 默认 | 作用 |
| --- | --- | --- |
| `OPENDF_HOST` | `127.0.0.1` | 监听地址 |
| `OPENDF_PORT` | `8000` | 监听端口 |
| `OPENDF_API_PREFIX` | `/api/v1` | API 前缀 |
| `OPENDF_CORS_ORIGINS` | `*` | 允许的浏览器来源，逗号分隔 |
| `OPENDF_APP_NAME` | OpenDF 具身智能采标平台 | 服务名称 |
| `OPENDF_DATA_DIR` | 后端目录（即 `opendf.db` 与 `storage/` 所在处） | 把数据库和对象存储放到别的目录；生产镜像设为 `/data` |

接口文档：http://127.0.0.1:8000/docs

数据库文件是 `backend/opendf.db`。视频和轨迹写到 `backend/storage/raw/`，导出包写到 `backend/storage/export/`。LeRobot 导出是 v2.1 目录：`data/chunk-000/episode_XXXXXX.parquet`（数值列与 `meta/info.json` 一致，为 float32）、`meta/info.json`（以及 episodes、tasks、stats，含视频特征统计）、`videos/chunk-000/observation.images.rgb/episode_XXXXXX.mp4`。有 ffmpeg 时，非 H.264 或非 MP4 的视频会转成 H.264 yuv420p，缺视频的回合会补一段黑屏；`info.json` 里的编码来自写出文件的探测结果。没有 ffmpeg 时，只原样打包已经是 MP4 的文件，并记录探测到的编码，不会把别的容器标成 H.264。写出 parquet 需要 `pandas` 和 `pyarrow`；两者缺一时导出仍会返回下载地址，并在响应和 `info.json` 里带上 CSV 回退说明。

生成一条模拟样本（正弦末端轨迹，夹爪在 3–7 秒闭合，并带一段对齐测试视频）：

```bash
curl -X POST http://127.0.0.1:8000/api/v1/sessions/mock-sample
```

## 前端

```bash
cd frontend
npm install
npm run dev
```

打开 http://127.0.0.1:4280 。开发服务器把 `/api` 和 `/storage` 代理到 `127.0.0.1:8000`。如果改了 `OPENDF_PORT`，需要同步改 `frontend/vite.config.js` 里的代理目标。

演示账号密码都是 `opendf`：`admin`（超级管理员）、`collector`（采集人员）、`qa`（标注与质检员）。首页可以直接进入，不必先登录。

## 演示路径

1. 首页查看「多源异构数采平台」六步流程和四张指标卡。
2. 采集会话里点击「生成模拟样本」。
3. 打开标注模块：播放视频，红色游标沿波形移动；点击波形跳转；拖拽区间后选择 Approach / Grasp / Place。
4. 在审核模块通过或驳回切片。
5. 在数据模块导出 LeRobot v2.1 包并下载。

## 生产部署（vpsjy / Docker）

生产目录是 vpsjy 上的 `/data/opendf`。前后端打成两个镜像，用同一份 `docker-compose.yml` 拉起，项目名固定为 `opendf`，不会碰到这台机器上其他容器。只有前端 nginx 对外发布端口，而且只绑在本机回环地址：`127.0.0.1:18090`。公网入口是 Cloudflare Tunnel `jyvps` 上的 `opendf.20000427.xyz`，前面加了 Cloudflare Access（邮箱一次性验证码，会话 7 天）。

首次或更新部署，在服务器上执行：

```bash
cd /data/opendf
./deploy.sh
```

`./deploy.sh` 会从 Git 拉取指定引用（默认 `main`）、构建镜像、只重启 `opendf` 这个 compose 项目，并在还没有带视频的会话时自动调用一次 `POST /api/v1/sessions/mock-sample`。指定分支或 commit：

```bash
./deploy.sh deploy/vpsjy-docker
```

运行时数据在 `/data/opendf/data/`（`opendf.db` 和 `storage/`），已被 gitignore，更新代码时不会被覆盖。后端镜像内安装了 ffmpeg / ffprobe，用于模拟样本和 LeRobot 导出。

本机验证：

```bash
curl -sI http://127.0.0.1:18090/
curl -s http://127.0.0.1:18090/api/v1/dashboard/stats
```

前端路由 `/docs` 是操作手册，因此 FastAPI Swagger 不挂在 `/docs`，需要看接口文档时打开 `/redoc` 或 `/openapi.json`。
