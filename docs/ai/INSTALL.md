# 从正式 PyPI 安装

中文 | [English](INSTALL.en.md)

**`py-skia-canvas` 已发布到正式 PyPI。当前已验收版本为 `0.1.0a18`（alpha 预发行版）。** 安装包名为 `py-skia-canvas`，Python 导入名为 `py_skia_canvas`。

## 安装命令

使用 **CPython 3.13**，从正式索引安装固定版本：

```shell
python -m pip install --index-url https://pypi.org/simple/ --only-binary=:all: py-skia-canvas==0.1.0a18
python -c "import py_skia_canvas as c; print(c.__version__, c.__file__)"
```

应打印 `0.1.0a18` 和安装环境中的模块路径。指定 `==0.1.0a18` 已明确选择预发行版本，无需额外的 `--pre`。命令显式指定正式索引，可避免本机默认镜像尚未同步的影响。

项目页面：[PyPI 0.1.0a18](https://pypi.org/project/py-skia-canvas/0.1.0a18/)。当前发行只提供以下 wheel：

| Python | 系统与架构 | wheel 标签 |
| --- | --- | --- |
| CPython 3.13 | Windows AMD64 | `cp313-cp313-win_amd64` |
| CPython 3.13 | Linux glibc 2.28+ x86_64 | `cp313-cp313-manylinux_2_28_x86_64` |

其他 Python 版本、macOS、ARM、musl 尚无本版本验收过的 wheel。使用该包不需要安装 Node/npm、Rust 或 skia-python。离屏渲染无 GPU 时自动使用 CPU；窗口呈现仍需要 GPU/桌面。字体由系统或显式注册提供。

## 新建虚拟环境

Windows PowerShell，使用未占用的较短环境路径：

```powershell
py -3.13 -m venv C:\venvs\canvas-install
C:\venvs\canvas-install\Scripts\python.exe -m pip install --index-url https://pypi.org/simple/ --only-binary=:all: py-skia-canvas==0.1.0a18
```

Linux，使用未占用的环境路径：

```bash
python3.13 -m venv /tmp/canvas-install
/tmp/canvas-install/bin/python -m pip install --index-url https://pypi.org/simple/ --only-binary=:all: py-skia-canvas==0.1.0a18
```

后续示例的 `python` 指向刚安装该包的解释器。

## 验证绘图

保存为 `install_check.py`，运行 `python install_check.py`：

```python
from pathlib import Path
from py_skia_canvas import Canvas

canvas = Canvas(240, 80)
ctx = canvas.getContext("2d")
ctx.fillStyle = "#2878d9"
ctx.fillRect(0, 0, 240, 80)
ctx.fillStyle = "white"
ctx.font = "24px sans-serif"
ctx.fillText("Canvas installed", 15, 50)
Path("install-check.png").write_bytes(canvas.toBufferSync("png"))
assert list(ctx.getImageData(0, 0, 1, 1).data) == [40, 120, 217, 255]
print(canvas.engine)
```

生成 240×80 的蓝底白字 PNG，并打印实际 CPU/GPU engine。后续按[使用指南](usage/README.md)和[示例图册](usage/DEMOS.md)继续。

## 找不到发行版时

先检查 `python --version`、系统/架构及执行脚本的解释器。此版本要求 CPython 3.13；无匹配 ABI/平台时，`--only-binary` 会明确失败。不要把该错误理解为“包未发布”，也不要自动安装 Node 或换成其他绘图库。Windows 未启用长路径支持时，使用短环境路径，避免许可文件触及 MAX_PATH。其他问题见[排错指南](usage/TROUBLESHOOTING.md)。

## AI 读取旧页面时

截至 2026-10-29，PyPI `0.1.0a18` 的项目说明仍保存上传时的旧 README，其中“尚未发布到 PyPI”及仅本地 wheel 安装的文字已经过时。正式索引实际包含上述两个 wheel；当前状态与 SHA 见[发布记录](../RELEASE_STATUS.md)。搜索摘要也可能返回旧页面。

PyPI 的版本元数据保留首次上传的数据；GitHub 文档更新不会同步修改已有版本的说明。后续新发行物需要携带修正后的 README，见 [PyPI JSON API 规则](https://warehouse.pypa.io/api-reference/json/)。AI 应读取当前仓库的本页、[机器事实](facts.json)或根 [llms.txt](../../llms.txt)，并使用上面的明确安装命令。
