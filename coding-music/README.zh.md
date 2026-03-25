# coding-music — Claude Code Skill

在用 Claude Code 写代码时，自动播放你的网易云音乐红心歌曲。Claude 弹出权限确认框时自动暂停，确认后立即恢复，不打断你的状态。

[English](./README.md)

## 环境依赖

- **ncm-cli** — `npm install -g @music163/ncm-cli`（[npm](https://www.npmjs.com/package/@music163/ncm-cli)）
- [mpv](https://mpv.io) — 播放器（`brew install mpv`）
- [jq](https://jqlang.github.io/jq/) — JSON 处理工具（`brew install jq`）
- Python 3.8+
- Node.js >= 18

## 安装

### 第一步：获取网易云音乐开发者凭证

前往[网易云音乐开放平台](https://developer.music.163.com/st/developer/apply/account?type=INDIVIDUAL)注册，获取 `appId` 和 `privateKey`。

### 第二步：安装并配置 ncm-cli

```bash
npm install -g @music163/ncm-cli
ncm-cli configure   # 输入 appId 和 privateKey
ncm-cli login       # 授权账号
```

ncm-cli 的详细使用说明见 [NetEase/skills](https://github.com/NetEase/skills)。

### 第三步：安装 coding-music

```bash
git clone https://github.com/KKL08/Skill.git
cd Skill/coding-music
bash scripts/install.sh
```

`install.sh` 会自动完成以下操作：
- 将 hook 脚本复制到 `~/.claude/hooks/coding-music/`
- 将 `SKILL.md` 安装到 `~/.claude/skills/coding-music/`
- 在 `~/.claude/settings.json` 中注册所有 hook
- 创建默认配置文件和状态文件

安装完成后重启 Claude Code 即可生效。

## 使用方式

| 说这句话 | 效果 |
|----------|------|
| `coding-music` | 开始播放红心歌曲，激活自动暂停/恢复 |
| `停止 coding-music` | 停止播放，禁用 hook |
| `开启 rule2` | Claude 回复完毕时也暂停 |
| `关闭 rule2` | 关闭 rule2 |
| `查看伴奏状态` | 查看当前配置和播放状态 |

## 工作原理

```
权限确认框出现
    → PermissionRequest hook → 暂停音乐
用户点击确认
    → PostToolUse hook → 立即恢复播放
```

两条规则：

- **Rule 1**（默认开启）：权限弹窗时暂停，确认后恢复
- **Rule 2**（可选开启）：Claude 回复完毕时暂停，你发下一条消息时恢复

## 卸载

```bash
bash scripts/uninstall.sh
```

会移除 hook 脚本、SKILL.md，并清理 `settings.json` 中的所有 hook 注册。

## 配置

`~/.claude/hooks/coding-music/config.json`：

```json
{
  "enabled": true,
  "rule2_enabled": false,
  "log_enabled": true
}
```

日志文件：`~/.claude/hooks/coding-music/logs/music.log`
