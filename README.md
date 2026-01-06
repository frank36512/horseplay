# <img src="horseplay.ico" width="48" style="vertical-align: middle;"> 马上短剧生成系统 (Horseplay)

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)

[English](README_EN.md) | **中文**

---

## 📖 简介

**马上短剧生成系统 (Horseplay)** 是一款旨在革新短剧创作流程的综合性工具。通过集成最先进的 AI 模型（涵盖剧本创作、角色设计、图像生成、视频合成及语音合成），本工具致力于赋能创作者，以极高的效率生产高质量的内容。

无论您是独立创作者还是制作团队，本工具都能帮助您保持角色一致性、生成动态的视觉叙事，并实现音画的完美同步。

---

## ✨ 核心功能

### 📝 智能剧本管理
- **AI 辅助写作**: 利用强大的大语言模型（OpenAI, DeepSeek）生成剧本、对话和场景描述。
- **格式标准化**: 自动将剧本格式化为行业标准的剧本格式。

### 🎨 角色一致性系统
- **档案管理**: 定义详细的角色特征、外貌和背景故事。
- **参考图管理**: 上传并管理参考图像，确保生成媒体中的视觉一致性。

### 🎥 AI 视频生成
- **多模型支持**: 集成顶尖视频生成模型，如 **Google Veo**, **Sora**, **Runway**, 和 **Stable Video Diffusion**。
- **文/图生视频**: 直接根据剧本描述或分镜图像生成视频。

### 🗣️ 音频合成
- **TTS 集成**: 支持 **ElevenLabs**, **OpenAI TTS**, 和 **Edge TTS**，生成逼真的角色语音。
- **音效生成**: 自动生成符合场景氛围的背景音乐和音效。

### 🎬 可视化分镜
- **场景可视化**: 使用 DALL-E 3 或 Stable Diffusion 将剧本场景转化为可视化分镜。
- **镜头规划**: 在视频生成前规划摄像机角度和运镜。

---

## 🛠️ 技术栈

- **语言**: Python 3.10+
- **GUI 框架**: PyQt6 (现代且响应迅速的界面)
- **AI 模型与 API**:
  - **LLM**: OpenAI GPT-4, DeepSeek
  - **图像**: DALL-E 3, Stable Diffusion
  - **视频**: Google Veo, OpenAI Sora, Runway Gen-2/3
  - **音频**: OpenAI TTS, ElevenLabs
- **媒体处理**: FFmpeg, OpenCV, Pydub
- **数据管理**: 基于 JSON 的项目结构

---

## 📂 项目结构

```text
e:\play_tool\
├── src/                    # 源代码
│   ├── ui/                 # 用户界面 (PyQt6)
│   ├── core/               # 核心业务逻辑 (剧本, 角色)
│   ├── ai_engine/          # AI 引擎接口 (LLM, 图像, 视频, 音频)
│   └── database/           # 数据持久化
├── resources/              # 资源与配置
│   ├── config/             # 配置文件
│   ├── projects/           # 用户项目 (Git 忽略)
│   └── scenes/             # 场景资源
├── .venv/                  # 虚拟环境
├── requirements.txt        # 依赖列表
└── main.py                 # 启动入口
```

---

## 🚀 快速开始

### 前置要求

- **Python 3.10+**: 确保安装了 Python 3.10 或以上版本。
- **FFmpeg**: 必须安装 FFmpeg 并添加到系统 PATH 环境变量中。

### 安装步骤

1.  **克隆仓库**:
    ```bash
    git clone https://github.com/frank36512/horseplay.git
    cd horseplay
    ```

2.  **创建虚拟环境**:
    ```bash
    # Windows
    python -m venv .venv
    .venv\Scripts\activate

    # Linux/macOS
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```

### 配置指南

1.  **设置配置文件**:
    复制示例配置文件以创建本地配置。
    ```bash
    # Windows
    copy resources\config\config.example.json resources\config\config.json
    
    # Linux/macOS
    cp resources/config/config.example.json resources/config/config.json
    ```

2.  **添加 API 密钥**:
    打开 `resources/config/config.json` 并填入您计划使用的服务（OpenAI, ElevenLabs, Google 等）的 API 密钥。

### 运行应用

使用以下命令启动应用程序：

```bash
python src/main.py
```

---

## 🗺️ 开发计划

- [x] **第一阶段：基础建设** - 基础 UI、项目管理、剧本编辑器。
- [x] **第二阶段：AI 核心** - 深度集成 LLM 用于剧本创作，以及图像生成用于分镜。
- [x] **第三阶段：视频合成** - 从分镜生成连贯视频片段的流水线。
- [x] **第四阶段：音频与同步** - 口型同步技术（Wav2Lip）和自动混音。
- [x] **第五阶段：打磨** - 导出通用视频格式，时间轴编辑功能。

---

## 🤝 贡献指南

欢迎贡献代码！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解我们的行为准则以及提交拉取请求（Pull Request）的流程。

---

## 📄 许可证

本项目采用 Apache License 2.0 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。
