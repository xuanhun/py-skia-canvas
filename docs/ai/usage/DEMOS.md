# 示例与任务配方

完整可运行程序：[examples/ai_demos.py](../../../examples/ai_demos.py)。只依赖 Python 标准库和已发布的 `py-skia-canvas==0.1.0a18`。示例中的输入图像由 Canvas 生成，没有外网请求或随包字体。

## 运行方式

在仓库根目录运行；`--out` 使用新的目录：

```shell
python examples/ai_demos.py hello --out test-runs/my-hello-001
python examples/ai_demos.py all --out test-runs/my-gallery-001
python examples/ai_demos.py all --backend cpu --out test-runs/my-cpu-001
python examples/ai_demos.py all --backend gpu --out test-runs/my-gpu-001
python examples/ai_demos.py window --out test-runs/my-window-001
```

`auto` 为默认，保留库自动选择；`cpu` 使用公开 setter；`gpu` 要求实际报告 GPU，否则失败。`all` 运行九个离屏示例，窗口通过独立命令或 `--include-window` 明确启用。`window --hidden` 用于验证隐藏窗口，仍需要桌面/GPU。请求 CPU 窗口会明确报错。

`--font-file /absolute/path/to/font.ttf` 可演示在当前线程注册用户提供的合法字体，`text` 示例使用 `DemoFace` alias。示例不会复制字体到输出目录。

## 示例目录

| 命令 | 展示的调用 | 输出与可检查结果 |
| --- | --- | --- |
| `hello` | Canvas、fillRect、fillText、getImageData | 360×180 `preview.png`；对蓝色色块内部 RGBA 做精确断言 |
| `paths` | Path2D、difference、gradient、DOMMatrix、save/restore | 圆环、变换三角形、旋转矩形；显式 evenodd 填充，验证内外点和圆心背景像素 |
| `text` | font、measureText、textWrap、direction、textDecoration | 多语言排版 PNG 与宽度/升降部/行数；受系统字体影响 |
| `images` | await loadImage、三类 drawImage、pattern、ImageData | 缩放、裁剪、平铺和 raw 红像素；检查读回 RGBA |
| `effects` | shadow、filter、multiply、globalAlpha、texture | 阴影/叠色/线纹；局部状态用 save/restore 包围 |
| `exports` | toBufferSync 六格式、density、toURLSync | PNG/JPG/WebP/raw/PDF/SVG、720×360 的 2× PNG、data URL 前缀 |
| `pages` | newPage、pages、page、文件序列 | 三页 `pages.pdf`、`page-01.png` 等、first/last PNG |
| `async` | toBuffer、asyncio.gather、await toFile | 修改前后两个快照 PNG 和 PDF；两个快照必须不同 |
| `batch` | 各 worker 内创建/绘制/编码 | 三个 PNG；跨线程只传 bytes 和复制的 engine 数据 |
| `window` | Window、draw 事件、App.launch、close | 五帧左右自动关闭，保存最后一帧 PNG |

每个示例生成 `result.json`：版本、请求的 backend、实际 engine、文件字节数/SHA、PNG 尺寸，以及该示例的指标。顶层 `summary.json` 记录本次执行的示例集合。输出目录已存在会失败，避免覆盖先前结果。

## 实际输出图册

以下 PNG 直接复制自 **0.1.0a18 Windows Vulkan GPU** 的示例输出，没有重新绘制或后期修图。Linux、GPU/CPU 的实际执行范围见[验证记录](../VALIDATION.md)；系统字体不同可使文字外观变化。图像存放在仓库 [assets](../assets/README.md)，不依赖本机测试目录；每张的尺寸、SHA 和原始输出位置见 [manifest.json](../assets/manifest.json)。

### hello：第一张图

```shell
python examples/ai_demos.py hello --out test-runs/NEW_HELLO
```

360×180；显式白底、蓝色色块、文本和精确内部像素断言。

![360×180 hello 绘图：蓝色色块与 Hello Canvas](../assets/hello.png)

### paths：布尔路径、渐变与变换

```shell
python examples/ai_demos.py paths --out test-runs/NEW_PATHS
```

520×280；圆环使用 difference 和显式 `evenodd` 填充规则，圆心保留背景；三角形用 DOMMatrix 的角度变换，描边矩形用 Context 的弧度旋转。

![渐变圆环、旋转三角形与描边矩形](../assets/paths.png)

### text：测量、换行与多语言

```shell
python examples/ai_demos.py text --out test-runs/NEW_TEXT
```

560×300；包含组合字符、中文、阿拉伯文、emoji、下划线和 RTL 对齐。这里是该平台系统字体的实际结果；指定字体注册方式见 `--font-file`。

![多语言文本、换行、下划线和右对齐阿拉伯文](../assets/text.png)

### images：缩放、裁剪、平铺与像素

```shell
python examples/ai_demos.py images --out test-runs/NEW_IMAGES
```

560×280；左边是生成后重新加载的棋盘图，中间为裁剪，右侧为 pattern，左下红点来自 ImageData 像素写入。

![棋盘图缩放、黄色裁剪、蓝黄平铺及红色像素块](../assets/images.png)

### effects：阴影、滤镜、混色和线纹

```shell
python examples/ai_demos.py effects --out test-runs/NEW_EFFECTS
```

560×260；依次展示阴影、模糊与 multiply 叠色、程序化 texture。

![阴影色块、模糊叠色和斜线 texture](../assets/effects.png)

### exports：同一场景的多格式输出

```shell
python examples/ai_demos.py exports --out test-runs/NEW_EXPORTS
```

这里嵌入 360×180 的 `scene.png`；同目录还生成 JPG/WebP/raw/PDF/SVG，以及 720×360 的 2× PNG。Markdown 预览不能证明 PDF/SVG 文件内容，示例和发行测试分别检查对应产物。

![多格式导出演示场景 One scene, six formats](../assets/exports.png)

### pages：三页文档

```shell
python examples/ai_demos.py pages --out test-runs/NEW_PAGES
```

同一 Canvas 的三页各为 480×240；同时输出单个三页 PDF、PNG 序列和显式首/末页 PNG。

| 第 1 页 | 第 2 页 | 第 3 页 |
| --- | --- | --- |
| ![浅蓝背景 Page 1](../assets/page-1.png) | ![浅黄背景 Page 2](../assets/page-2.png) | ![浅绿背景 Page 3](../assets/page-3.png) |

### async：调用时快照

```shell
python examples/ai_demos.py async --out test-runs/NEW_ASYNC
```

两个 240×120 PNG 来自同一画布在修改前后发起的任务。即使一起等待，第一次导出仍是红色快照，第二次是绿色快照。

| 修改前发起的导出 | 修改后发起的导出 |
| --- | --- |
| ![第一次导出的红色画面](../assets/async-before.png) | ![第二次导出的绿色画面](../assets/async-after.png) |

### batch：各 worker 内独立渲染

```shell
python examples/ai_demos.py batch --out test-runs/NEW_BATCH
```

两个 worker 完成三个任务，各自创建 Canvas、绘制并取得 PNG；任务只返回 bytes 和 engine 数据。

| 任务 1 | 任务 2 | 任务 3 |
| --- | --- | --- |
| ![任务 1 蓝色色块](../assets/batch-1.png) | ![任务 2 橙色色块](../assets/batch-2.png) | ![任务 3 绿色色块](../assets/batch-3.png) |

### window：GPU 窗口最后一帧

```shell
python examples/ai_demos.py window --out test-runs/NEW_WINDOW
```

480×300 的 Canvas 最后一帧，通过真实窗口事件循环绘制后保存；图片本身不包含操作系统窗口边框。示例数帧后关闭；自动化运行可加 `--hidden`，仍需要 GPU/桌面。

![窗口示例最后一帧的 Canvas 输出](../assets/window.png)

## AI 生成代码时的配方

### 图文卡片 / 统计图

先选定画布大小和字体；创建 Canvas 与 Context；用路径/矩形组织图形；测量标题后定位；最后导出。可组合 `hello`、`paths`、`text`。图表数据先由应用转换为坐标，再交给 Canvas；库没有 PPT/图表业务模型。

### 处理用户图片

在 `async def` 中加载 `image = await loadImage(path)`；根据 `image.width/height` 计算目标区域；使用 5 参数缩放或 9 参数裁剪。把照片解码和 raw 像素处理分开，见 `images`。较大图片应由应用限制资源规模与并发量。

### 批量报表

每个任务独立创建 Canvas；需要多页时调用 `newPage()`；导出单个 PDF 或明确的页面 PNG 序列。对 Windows 矢量文件序列应用已记录的显式串行设置。见 `pages`、`exports`、`batch`。

### Web/API 返回图片

在请求的 owner 线程完成绘制，再取得 `bytes` 交给 Web 框架响应。异步导出可以在相同事件循环中等待；不要把已创建的 Canvas 交给框架的另一个线程。响应头使用实际 MIME，例如 PNG 的 `image/png`。框架集成代码由调用方提供，本示例不依赖 Web 框架。

### 交互窗口

使用 `Window` 自带的 `ctx`。draw 回调在主线程执行，每帧重新设置必要状态；需要持续动画时调整示例的自动关闭条件。无桌面/GPU 的运行环境使用离屏任务，不将窗口失败转换为“窗口测试通过”。

## 示例运行与兼容验收的区别

示例验证了公开 API 的组合用法和输出断言。它不自动证明全部上游契约或当前驱动的所有渲染路径。修改库的 AI 应进入[开发测试流程](../development/TESTING_AND_RELEASE.md)，使用固定 Node A、同字体/后端、无容差差分以及真实 native 观测。
