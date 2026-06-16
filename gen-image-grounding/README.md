# Gen Image Grounding

生图前先搜事实和视觉参考，整理成结构化的生图参数 🧠📷
适用于需要准确性的场景：真实人物、公众人物、品牌、地标、建筑、徽标、服装、海报文字等。

## 使用

直接在对话里说「先搜一下参考」，或者用：

```
/gen-image-grounding
```

Agent 会自动判断要不要搜。

### 触发条件

这些情况会自动触发搜索：
真实人物、公众人物、运动员、品牌、地标、建筑、事件、新闻、科学对象、历史物品、海报、可读文字。

这些会跳过：
纯虚构或通用 prompt，比如「水彩画一只沙发上的猫」，除非你明确要求搜索参考。

### 没有 API key 时

不会执行实际搜索，只输出一份搜索计划。
配置任意一个 provider 的 key 即可启用完整功能——见下方 provider 配置。

## 工作方式

1. 分析 prompt，规划搜索 query
2. 调用已配置的文本搜索、图片搜索和网页读取 provider
3. 下载参考图到本地缓存
4. 输出 JSON，供后续生图模型使用

## 输出格式

```json
{
  "need_search": true,
  "original_prompt": "用户原始 prompt",
  "gen_prompt": "补充事实后的生图 prompt",
  "reference_images": [
    {
      "id": "IMG_001",
      "local_path": "cache/images/...",
      "url": "https://...",
      "page_url": "https://...",
      "title": "图片描述",
      "note": "需要从这张图里参考什么",
      "provider": "serper"
    }
  ],
  "facts": [
    { "claim": "...", "source_url": "https://...", "confidence": "high" }
  ],
  "sources": ["https://..."],
  "warnings": ["注意事项"]
}
```

`need_search` 为 false 时，直接用 `gen_prompt` 生图，无需额外参考。

## 搜索 Provider 配置 🛠️

至少配一个 key 就能跑。没配 key 时只出搜索计划不执行。

**推荐起步**——文本 + 图片搜索一把配齐：

```bash
export SERPER_KEY_ID="..."
```

中国区友好的图片搜索：

```bash
export VOLCENGINE_SEARCH_API_KEY="..."
```

Agent 友好的文本搜索：

```bash
export TAVILY_API_KEY="..."
```

可选：网页内容抓取

```bash
export FIRECRAWL_API_KEY="..."
export JINA_API_KEYS="..."
```

需要自定义 endpoint 时用这两个 👇

```bash
export TEXT_SEARCH_API_BASE_URL="https://google.serper.dev/search"
export IMAGE_SEARCH_API_BASE_URL="https://google.serper.dev/images"
export VOLCENGINE_SEARCH_API_BASE="https://open.feedcoopapi.com/search_api/web_search"
```

## 依赖

- Python 3
- 至少一个搜索 provider 的 API key（没有 key 时只输出计划，不影响其他功能）

## 目录结构

```
gen-image-grounding/
  SKILL.md          # 核心指令
  scripts/          # gen_grounder.py 搜索和整理脚本
  references/       # provider 配置参考
  agents/           # runtime 适配文件
```
