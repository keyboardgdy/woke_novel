# Mac OS 安装 Python、Claude 和 cc switch 教程

下面是一份详细的分步教程，帮助你在 macOS 上完成环境搭建。

---

## 📋 准备工作

在开始之前，请确保：
- 你的 macOS 版本在 **10.15 (Catalina)** 或更高
- 拥有 **管理员权限**（安装软件时需要输入密码）
- 稳定的网络连接

---

## 第一部分：安装 Python

### 方法一：使用 Homebrew（推荐）✅

#### 步骤 1：安装 Homebrew

打开 **终端（Terminal）**（可在 Spotlight 中搜索 "Terminal"），执行：

```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

按提示输入密码，等待安装完成。

#### 步骤 2：配置环境变量

Apple Silicon (M1/M2/M3) 芯片需要额外配置：

```bash
echo 'eval "$(/opt/homebrew/bin/brew shellenv)"' >> ~/.zprofile
eval "$(/opt/homebrew/bin/brew shellenv)"
```

Intel 芯片通常无需此步骤。

#### 步骤 3：安装 Python

```bash
brew install python@3.12
```

#### 步骤 4：验证安装

```bash
python3 --version
pip3 --version
```

看到类似 `Python 3.12.x` 的输出即表示成功。

### 方法二：官方安装包

1. 访问 [python.org/downloads](https://www.python.org/downloads/)
2. 下载 **macOS 64-bit universal2 installer**
3. 双击 `.pkg` 文件，按向导完成安装

---

## 第二部分：安装 Claude Code 

> Claude 是 Anthropic 官方的 macOS 桌面客户端。

### 步骤 1：确认已安装 Node.js（可选）

如果你的环境已有 Node.js 16+ 可跳过：

```bash
brew install node
```

### 步骤 2：安装应用

```bash
npm install -g @anthropic-ai/claude-code@2.1.150
```

### 步骤 4：验证

登录成功后即可在终端与 Claude 对话。

> ```bash
> 	claude --version
> ```

---

## 第三部分：安装 cc switch

> **cc switch**（Claude Code Switch）是一个用于在多个 Claude API 配置（官方 API / 中转 API / 不同模型）之间快速切换的辅助工具，常用于 Claude Code 命令行使用场景。

程序安装包
[Releases · farion1231/cc-switch](https://github.com/farion1231/cc-switch/releases)
![[Pasted image 20260603172647.png]]




---

## 🛠 常见问题排查

| 问题 | 解决方案 |
|------|---------|
| `python3: command not found` | 重新执行 `brew install python@3.12`，确认 PATH 配置 |
| Claude Desktop 无法打开 | 在「系统设置 → 隐私与安全性」中点击「仍要打开」 |
| `cc-switch: command not found` | 全局安装路径未加入 PATH，运行 `npm config get prefix` 查看 |
| pip 安装速度慢 | 使用国内镜像：`pip3 install -i https://pypi.tuna.tsinghua.edu.cn/simple xxx` |
| zsh 与 bash 命令差异 | macOS 默认 zsh，配置文件为 `~/.zshrc` 或 `~/.zprofile` |

---

## 📝 完整命令速查

```bash
# 一键安装脚本（按顺序执行）
brew install python@3.12 node
brew install --cask claude
npm install -g cc-switch

# 验证
python3 --version
claude --version      # 如果 Claude Code CLI 已配置
cc-switch --help
```

---

如果你能告诉我 **cc switch** 的具体来源（GitHub 仓库或官网），我可以提供更精确的安装命令和配置示例。需要我针对哪个部分展开说明吗？