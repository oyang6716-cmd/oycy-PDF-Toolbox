# oycy的PDF工具箱 · Windows 桌面版

包豪斯设计的 Windows 桌面 PDF 工具箱，带可配置的 OpenAI 兼容 API 文档助手。由 Python/Tkinter 和 PyMuPDF 实现。**此 ZIP 是可构建的软件源码，不是预先编译好的安装程序。**

## 零本地开发环境：通过 GitHub 在线构建 Windows EXE

1. 在 GitHub 新建一个**私人仓库**（Private repository）。
2. 将本项目 ZIP 解压后的**文件内容**上传至仓库根目录，包括 `.github/workflows/windows-build.yml`（注意 `.github` 是隐藏目录）。也可用 GitHub Desktop 上传整个项目。
3. 在 GitHub 仓库顶部选择 **Actions** → **Build Windows executable** → **Run workflow**。
4. 构建完成后，点击本次运行页面下方的 **Artifacts → oycy-PDF-Toolbox-Windows**，下载并解压。
5. 双击 `oycy-PDF-Toolbox.exe` 启动。它是**便携式 EXE，不是带安装向导的 MSI/Setup.exe**，可把它放在任意目录，并创建桌面快捷方式。首次运行可能出现 Windows SmartScreen 提醒，因为 EXE 未做代码签名；不要在不能确认来源时绕过安全提示。

> GitHub Actions 在私有仓库中使用时可能受配额、账户或平台规则限制。构建过程依赖 Python 包下载，打包成功需要在 Windows 环境验证。

## 有 Python 的 Windows 用户

双击 `build_windows.bat` 自动安装依赖并构建：最终文件位于 `dist/oycy-PDF-Toolbox.exe`。
开发方式：`py -m pip install -r requirements.txt`，然后 `py app.py`。

## 功能

- PDF 合并、按页拆分、按页提取、删除页、指定顺序重排、旋转、添加页码、添加文字水印、清除元数据。
- PDF 无损清理压缩；图像压缩（会将 PDF 页面转成图片，**丢失文字可编辑/可搜索性**）。质量选项：轻量 / 标准 / 高清 / 超清。
- PDF AES-256 加密 / 密码解锁（有正确密码）、PDF 转文本、Word（基础文字）、Excel（逐行文字）、PPT（图片页）、JPG 图片包（ZIP）、提取嵌入图片、图片转 PDF。
- Word 转 PDF **需要另外安装 LibreOffice**。该工具依赖 `soffice` 能被系统路径找到。
- 选择文件、选择保存目录与文件名（Windows 原生“另存为”对话框）。
- AI 文档助手：支持 PDF / TXT / DOCX 提取文本，用自填的 OpenAI 兼容 `chat/completions` API 地址、模型 ID、API Key 进行问答。分析结果可以另存为 TXT。
- API Key 使用 Windows 凭据存储（Python `keyring`），不会存进设置 JSON。API 地址与模型保存在 `%APPDATA%\oycy-PDF-Toolbox\settings.json`。

## 使用说明

打开软件 → `PDF 工具` → 选择功能 → 添加文件 → 设置参数 → `选择输出文件并开始处理`。多文件 PDF 合并时通过添加顺序控制；“上移/下移顺序”按钮当前是**循环移动整个列表**（不是任意拖动单项）。

在 `API 与设置` 选项卡填写 API Base URL、模型 ID 和密钥，点击保存。示例 `https://api.openai.com/v1`，模型名称必须是账号有权限调用的模型。可改用第三方 OpenAI 兼容提供商或本地服务地址（如 `http://localhost:11434/v1`），兼容性取决于服务端实现。

在 `AI 文档助手` 中选择文件并提交问题。软件会提取文本，并将最多前 60,000 个字符发送至配置的外部 API。**需要 API 服务商账户、Key 和网络，可能产生费用**。扫描件若没有文本层，不会自动 OCR。

## 限制和风险

- 本版是**可用桌面应用的源码项目**；在当前环境通过了语法检查，但未完成 Windows EXE 的实际构建和全面集成测试。
- 高保真 Office 布局恢复、OCR 扫描识别、原文字编辑、高级 PDF 无损压缩、数字签章、AI 批量工作流未实现。PDF 转 Word/Excel 是文字提取，PDF 转 PPT 是图片幻灯片。
- 转换大型文件可能耗时、消耗较多内存；AI API 当前单次提交文本前 60,000 个字符，不具备智能分块处理。
- 中文水印使用系统已安装字体。不同字体环境下外观可能不同。
- AI 密钥在 Windows 凭据存储，调用时送至所设置的 API；切勿输入不受信任的 API 地址。远程 API 强制 HTTPS。
- 使用前先用非敏感的 PDF 测试，并核对页数、排版和转换质量；重要文件保留原件。

## 可安装软件 vs 便携软件

此项目当前输出的是可双击运行的**便携 EXE**，不是 Windows MSI 安装向导。若需要带卸载器和桌面快捷方式的 Setup.exe，还需使用 Inno Setup / NSIS 打包并在 Windows 构建测试。

## 新版：合并 PDF 统一页面尺寸

合并 PDF 后各页在阅读器中忽大忽小，是因为原 PDF 的 `/MediaBox` 页面尺寸不同。**选择“高清/超清”并不能解决页面规格不一致**。

进入 **合并PDF**，在右侧“合并时统一页面尺寸”中选择：

- **A4 纵向（默认）**：适合证书、报告、扫描件等纵向材料混合，合并后每页页面宽高一致。
- A4 横向：适合演示文稿及横向扫描件。
- A3 纵向 / 横向、Letter 纵向：可按需要选择。
- 原始尺寸：保留每页原尺寸，并尽量保留原 PDF 的链接、批注。

统一模式将 PDF 内容**等比例缩放并居中**，预留约 6.35 mm 安全边距。若源页面较小，其内容会适当放大；原有低清晰度扫描图片的像素并不会因此增加。矢量图、可提取文字等通常维持原有清晰度和可搜索性；**但此模式不会复制 PDF 批注、链接和交互表单**，重要原件请备份。

输出质量的“轻量/标准/高清/超清”设置不影响此处的矢量页面统一方式。统一模式可能增加 PDF 文件大小。

升级 GitHub：替换仓库根目录 `app.py`；可一并上传 `test_merge_pages.py` 和新版 `.github/workflows/windows-build.yml`，让 Actions 自动检查不同原始页面尺寸合并为 A4 的正确性。无需在自己电脑安装 Python。

## 新增：页面排版编辑器与处理结果预览（2026-11）

此项目现在包含 `page_layout.py` 和 `page_editor_ui.py`，并在桌面程序右侧提供“页面排版编辑 / 实时预览”与“预览当前 PDF”按钮。

- **纸张规格**：原始尺寸、A4/A3 纵横向、Letter 纵横向，以及自定义毫米宽高（30–2000 mm）。
- **逐页局部编辑**：选择单页或多页，单独旋转 0/90/180/270°、等比例缩放、左/中/右、顶/中/底对齐，或直接拖动预览内的内容位置。
- **自动排版**：根据目标纸张决定方向，重置为居中与均匀留白；不是文字自动重新流式排版。
- **页面顺序**：编辑器内可移动、移除页面（不改动源 PDF）。
- **最终导出**：对「合并 PDF」使用实际逐页排版数据生成 PDF，使用矢量页面嵌入以尽量保留清晰文字；合并 PDF 完成后可打开输出结果预览，支持逐页浏览和缩放。
- **其他功能**：可预览源 PDF，输出为 PDF 的其他工具在处理成功后可选择查看结果；ZIP、Word、Excel、PPT 等非 PDF 输出目前仍需外部应用查看。局部页面排版数据**仅在“合并 PDF”工具导出中生效**，不自动作用于分割及其他工具。请留意软件状态栏提示。
- **限制**：矢量重组模式可能丢失批注、链接、交互表单以及部分可访问性结构；不进行扫描图片超分辨率重建；过大放大倍数被限制，以避免裁切。PDF 编辑器对页面内容进行整体布局，不提供原始文字段落的逐字编辑。

### 更新 GitHub 仓库

请将以下文件上传到现有仓库**根目录**覆盖同名文件：
`app.py`、`page_layout.py`、`page_editor_ui.py`、`test_page_layout.py`、`test_editor_gui.py`、`test_merge_pages.py` 和 `.github/workflows/windows-build.yml`。也建议更新 `README.md`。不要只替换 `app.py`，否则软件启动时会找不到新模块。

在 GitHub 的 Actions 中重新运行 `Build Windows executable`，下载 Artifact 内的新 `oycy-PDF-Toolbox.exe`。**本压缩包为源代码，不含已编译的 Windows EXE。** 构建时要求安装 requirements.txt 中的所有依赖。

当前环境已运行 Python 语法检查、原页面合并测试、布局输出测试、GUI 启动测试与编辑器打开/应用/预览测试；尚未在真实 Windows 上构建及验收 EXE。
