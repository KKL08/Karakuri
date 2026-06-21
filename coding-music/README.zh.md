# coding-music —— 写代码时有 BGM 🎧

边写代码边听歌的感觉，不用多说。但 Claude Code 一弹权限确认框，你还得手动切出去暂停——来回几次，状态就碎了。

**coding-music 做的事很简单：** Claude 弹确认框时音乐自动停，你点完确认它立刻接着播。全程不用你动手，注意力不用断。

[English](./README.md)

---

## 这就是你的状态

打开终端，说句 `coding-music`，红心歌单开始播。写着写着 Claude 问你"允许执行这个命令吗？"——音乐自动淡出。你点完确认，下一秒它就续上。整个过程你甚至没注意到。

**两个规则，你说了算：**

| 规则 | 效果 | 默认 |
|------|------|------|
| Rule 1 | Claude 弹确认框→暂停，确认后→恢复 | ✅ 开 |
| Rule 2 | Claude 回复完→暂停，你发下一条消息→恢复 | ❌ 关 |

想用 Rule 2 就说 `开启 rule2`，不想要就说 `关闭 rule2`。Rule 2 比较适合那种"Claude 回完我要仔细看"的场景。

---

## 快速上手

装好了就说这句话：

| 说 | 发生什么 |
|----|---------|
| `coding-music` | 红心歌单开播，自动暂停/恢复激活 |
| `停止 coding-music` | 停播，hook 关掉 |
| `开启 rule2` / `关闭 rule2` | 切换 Rule 2 |
| `查看伴奏状态` | 看一眼当前配置和播放状态 |

---

## 怎么做到自动暂停/恢复？

```
Claude 弹出权限确认框
    → PermissionRequest hook 触发 → 暂停音乐
你点了确认
    → PostToolUse hook 触发 → 立刻恢复播放
```

两条 hook 挂在 Claude Code 的 hook 系统上，轻量，不改任何 Claude Code 内部行为。

---

## 安装

### 准备工作

装这几个东西（都只装一次）：

- [mpv](https://mpv.io) 播放器：`brew install mpv`
- [jq](https://jqlang.github.io/jq/) JSON 处理：`brew install jq`
- Python 3.8+
- Node.js >= 18

### 1. 拿到网易云音乐开发者凭证

去[网易云音乐开放平台](https://developer.music.163.com/st/developer/apply/account?type=INDIVIDUAL)注册，拿到你的 `appId` 和 `privateKey`。

### 2. 装好 ncm-cli 并登录

```bash
npm install -g @music163/ncm-cli
ncm-cli configure   # 输入 appId 和 privateKey
ncm-cli login       # 授权你的网易云账号
```

详细的 ncm-cli 用法见 [NetEase/skills](https://github.com/NetEase/skills)。

### 3. 安装 coding-music

```bash
git clone https://github.com/KKL08/Karakuri.git
cd Skill/coding-music
bash scripts/install.sh
```

`install.sh` 会帮你把一切就位，不用手动搬文件：

- hook 脚本 → `~/.claude/hooks/coding-music/`
- `SKILL.md` → `~/.claude/skills/coding-music/`
- 在 `~/.claude/settings.json` 里注册所有 hook
- 创建默认的配置文件、状态文件

装完重启 Claude Code，就能用了。

---

## 配置和日志

配置文件在 `~/.claude/hooks/coding-music/config.json`：

```json
{
  "enabled": true,
  "rule2_enabled": false,
  "log_enabled": true
}
```

- `enabled`：全局开关，关掉 coding-music 就跟没装一样
- `rule2_enabled`：对应上文的 Rule 2
- `log_enabled`：开日志的话，每次暂停/恢复都有记录

日志写在这里：`~/.claude/hooks/coding-music/logs/music.log`

---

## 不想用了？

```bash
bash scripts/uninstall.sh
```

hook 脚本、SKILL.md、settings.json 里的注册项一起清掉，干干净净。
