# Windows Quick Start：NapCat 配置、Token 获取与测试

适用场景：Lumenbay 和 NapCat 都运行在同一台 Windows 10/11 电脑上。先用**获授权的测试微信群、测试 QQ 群及已有 QQ 群相册**验证，暂不用于长期无人值守。

## 1. 安装与启动 NapCat

如果尚未安装，推荐按 [NapCatQQ Desktop 官方 Windows 指南](https://napneko.github.io/NapCatQQ-Desktop/docs/)：

1. [安装 NapCatQQ Desktop](https://napneko.github.io/NapCatQQ-Desktop/docs/installation/)。
2. 在「组件」页安装 QQ 和 **NapCat**；在「机器人」中创建并启动本机 QQ Bot。
3. 使用手机 QQ 扫码、确认登录；确认 Bot 显示已登录。目标 QQ 账号必须在测试群中，且有向该群相册上传图片的权限。

已经通过 NapCat Shell 安装的用户可以继续使用现有部署，无须改装 Desktop。Shell 用户按 [NapCat 官方 WebUI 配置指南](https://napneko.github.io/config/basic) 打开 WebUI；启动日志中的 WebUI 地址通常类似 `http://127.0.0.1:6099/webui?token=...`。

> **两个 Token 不同：**
>
> - **WebUI Token / 密码**：仅用于登录管理页面，WebUI 默认端口 **6099**（以实际日志为准）。
> - **OneBot HTTP Token**：HTTP API 的鉴权密钥，由**HTTP 服务器连接**单独配置或生成；Lumenbay 必须使用这个 Token，示例端口 **3000**。
>
> 不要将 WebUI Token 写入 `LUMENBAY_NAPCAT_TOKEN`。Token 不是从 Lumenbay 或 mise 生成的。

## 2. 创建 HTTP 服务器，获取 OneBot Token

### NapCatQQ Desktop（推荐）

1. 打开「机器人」→ 目标 Bot 的**配置** →「连接」。
2. 在新增连接中选择 **HTTP 服务器**（不要选 HTTP 客户端、WebSocket 服务器）。
3. 填写下表：

| 配置项 | 建议值 | 用途 |
| --- | --- | --- |
| 连接名称 | `lumenbay-http` | 当前 Bot 内唯一 |
| Host / 监听 IP | `127.0.0.1` | 只允许本机连接 |
| Port / 端口 | `3000` | Lumenbay 连接的 OneBot 端口 |
| Path / 监听路径 | `/` | API 默认路径 |
| 消息上报格式 | `Array`（默认） | 此项目只调用 HTTP API |
| **鉴权 Token** | **保留自动生成的随机值，复制并妥善保存** | 供 Lumenbay 使用 |
| 启用此连接 | **开启** | 否则 API 不会监听 |

4. 点击「**保存连接**」，再点击 Bot 配置页右上角的「**保存**」。必要时重启 Bot。
5. 以后需要重新获取 Token：回到**该 HTTP 服务器连接的配置**，查看鉴权 Token。更改 Token 后同步更新本机环境变量。

> Shell WebUI 用户：打开 WebUI「网络配置」→「新建」→ **HTTP 服务端**；设置 `host=127.0.0.1`、`port=3000`、`enable=true` 和一个随机 `token`，保存并启用。**不要复制 WebUI 登录 Token 作为 OneBot Token**。请参照 [NapCat 官方配置说明](https://napneko.github.io/config/basic)。

## 3. 在 PowerShell 检查 API 和 Token

在新的 PowerShell 中执行（替换端口以匹配第 2 步）：

```powershell
# 输入的是 HTTP 服务器连接的 OneBot Token，不是 WebUI 密码
$env:LUMENBAY_NAPCAT_TOKEN = Read-Host "OneBot HTTP Token"

# 只检查 TCP 端口；成功不代表鉴权正确
Test-NetConnection 127.0.0.1 -Port 3000

# 读取 NapCat 当前登录账号，不发送消息
$r = Invoke-RestMethod `
  -Uri "http://127.0.0.1:3000/get_login_info" `
  -Method Post `
  -Headers @{ Authorization = "Bearer $env:LUMENBAY_NAPCAT_TOKEN" } `
  -ContentType "application/json" `
  -Body '{}'
if ($r.status -ne "ok" -or $r.retcode -ne 0) {
  throw "OneBot API returned a non-success status"
}
"OneBot OK; logged-in QQ: $($r.data.user_id)"
```

预期：`TcpTestSucceeded : True`，且 OneBot 响应 `status=ok`、`retcode=0`、QQ 号正确。这个测试**只读**，不会上传照片。不要把 Token、个人 QQ 信息或完整响应发到公开 Issue。

## 4. 配置 Lumenbay 的微信群与相册

首次安装或更新到最新版：

```powershell
cd C:\work\lumenbay
git switch main
git pull --ff-only
mise install
mise exec -- python -m pip install -e .
mise exec -- python -m pip install wxauto4
Copy-Item config.example.json config.json
notepad config.json
```

按照实际环境修改 `config.json`（以下均为**示例值**）：

```json
{
  "wechat_group": "已授权的测试微信群",
  "qq_group_id": "123456789",
  "qq_album_name": "测试照片归档",
  "napcat_base_url": "http://127.0.0.1:3000",
  "database": "data/archive.sqlite3",
  "spool": "data/spool",
  "interval_seconds": 10
}
```

| 字段 | 从哪里获取 / 要求 |
| --- | --- |
| `wechat_group` | Windows 微信内的**群聊显示名称**，需完全一致；避免使用同名的多个群 |
| `qq_group_id` | QQ 测试群的**群号**，不是 QQ 个人账号或相册 ID |
| `qq_album_name` | 在 QQ 群**相册功能中提前创建**的相册名称；区分大小写，名称必须唯一 |
| `napcat_base_url` | **OneBot HTTP 服务器**地址和端口；不是 `:6099` WebUI |
| `database` / `spool` | 本机持久化状态与图片缓存路径；请保留此数据 |
| `interval_seconds` | 微信轮询间隔，秒；示例为 10 秒 |

当前 MVP **按 QQ 群号 + 相册名查找相册 ID**，不要求在配置里手填相册 ID。请使用已经创建、可写入的相册。

`config.json`、本地数据库、图片缓存均被 `.gitignore` 排除，不要提交到 Git。Token **只通过**当前 PowerShell 的 `LUMENBAY_NAPCAT_TOKEN` 环境变量传给 Lumenbay；不要把它写进 JSON 或源码。

## 5. 首次测试

1. 打开并登录 Windows 桌面微信，确认测试群可见。
2. 确认 NapCat 的 QQ 已登录、已加入目标 QQ 群，相册已创建，且第 3 步的 HTTP 请求成功。
3. 在**测试微信群**发送一张获授权的测试照片。
4. 在**同一个 PowerShell**（已设置 Token）执行：

```powershell
# 离线本地状态；不会访问 NapCat，也不能用于检查 Token
mise exec -- lumenbay status --config config.json

# 显式允许本次读取微信并向 QQ 群相册上传
mise exec -- lumenbay run --config config.json --once --execute

# 查看本地处理结果
mise exec -- lumenbay status --config config.json
```

到 QQ **群相册**页面人工检查测试照片是否出现。输出中的 `acknowledged` 只表示 NapCat 接受了上传请求，**并不代表已自动核验 QQ 相册持久保存**。`unknown` 表示上传结果不确定，程序不会自动重复上传，以降低重复图片风险。

完成单次验证后，可运行 `mise exec -- lumenbay run --config config.json --execute` 持续轮询；当前微信免费适配器**不保证离线期间补采历史照片**。请先完成实机兼容性验证再考虑长期运行。

## 6. 常见问题

| 现象 | 检查事项 |
| --- | --- |
| 打不开 `:6099` | 这是 **WebUI** 管理界面；检查 NapCat 是否启动、日志中实际 WebUI 端口 |
| `:3000` 连接被拒绝 | HTTP **服务器**连接未启用、配置未保存、Bot 未启动、端口或 Host 配错 |
| `401` / `403` | 用错 Token（常见是 WebUI Token）、环境变量未设置、HTTP Token 已修改；请求需使用 `Bearer` |
| `404` | 端口或 URL 路径不对，可能访问到了 WebUI 或其他进程 |
| `get_login_info` 返回错误 QQ 号 | 连到了另一个 QQ Bot，核对实例与端口 |
| HTTP 测试成功，但找不到相册 | 核对 QQ 群号、已创建的群相册名称、NapCat 版本与该 QQ 账号权限 |
| `lumenbay status` 正常，但同步失败 | `status` **只读本地 SQLite**；不能证明 NapCat、微信已连通 |
| `WxAutoImageSource` 运行失败 | 检查 Windows 微信是否已登录、`wxauto4` 是否兼容当前微信版本 |
| 上传显示 `unknown` | 请求结果不确定，**不要盲目重传**；先检查 QQ 群相册，保存本地状态并提交脱敏反馈 |

**安全边界：**同机部署优先绑定 `127.0.0.1`，不要把 `:3000` 或 `:6099` 直接暴露到公网。跨机器部署须使用受保护的访问通道与 HTTPS。不要在公开日志、截图、Issue 中泄露 WebUI Token、OneBot Token 或私人照片。

## 官方资料

- [NapCatQQ Desktop：入门](https://napneko.github.io/NapCatQQ-Desktop/docs/)
- [NapCatQQ Desktop：HTTP 连接与 OneBot Token 配置](https://napneko.github.io/NapCatQQ-Desktop/docs/connections/)
- [NapCatQQ：WebUI 与 HTTP 服务端配置](https://napneko.github.io/config/basic)
- [NapCatQQ：Windows Shell 安装](https://napneko.github.io/guide/boot/Shell)
