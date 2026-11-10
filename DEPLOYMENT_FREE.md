# DaJuice 零成本部署指南

本方案使用现有的 LLM API 和 Tavily 账号，不接入第三方免费池。浏览器只持有管理员发放的 `User_Token`；`LLM_API_KEY`、`LLM_BASE_URL` 和 `TAVILY_API_KEY` 只放在 Render 服务端环境变量中。

## 1. 部署后端到 Render

1. 把项目根目录（包含 `Dockerfile`、`render.yaml`、`app/`、`v2/`）推送到 GitHub 仓库。不要提交 `.env`、`data/` 或任何真实 Key。
2. 在 Render 控制台选择 **New → Blueprint**，连接该仓库。Render 会读取 `render.yaml`，创建 `dajuice-api` Docker Web Service。
3. 在服务的 **Environment** 页面填写以下变量：

   | 变量 | 必填 | 说明 |
   | --- | --- | --- |
   | `LLM_API_KEY` | 是 | 现有大模型 API Key |
   | `LLM_BASE_URL` | 是 | 现有 OpenAI-compatible API 地址，例如服务商给出的 `/v1` 地址 |
   | `TAVILY_API_KEY` | 否 | 不填时联网案例功能自动降级为“未配置” |
   | `USER_TOKENS` | 是 | 管理员发放的 Token，多个用英文逗号分隔 |
   | `LLM_MODEL` | 否 | 默认 `deepseek-chat` |
   | `LLM_MAX_TOKENS` | 否 | 默认 `4000` |

   配额变量已由 `render.yaml` 提供默认值：每日 50 次判定、每日 5 次 Tavily、月度 1000/60。可以在 Render 中覆盖。
4. 部署完成后访问 `https://<你的服务>.onrender.com/health`，应返回 `{"status":"ok"}`。该地址是公开健康检查，不需要 Token。
5. 后端接口文档在 `https://<你的服务>.onrender.com/docs`。除 `/health` 和文档外，业务接口都需要 `Authorization: Bearer <User_Token>`。

### 本地 Docker 检查

```powershell
docker build -t dajuice-api .
docker run --rm -p 8000:8000 `
  -e LLM_API_KEY=... `
  -e LLM_BASE_URL=... `
  -e TAVILY_API_KEY=... `
  -e USER_TOKENS=... `
  dajuice-api
```

## 2. 部署前端到 Vercel

1. 在 Vercel 选择 **Add New → Project**，导入同一个仓库。
2. **Root Directory** 选择 `frontend`。
3. Framework Preset 保持 **Next.js**，Build Command 使用默认 `npm run build`。
4. 在 Environment Variables 添加：

   ```text
   NEXT_PUBLIC_API_BASE_URL=https://<你的 Render 服务>.onrender.com
   ```

   `NEXT_PUBLIC_API_BASE_URL` 是公开地址，不要放任何 API Key 或 User_Token。
5. 部署。打开 Vercel 域名后，会出现 Y2K 风格的 Token 激活页；输入管理员发放的 `User_Token` 才能进入学习界面。

如果后端域名后改了，必须更新 Vercel 环境变量并重新部署前端。浏览器端只保存 User_Token，不保存 LLM/Tavily Key。

## 3. 生成 User_Token

在项目根目录运行：

```powershell
python generate_token.py
python generate_token.py --count 5
```

把输出的随机字符串保存在密码管理器中，并将它们写入 Render 的 `USER_TOKENS`。例如：

```text
USER_TOKENS=dju_xxxxxxxx,dju_yyyyyyyy
```

Token 是访问凭证，不是账号密码。泄露后从 `USER_TOKENS` 删除该值并重新部署即可吊销；已建立的会话会在服务重启后失效。

## 4. 免费方案的现实限制

### Render 冷启动

Render 免费 Web Service 在 15 分钟无请求后会休眠。休眠后的第一个请求通常需要约 50 秒才能完成冷启动，期间前端会显示网络等待或超时提示。建议在前端首次打开时预留等待时间，不要连续点击。

### 用 UptimeRobot 保活

1. 注册 UptimeRobot 免费账号。
2. 新建 HTTP(s) Monitor，URL 填 `https://<你的服务>.onrender.com/health`。
3. Interval 选 10 分钟，Method 选 GET。
4. 保存后确认状态为 Up。

这能降低演示时遇到休眠的概率，但不能保证 Render 永远不休眠，也不代表免费额度无限。不要用高频脚本轰炸服务。

### 数据持久化

Render 免费层默认磁盘是临时的。`data/user_quota.json`、`data/mistakes/mistakes.json` 和 `data/hot_cases.json` 在重启、重新部署或实例迁移后可能丢失。当前实现适合演示和小规模试用：

- 配额会重置；
- 错题本会丢失；
- 热点案例缓存会重建。

正式上线前应换成托管数据库或 Render 持久磁盘，并保证只有一个实例。当前配额锁是单进程内存锁，多实例之间不会共享计数。

### 其他限制

- Render 免费实例资源有限，长文本和联网检索会更慢。
- 不要在 Vercel 或浏览器暴露 `LLM_API_KEY`、`LLM_BASE_URL` 的真实值；前端只使用 `NEXT_PUBLIC_API_BASE_URL`。
- `USER_TOKENS` 是服务端秘密，不要写进 README、YAML 明文或 Git 历史。
- `/health` 必须保持公开，否则 UptimeRobot 无法探活。

## 5. 最小验收清单

```text
[ ] Render /health 返回 200
[ ] 不带 Authorization 请求 /library/books 返回 401
[ ] 带正确 User_Token 请求 /library/books 返回 200
[ ] 错误 User_Token 返回 401
[ ] 把 DAILY_DIAGNOSIS_LIMIT 临时设为 0，/api/diagnose 返回 429
[ ] Vercel 首次打开出现 Token 激活页
[ ] 输入 Token 后能加载科目页
[ ] 清除 localStorage 后重新打开会回到激活页
```
