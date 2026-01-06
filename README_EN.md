# Horseplay (AI Short Drama Generator)

[![License](https://img.shields.io/badge/License-Apache%202.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![PyQt6](https://img.shields.io/badge/GUI-PyQt6-green.svg)](https://www.riverbankcomputing.com/software/pyqt/)

**English** | [中文](README.md)

---

## 📖 Introduction

**Horseplay (马上短剧生成系统)** is a comprehensive tool designed to revolutionize the creation of short video dramas. By integrating state-of-the-art AI models for scriptwriting, character design, image generation, video synthesis, and voice synthesis, this tool empowers creators to produce high-quality content with unprecedented efficiency.

Whether you are an independent creator or a production team, this tool helps you maintain character consistency, generate dynamic visual storytelling, and synchronize audio-visual elements seamlessly.

---

## ✨ Key Features

### 📝 Intelligent Script Management
- **AI-Assisted Writing**: Generate scripts, dialogues, and scene descriptions using powerful LLMs (OpenAI, DeepSeek).
- **Format Standardization**: Automatically format scripts into industry-standard screenplays.

### 🎨 Character Consistency System
- **Profile Management**: Define detailed character traits, appearances, and backstories.
- **Reference Images**: Upload and manage reference images to ensure visual consistency across generated media.

### 🎥 AI Video Generation
- **Multi-Model Support**: Integrate with top-tier video generation models like **Google Veo**, **Sora**, **Runway**, and **Stable Video Diffusion**.
- **Text/Image to Video**: Generate videos directly from script descriptions or storyboard images.

### 🗣️ Audio Synthesis
- **TTS Integration**: Support for **ElevenLabs**, **OpenAI TTS**, and **Edge TTS** for realistic character voices.
- **Sound Effects**: Auto-generate background music and sound effects to match the scene mood.

### 🎬 Visual Storyboard
- **Scene Visualization**: Convert script scenes into visual storyboards using DALL-E 3 or Stable Diffusion.
- **Shot Planning**: Plan camera angles and movements before video generation.

---

## 🛠️ Tech Stack

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

## 📂 Project Structure

```text
e:\play_tool\
├── src/                    # Source Code
│   ├── ui/                 # User Interface (PyQt6)
│   ├── core/               # Business Logic (Script, Character)
│   ├── ai_engine/          # AI Clients (LLM, Image, Video, Audio)
│   └── database/           # Data Persistence
├── resources/              # Assets & Config
│   ├── config/             # Configuration Files
│   ├── projects/           # User Projects (Ignored by Git)
│   └── scenes/             # Scene Assets
├── .venv/                  # Virtual Environment
├── requirements.txt        # Python Dependencies
└── main.py                 # Entry Point
```

---

## 🚀 Getting Started

### Prerequisites

- **Python 3.10+**: Ensure Python is installed.
- **FFmpeg**: Must be installed and added to your system PATH.

### Installation

1.  **Clone the repository**:
    ```bash
    git clone https://github.com/frank36512/horseplay.git
    cd horseplay
    ```

2.  **Create Virtual Environment**:
    ```bash
    # Windows
    python -m venv .venv
    .venv\Scripts\activate

    # Linux/macOS
    python3 -m venv .venv
    source .venv/bin/activate
    ```

3.  **Install Dependencies**:
    ```bash
    pip install -r requirements.txt
    ```

### Configuration

1.  **Setup Config File**:
    Copy the example configuration file to creating your local config.
    ```bash
    # Windows
    copy resources\config\config.example.json resources\config\config.json
    
    # Linux/macOS
    cp resources/config/config.example.json resources/config/config.json
    ```

2.  **Add API Keys**:
    Open `resources/config/config.json` and fill in your API keys for the services you plan to use (OpenAI, ElevenLabs, Google, etc.).

### Running

Launch the application using the following command:

```bash
python src/main.py
```

---

## 🗺️ Roadmap

- [x] **Phase 1: Foundation** - Basic UI, Project Management, Script Editor.
- [x] **Phase 2: AI Core** - Deep integration of LLM for script writing and Image Gen for storyboards.
- [x] **Phase 3: Video Synthesis** - Pipeline for generating consistent video clips from storyboards.
- [x] **Phase 4: Audio & Sync** - Lip-sync technology (Wav2Lip) and automated sound mixing.
- [x] **Phase 5: Polish** - Export to common video formats, timeline editing features.

---

## 🤝 Contributing

Contributions are welcome! Please read our [CONTRIBUTING.md](CONTRIBUTING.md) for details on our code of conduct, and the process for submitting pull requests.

---

## 📄 License

This project is licensed under the Apache License 2.0 - see the [LICENSE](LICENSE) file for details.
