# Wyoming Voice Services

完全本地语音处理服务，支持 Home Assistant。

## 包含服务

| 服务 | 功能 | 端口 | 模型 |
|------|------|------|------|
| **VoxCPM2** | TTS 语音合成 | 8000/10200 | 2B 参数，30 语言，48kHz |
| **Whisper** | STT 语音识别 | 10300 | medium-int8 (中文) |
| **OpenWakeWord** | 唤醒词 | 10400 | hey_mycropt |

---

## Mac 安装 (推荐 - Apple Silicon)

M4 Mac Mini 性能很强，直接本地运行效果最好：

### 1. 安装 Homebrew（如果没有）

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

### 2. 安装 Python

```bash
brew install python@3.11
```

### 3. 运行安装脚本

```bash
cd wyoming-voice
chmod +x install-mac.sh
./install-mac.sh
```

### 4. 启动服务

```bash
cd ~/voxcpm-tts
./start.sh
```

### 5. 添加到 Home Assistant

在 Home Assistant 中：

1. **设置** → **设备与服务** → **添加集成**
2. 搜索 **Wyoming**
3. 配置：
   - 主机：Mac 的 IP 地址（如 `192.168.2.xxx`）
   - 端口：`10200`

---

## VoxCPM2 特性

| 特性 | 说明 |
|------|------|
| **语言支持** | 30 种语言（含中文、英文、日文） |
| **中国方言** | 四川话、粤语、吴语、东北话、闽南话等 |
| **Voice Design** | 用自然语言描述创建新声音 |
| **声音克隆** | 从参考音频克隆声音 |
| **输出质量** | 48kHz 高清音频 |

### 语音风格示例

```python
# 温柔女声
"(年轻女性，温柔甜美的声音)你好，欢迎回家！"

# 沉稳男声
"(中年男性，声音深沉稳重)今天的温度是二十五度。"

# 四川话
"(四川方言，地道四川话)你今天吃火锅了吗？"

# 粤语
"(粤语，地道广东话)早晨，今日天气好好。"
```

---

## Linux/WSL 安装 (Docker)

需要 NVIDIA GPU。

### 1. 安装 Docker

```bash
# Linux
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER

# Windows: 安装 Docker Desktop
# Mac: 安装 Docker Desktop (但推荐用上面的 Mac 本地方案)
```

### 2. 启动服务

```bash
cd wyoming-voice
docker compose up -d
```

---

## Home Assistant Pipeline 配置

安装完成后，创建语音助手：

1. **设置** → **语音助手** → **添加**
2. 配置：

| 项目 | 选择 |
|------|------|
| 名称 | 本地中文助手 |
| STT | FunASR 或 Wyoming Whisper |
| TTS | Wyoming VoxCPM |
| 对话代理 | CodingPlan |
| 唤醒词 | Wyoming OpenWakeWord |

---

## 文件说明

```
wyoming-voice/
├── install-mac.sh         # Mac 安装脚本 ⭐ 推荐
├── docker-compose.yml     # Linux GPU Docker 配置
├── docker-compose.mac.yml # Mac Docker 配置（不推荐）
├── Dockerfile.wyoming     # Wyoming 适配器 Docker
├── wyoming_voxcpm.py      # Wyoming 协议适配器代码
└── README.md              # 本文件
```

---

## 迁移到 Mac Mini

如果你在 Windows/WSL 上开发，之后要迁移到 Mac：

1. 在 Mac 上运行 `install-mac.sh`
2. 首次启动会下载模型（~4GB）
3. 在 Home Assistant 中更新 Wyoming 地址

---

## 性能对比

| 设备 | RTF (实时因子) | 说明 |
|------|---------------|------|
| M4 Mac Mini | ~0.5-0.8 | 很快，流畅 |
| RTX 4090 | ~0.13 | 最快 |
| M1 Mac | ~0.8-1.2 | 可用 |
| 纯 CPU | >2.0 | 很慢，不推荐 |

RTF < 1.0 表示生成速度快于播放速度，实时流畅。

---

## 常见问题

### 模型下载慢？

使用 ModelScope 国内镜像：

```bash
pip install modelscope
python -c "from modelscope import snapshot_download; snapshot_download('OpenBMB/VoxCPM2', local_dir='./models')"
```

然后设置环境变量：
```bash
export MODEL_PATH=./models
```

### 内存不足？

VoxCPM2 需要约 8GB 内存，确保 Mac 有足够空间。

### 音频质量不好？

调整参数：
```python
wav = model.generate(
    text=text,
    cfg_value=5.0,        # 更高 = 更清晰
    inference_timesteps=20, # 更高 = 更细腻
)
```