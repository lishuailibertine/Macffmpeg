# Macffmpeg

Macffmpeg 是一个基于 PyQt6 和 Whisper 等技术开发的 macOS 应用程序，主要用于视频字幕的提取、翻译以及将字幕烧录到视频中，为用户提供了便捷的字幕处理解决方案。

## 功能特点

1. **字幕提取**：支持从多种视频文件（如 mp4、mkv、mov 等）中提取字幕，可选择不同的 Whisper 模型进行处理，并能将提取结果保存为 .srt 或 .txt 格式。
2. **字幕翻译**：提供字幕翻译功能，支持选择不同的翻译服务提供商，需配置相应的 API 密钥。
3. **字幕烧录**：能够将字幕文件烧录到视频中，用户可自定义字幕的字体、大小、颜色、对齐方式、边距、轮廓和阴影等样式。
4. **模型管理**：可查看、下载和删除 Whisper 模型，方便用户根据需求选择合适的模型进行字幕提取。
5. **API 密钥管理**：支持添加、管理不同翻译服务提供商的 API 密钥，以便使用其翻译功能。
6. **界面定制**：提供明暗两种主题模式，用户可根据个人喜好切换，同时支持字体大小调整。

## 技术栈

- **前端框架**：PyQt6，用于构建图形用户界面。
- **语音识别**：OpenAI Whisper，用于从视频中提取字幕文本。
- **打包工具**：PyInstaller，用于将 Python 代码打包成 macOS 可执行应用。
- **自动化构建**：GitHub Actions，用于自动构建 Intel 和 Apple Silicon 版本的应用。

## 安装与使用

1. 克隆仓库：`git clone https://github.com/lishuailibertine/Macffmpeg.git`
2. 进入项目目录：`cd Macffmpeg`
3. 创建并激活虚拟环境：`python3 -m venv venv`，`source venv/bin/activate`
4. 安装依赖：`pip install -r requirements.txt`
5. 运行应用：`python3 main.py`

也可通过项目的 GitHub Actions 构建产物获取已打包的 DMG 安装文件，直接安装使用。

## 许可证

本项目采用 MIT 许可证，详情参见 [LICENSE](LICENSE) 文件。
