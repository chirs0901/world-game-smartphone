# 🌍 World Game — 手机全产业模拟经营游戏

> AI 驱动的产业世界模拟器，扮演手机公司产品经理，在真实的行业资讯驱动下做出经营决策。

🎮 **[点击开始游戏 →](https://world-game-smartphone.vercel.app)**

---

## 📖 游戏世界观

### 背景设定

时间设定在 **2025年**，全球智能手机产业正处于 AI 浪潮的拐点。

你是一家手机品牌的掌舵人。每一回合代表一个季度，共 **40 回合（10年）**。你需要在瞬息万变的市场中，做出关于技术研发、供应链布局、品牌营销、产品定价的战略决策，最终打造你的手机帝国。

### 行业资讯驱动一切

游戏中的事件、市场趋势、技术路线全部由**真实的行业资讯（RSS）**驱动：

- 每 **30 分钟**自动抓取全网 23+ 行业 RSS 源
- RSS 情报引擎将新闻转化为游戏事件、市场信号、趋势调整
- 8 大分类：手机品牌动态、屏幕显示、平台芯片、散热、电池、影像、存储供应、AI
- 小红书社交动态实时反映品牌口碑

### 核心循环

```
观察事件 → 制定决策 → AI决策委辩论 → 推演沙盘模拟 → 指标变化 → 下一回合
```

每个回合你会经历：
1. **情报阶段** — 接收 RSS 驱动的行业事件和市场动态
2. **决策阶段** — 在研发、营销、供应链等方向分配资源
3. **辩论阶段** — AI 决策委员会（CTO/CMO/CFO等角色）对你的方案进行辩论
4. **推演阶段** — LLM 驱动的沙盘模拟你决策的连锁影响
5. **反馈阶段** — 查看指标变化和叙事总结

---

## 🎮 可选公司

| 品牌 | 定位 | 难度 | 特色 |
|------|------|------|------|
| 🍎 Apply | 端侧AI生态引领者 | 普通 | 生态系统壁垒、品牌溢价、自研芯片 |
| 📱 Samsun | AI全场景生活助手 | 简单 | 全产业链垂直整合、屏幕技术领先 |
| 🌐 Huawey | 全栈自研AI终端 | 困难 | 自研芯片+OS，面临外部制裁压力 |
| 📸 OYeah | AI影像与年轻化体验 | 普通 | 拍照调教、线下渠道、营销能力 |
| 🎵 Viva | AI音影融合体验 | 普通 | HiFi音频、东南亚渠道、性价比 |
| 🔥 Xiaomee | AIoT生态普惠者 | 困难 | 极致性价比、IoT生态、粉丝社区 |
| ⚡ HonorX | AI赋能年轻商务场景 | 困难 | 品牌重塑、海外市场、灵活机制 |
| 💡 NothingX | AI驱动的极简设计体验 | 困难 | 设计创新、社区热度、小众差异化 |

---

## ✨ 游戏特色

### 📡 RSS 行业情报系统
- 23+ 行业 RSS 源，覆盖 8 大器件和技术分类
- 每 30 分钟自动刷新，实时转化为游戏内容
- 情报信号自动注入：游戏事件、AI决策委辩论、推演沙盘、器件路线图

### 🤖 AI 决策委员会
- 多角色 AI 代理人（CTO、CMO、CFO 等）对玩家决策进行辩论
- 基于 RSS 情报生成辩论议题，模拟真实公司治理
- LLM 驱动的观点碰撞，输出决策建议

### 🔬 推演沙盘
- LLM 驱动的决策推演引擎
- 支持「如果…会怎样」假设分析
- RSS 情报作为计算因子注入推演上下文

### 📊 器件技术路线图
- 8 大器件类别级联预测：BOM成本、FFR、质量、口碑
- 趋势权重由 RSS 情报动态调整
- 静态趋势 vs 动态趋势对比

### 📱 小红书社交动态
- 实时抓取品牌相关小红书笔记
- 按点赞排序展示 Top 20
- 每 2 小时更新，支持手动刷新
- 图片代理绕过防盗链

### 🏪 专卖店实时动画
- 顾客进出店动画
- 实时市场活动流
- 品牌排行榜和销量统计

---

## 🛠 技术栈

| 层级 | 技术 |
|------|------|
| **后端** | Python 3.11 · FastAPI · SQLite (SQLAlchemy async) |
| **前端** | Next.js 16 · React 19 · TypeScript · Tailwind CSS · Framer Motion |
| **LLM** | 多 LLM Provider 支持（OpenAI / DeepSeek 等） |
| **RSS** | OPML 解析 · httpx 异步抓取 · BeautifulSoup4 |
| **社交** | opencli 小红书采集 · 图片代理 |

---

## 🚀 本地运行

### 环境要求
- Python 3.11+
- Node.js 18+
- LLM API Key（OpenAI / DeepSeek 等）

### 启动后端

```bash
cd world-game
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入 LLM API Key

# 启动
uvicorn src.main:app --host 127.0.0.1 --port 8000
```

### 启动前端

```bash
cd world-game/frontend
npm install
npm run dev
```

打开 [http://localhost:3000](http://localhost:3000) 即可开始游戏。

---

## 📁 项目结构

```
world-game/
├── src/                    # Python 后端
│   ├── api/                # FastAPI 路由
│   ├── engines/            # 核心引擎（事件生成、推演、RSS情报、技术路线图）
│   ├── services/           # 业务服务层
│   ├── models/             # 数据模型
│   ├── schemas/            # Pydantic Schema
│   └── llm/                # LLM 客户端
├── frontend/               # Next.js 前端
│   ├── app/                # 页面路由
│   ├── components/         # UI 组件
│   └── lib/                # API client / 状态管理
├── config/                 # YAML 配置文件
├── data/                   # 事件数据 / 知识图谱 / RSS源(OPML)
└── vercel.json             # Vercel 部署配置
```

---

## 📜 License

MIT License - 自由使用和修改
