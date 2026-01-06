# Horseplay / 马上短剧生成系统

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)

[English](#-introduction) | [中文](#-简介)

---

## 📖 Introduction

**Horseplay (马上短剧生成系统)** is a comprehensive tool designed to revolutionize the creation of short video dramas. By integrating state-of-the-art AI models for scriptwriting, character design, image generation, video synthesis, and voice synthesis, this tool empowers creators to produce high-quality content with unprecedented efficiency.

Whether you are an independent creator or a production team, this tool helps you maintain character consistency, generate dynamic visual storytelling, and synchronize audio-visual elements seamlessly.

## 📖 简介

**马上短剧生成系统 (Horseplay)** 是一款旨在革新短剧创作流程的综合性工具。通过集成最先进的 AI 模型（涵盖剧本创作、角色设计、图像生成、视频合成及语音合成），本工具致力于赋能创作者，以极高的效率生产高质量的内容。

无论您是独立创作者还是制作团队，本工具都能帮助您保持角色一致性、生成动态的视觉叙事，并实现音画的完美同步。

---

## ✨ Key Features / 核心功能

### 📝 Intelligent Script Management / 智能剧本管理
- **AI-Assisted Writing**: Generate scripts, dialogues, and scene descriptions using powerful LLMs (OpenAI, DeepSeek).
- **Format Standardization**: Automatically format scripts into industry-standard screenplays.
- **AI 辅助写作**: 利用强大的大语言模型（OpenAI, DeepSeek）生成剧本、对话和场景描述。
- **格式标准化**: 自动将剧本格式化为行业标准的剧本格式。

### 🎨 Character Consistency System / 角色一致性系统
- **Profile Management**: Define detailed character traits, appearances, and backstories.
- **Reference Images**: Upload and manage reference images to ensure visual consistency across generated media.
- **档案管理**: 定义详细的角色特征、外貌和背景故事。
- **参考图管理**: 上传并管理参考图像，确保生成媒体中的视觉一致性。

### 🎥 AI Video Generation / AI 视频生成
- **Multi-Model Support**: Integrate with top-tier video generation models like **Google Veo**, **Sora**, **Runway**, and **Stable Video Diffusion**.
- **Text/Image to Video**: Generate videos directly from script descriptions or storyboard images.
- **多模型支持**: 集成顶尖视频生成模型，如 **Google Veo**, **Sora**, **Runway**, 和 **Stable Video Diffusion**。
- **文/图生视频**: 直接根据剧本描述或分镜图像生成视频。

### 🗣️ Audio Synthesis / 音频合成
- **TTS Integration**: Support for **ElevenLabs**, **OpenAI TTS**, and **Edge TTS** for realistic character voices.
- **Sound Effects**: Auto-generate background music and sound effects to match the scene mood.
- **TTS 集成**: 支持 **ElevenLabs**, **OpenAI TTS**, 和 **Edge TTS**，生成逼真的角色语音。
- **音效生成**: 自动生成符合场景氛围的背景音乐和音效。

### 🎬 Visual Storyboard / 可视化分镜
- **Scene Visualization**: Convert script scenes into visual storyboards using DALL-E 3 or Stable Diffusion.
- **Shot Planning**: Plan camera angles and movements before video generation.
- **场景可视化**: 使用 DALL-E 3 或 Stable Diffusion 将剧本场景转化为可视化分镜。
- **镜头规划**: 在视频生成前规划摄像机角度和运镜。

---

## 🛠️ Tech Stack / 技术栈

- **Language**: Python 3.10+
- **GUI Framework**: PyQt6 (Modern & Responsive Interface)
- **AI Models & APIs**:
  - **LLM**: OpenAI GPT-4, DeepSeek
  - **Image**: DALL-E 3, Stable Diffusion
  - **Video**: Google Veo, OpenAI Sora, Runway Gen-2/3
  - **Audio**: OpenAI TTS, ElevenLabs
- **Media Processing**: FFmpeg, OpenCV, Pydub
- **Data Management**: JSON based project structure

---

## 📂 Project Structure / 项目结构

```text
e:\play_tool\
├── src/                    # Source Code / 源代码
│   ├── ui/                 # User Interface (PyQt6) / 用户界面
│   ├── core/               # Business Logic (Script, Character) / 核心业务逻辑
│   ├── ai_engine/          # AI Clients (LLM, Image, Video, Audio) / AI 引擎接口
│   └── database/           # Data Persistence / 数据持久化
├── resources/              # Assets & Config / 资源与配置
│   ├── config/             # Configuration Files / 配置文件
│   ├── projects/           # User Projects (Ignored by Git) / 用户项目
│   └── scenes/             # Scene Assets / 场景资源
├── .venv/                  # Virtual Environment / 虚拟环境
├── requirements.txt        # Python Dependencies / 依赖列表
└── main.py                 # Entry Point / 启动入口
```

---

## 🚀 Getting Started / 快速开始

### Prerequisites / 前置要求

- **Python 3.10+**: Ensure Python is installed. / 确保安装了 Python 3.10 或以上版本。
- **FFmpeg**: Must be installed and added to your system PATH. / 必须安装 FFmpeg 并添加到系统 PATH 环境变量中。

### Installation / 安装步骤

1.  **Clone the repository / 克隆仓库**:
    ```bash
    git clone https://github.com/your-username/horseplay.git
    cd horseplay
    ```

2.  **Create Virtual Environment / 创建虚拟环境**:
    ```bash
    # Windows
    python -m venv .venv
    .venv\Scripts\activate

    # Linux/macOS
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install Dependencies / 安装依赖**:
    ```bash
    pip install -r requirements.txt
    ```

### Configuration / 配置指南

1.  **Setup Config File / 设置配置文件**:
    Copy the example configuration file to creating your local config.
    复制示例配置文件以创建本地配置。
    ```bash
    # Windows
    copy resources\config\config.example.json resources\config\config.json
    
    # Linux/macOS
    cp resources/config/config.example.json resources/config/config.json
    ```

2.  **Add API Keys / 添加 API 密钥**:
    Open `resources/config/config.json` and fill in your API keys for the services you plan to use (OpenAI, ElevenLabs, Google, etc.).
    打开 `resources/config/config.json` 并填入您计划使用的服务（OpenAI, ElevenLabs, Google 等）的 API 密钥。

### Running / 运行应用

Launch the application using the following command:
使用以下命令启动应用程序：

```bash
python src/main.py
```

---

## 🗺️ Roadmap / 开发计划

- [x] **Phase 1: Foundation** - Basic UI, Project Management, Script Editor.
- [ ] **Phase 2: AI Core** - Deep integration of LLM for script writing and Image Gen for storyboards.
- [ ] **Phase 3: Video Synthesis** - Pipeline for generating consistent video clips from storyboards.
- [ ] **Phase 4: Audio & Sync** - Lip-sync technology (Wav2Lip) and automated sound mixing.
- [ ] **Phase 5: Polish** - Export to common video formats, timeline editing features.

- [x] **第一阶段：基础建设** - 基础 UI、项目管理、剧本编辑器。
- [ ] **第二阶段：AI 核心** - 深度集成 LLM 用于剧本创作，以及图像生成用于分镜。
- [ ] **第三阶段：视频合成** - 从分镜生成连贯视频片段的流水线。
- [ ] **第四阶段：音频与同步** - 口型同步技术（Wav2Lip）和自动混音。
- [ ] **第五阶段：打磨** - 导出通用视频格式，时间轴编辑功能。

---

## 🤝 Contributing / 贡献指南

Contributions are welcome! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests.

欢迎贡献代码！请阅读 [CONTRIBUTING.md](CONTRIBUTING.md) 了解我们的行为准则以及提交拉取请求（Pull Request）的流程。

---

## 📄 License / 许可证

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.

本项目采用 Apache License 2.0 许可证 - 详情请参阅 [LICENSE](LICENSE) 文件。
