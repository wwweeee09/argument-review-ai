# 吵架复盘AI助手 - 让对话更有温度

[![License](https://img.shields.io/badge/license-MIT-blue.svg)](LICENSE)
[![Python](https://img.shields.io/badge/python-3.9+-green.svg)](https://www.python.org/)
[![Flask](https://img.shields.io/badge/flask-2.3.3-red.svg)](https://flask.palletsprojects.com/)
[![DeepSeek](https://img.shields.io/badge/DeepSeek-API-orange.svg)](https://deepseek.com/)

> **先处理心情，再处理事情。赢了对错，输了感情，才是最大的损失。**

## 📖 项目简介

**吵架复盘AI助手** 是一款智能沟通分析工具，通过上传争吵录音，自动识别不同说话人，并结合完整对话语境进行深度分析。它能帮助你理解争吵中的情绪变化、逻辑问题、沟通模式，并提供建设性的改进建议。

### ✨ 核心理念

- **让对话更有温度** - 不仅仅分析对错，更关注如何让沟通更温暖
- **先听再说** - 理解每句话背后的情绪和需求
- **和好才是目的** - 帮助用户找到更好的沟通方式

---

## 🎯 主要功能

| 功能模块 | 说明 |
|---------|------|
| 🎙️ **多说话人识别** | 自动识别2-10个不同说话人，每个说话人用不同颜色标记 |
| 📝 **音频转文字** | 支持MP3、WAV、M4A等格式，自动转换为PCM格式识别 |
| 🔍 **结合语境逐句分析** | 每句话都结合完整对话上下文分析，而非孤立分析 |
| 📊 **综合分析报告** | 500-1000字深度报告 + 情绪变化曲线图 + 沟通能力雷达图 |
| 💬 **智能对话问答** | 分析完成后可随时提问，AI结合对话内容回答 |
| ✏️ **在线编辑修正** | 识别结果可直接编辑修改，修正识别错误 |
| ⏸️ **流式控制** | 支持暂停/继续/停止AI回答，像DeepSeek一样流畅 |
| 🎨 **暖心视觉设计** | Babylon.js 3D粒子背景 + 30张随机温馨图片 |

---

## 🖼️ 界面预览

```
┌─────────────────────────────────────────────────────────────────┐
│  🎙️ 吵架复盘AI助手                    🤖 AI 智能分析助手        │
│  先处理心情，再处理事情                 逐句分析 + 综合 + 问答     │
├─────────────────────────────┬───────────────────────────────────┤
│  📁 上传音频                 │  🧠 思考模式  ⚡ 快速模式           │
│  🎤 说话人0: 6句            │  📝 逐句分析 + 综合                │
│  🎤 说话人1: 8句            │  🗑️ 清空记忆                      │
│  💬 说话人0: 你干嘛？        ├───────────────────────────────────┤
│  💬 说话人1: 能不能别拉黑   │  💬 AI: 这句话表达了愤怒情绪...    │
│  [可编辑修正]               │  📊 情绪变化曲线图                  │
│  [重新上传] [开始分析]      │  🎯 沟通能力雷达图                  │
├─────────────────────────────┴───────────────────────────────────┤
│  💡 用心倾听，用爱沟通。好好说话，就是把对方放在心上。           │
└─────────────────────────────────────────────────────────────────┘
```

---

## 🛠️ 技术架构

### 后端技术栈

| 技术 | 用途 |
|------|------|
| **Python 3.9+** | 后端开发语言 |
| **Flask** | Web框架 |
| **百度语音质检API** | 多说话人语音识别 |
| **DeepSeek API** | 智能分析和对话 |
| **pydub + ffmpeg** | 音频格式转换 |

### 前端技术栈

| 技术 | 用途 |
|------|------|
| **HTML5/CSS3** | 页面结构 |
| **JavaScript** | 交互逻辑 |
| **Babylon.js** | 3D爱心粒子背景 |
| **ECharts** | 数据可视化图表 |
| **Marked.js** | Markdown渲染 |
| **Font Awesome** | 图标库 |

---

## 📦 安装与运行

### 1. 克隆项目

```bash
git clone https://github.com/yourusername/argument-review-ai.git
cd argument-review-ai
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

创建 `.env` 文件：

```env
# 百度AI平台配置（必需）
BAIDU_API_KEY=你的API Key
BAIDU_SECRET_KEY=你的Secret Key

# DeepSeek配置（必需）
DEEPSEEK_API_KEY=你的DeepSeek API Key

# 可选：百度云BOS配置
# BAIDU_ACCESS_KEY=你的BOS Access Key
# BAIDU_SECRET_KEY=你的BOS Secret Key
# BOS_ENDPOINT=bj.bcebos.com
# BOS_BUCKET_NAME=asr-audio-bucket
```

### 4. 安装 ffmpeg（音频处理必需）

- **macOS**: `brew install ffmpeg`
- **Ubuntu/Debian**: `sudo apt-get install ffmpeg`
- **Windows**: 下载 [ffmpeg](https://ffmpeg.org/download.html) 并添加到 PATH

### 5. 运行应用

```bash
python app.py
```

### 6. 访问应用

打开浏览器访问 `http://localhost:5000`

---

## 🔧 API 接口文档

| 接口 | 方法 | 说明 |
|------|------|------|
| `/api/upload` | POST | 上传音频文件 |
| `/api/recognize/<file_id>` | POST | 识别音频（多说话人） |
| `/api/analyze_sentence` | POST | 逐句分析（结合上下文） |
| `/api/analyze_overall` | POST | 综合分析 |
| `/api/chat/stream` | POST | 流式对话 |
| `/api/models` | GET | 获取模型列表 |
| `/api/health` | GET | 健康检查 |

---

## 📁 项目结构

```
argument-review-ai/
├── app.py              # Flask主程序
├── requirements.txt    # Python依赖
├── .env               # 环境变量配置
├── uploads/           # 临时音频存储目录
├── templates/
│   └── index.html     # 前端页面
└── README.md          # 项目说明
```

---

## 🧠 逐句分析示例

**原文：** “你怎么又忘了？每次都这样！”

**AI 结合语境分析：**

```
📌 情绪分析：这句话表达了强烈的失望和愤怒情绪，
情绪强度约8/10。结合前文，这是对方第3次提到"忘记"，
情绪在逐渐累积。

🔍 逻辑分析：使用了绝对化词语"每次都"，
属于以偏概全的逻辑谬误，容易激化矛盾。

💡 改进建议：换成“这次忘记了我有点难过，
下次可以提醒我一下吗？”更能让对方接受。
```

---

## 📊 图表说明

### 情绪变化曲线
- 显示对话过程中情绪强度的变化趋势
- 鼠标悬停可查看具体数值
- 帮助识别情绪爆发点和缓和点

### 沟通能力雷达图
- 从5个维度评估沟通能力
- 客观呈现沟通中需要提升的方向

---

## 🌟 特色亮点

1. **真正逐句分析** - 每一句话都独立调用AI分析，绝不偷工减料
2. **完整上下文理解** - 不再是孤立分析，而是结合整段对话语境
3. **多说话人准确识别** - 最多支持10人，自动分配颜色
4. **可编辑的识别结果** - 识别错误可直接修改
5. **流式问答体验** - 暂停/继续/停止，体验流畅
6. **暖心设计细节** - 温馨文字提醒 + 3D爱心粒子 + 随机图片

---

## 📄 许可证

本项目采用 MIT 许可证 - 详见 [LICENSE](LICENSE) 文件

---

## 🙏 致谢

- [DeepSeek](https://deepseek.com/) - 提供强大的AI分析能力
- [百度AI](https://ai.baidu.com/) - 提供语音识别服务
- [Babylon.js](https://www.babylonjs.com/) - 3D渲染引擎
- [ECharts](https://echarts.apache.org/) - 数据可视化


---

## 💬 写在最后

> **每一次争吵，都是为了更好的相遇。**
> **说出去的话，收不回；伤过的心，需要加倍温暖。**
> **用心倾听，用爱沟通。好好说话，就是把对方放在心上。**

希望这个工具能帮助你改善沟通，让每一段关系都更有温度。❤️

---

*如果这个项目对你有帮助，欢迎点亮 Star ⭐ 支持一下！*
