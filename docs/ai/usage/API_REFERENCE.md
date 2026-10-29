# 公共 API 参考

中文 | [English](API_REFERENCE.en.md)

适用 `py-skia-canvas==0.1.0a18`，兼容基线为官方 Node `skia-canvas@3.0.8`。本页用于 AI 选取常用签名、理解数据与生命周期；特殊重载和逐项兼容状态见 [公共 API 清单](../../public-api-ledger.json)、[alpha 状态](../../alpha-api-status.json) 和 [Python 宿主对应](../../PYTHON_HOST_PROFILE.md)。不要根据浏览器 Canvas 或其他 Python 绘图库推测本库接口。

## 1. 导入与宿主约定

```python
from py_skia_canvas import (
    Canvas, CanvasRenderingContext2D, TextMetrics, Path2D,
    CanvasGradient, CanvasPattern, CanvasTexture, FontLibrary,
    DOMMatrix, DOMPoint, DOMRect, Image, ImageData,
    loadImage, loadImageData, App, Window, undefined,
)
```

上游有 17 个运行时导出；Python 提供这些对应入口，另公开 `undefined` 单例。通常由 `Canvas.getContext()`、`ctx.create*()` 和 `ctx.measureText()` 获得相关对象。

| Node 概念 | Python 对应 | 使用要点 |
| --- | --- | --- |
| Buffer / Uint8ClampedArray | `bytes` / `ImageData.data` 像素视图 | 编码字节与 raw 像素分开处理 |
| Promise | 可 `await` 的导出对象；加载函数也可等待 | 用 `async def main()` 包围异步程序 |
| undefined / null | `undefined` / `None` | 省略参数、显式空值可能有不同结果；不要统一替换 |
| 普通 JS 对象/数组 | `dict` / `list` 等对应值 | `metrics.lines[0]["x"]`，使用字典键访问 |
| 文件路径 | 通常 `str`；导出也接受 `os.PathLike` | 字体注册传字符串路径 |
| Sharp | 同名入口报缺少 Node Sharp 依赖 | 取得 bytes，再交给应用选择的 Python 工具 |

数值默认保留原实现转换与校验；部分非法值沿用忽略赋值/不绘制行为，部分抛异常。常见 Python 捕获类型为 `TypeError`、`ValueError`、`RuntimeError`，以及文件/网络异常；未支持的宿主特例可能抛 `NotImplementedError`。不要把所有无效输入都预期为相同异常。`SKIA_CANVAS_STRICT=1` 须在进程启动/导入前设置，改变原实现的非法参数处理，适合诊断和兼容测试。

以下“owner”指创建原生对象的线程。Canvas、Context、Path、Image、Gradient、Pattern、Texture 的原生访问都在 owner；跨线程会报错。普通 DOM 值、TextMetrics、已取得的 bytes 和 ImageData 像素存储没有 GPU context；共享可变数据仍由应用同步。

## 2. Canvas 与页面

| 入口 | 参数与返回 | 语义 |
| --- | --- | --- |
| `Canvas(width=300, height=150, options=undefined)` | 宽高为 canvas units；返回 Canvas | options 包含 `textContrast`、`textGamma`、`gpu`；保留原默认 GPU 策略 |
| `getContext("2d")` | 返回当前页 Context | 其他 context 类型返回 `None` |
| `newPage()` / `newPage(width, height)` | 返回新页 Context | 新页成为当前页；原页面保留 |
| `pages` | 按创建顺序排列的 Context 列表 | 取得列表不等于复制所有原生画面 |
| `width` / `height` | 读写逻辑宽高 | 赋值会重置当前页；先定尺寸再绘制 |
| `engine` | 复制的 backend/设备/文字设置字典 | 看 `renderer` 为 `GPU` 还是 `CPU`；不等于逐次 native 调用 trace |
| `gpu` | 读写开关 | 明确用 CPU 时，在绘制前设置 `canvas.gpu = False` |

默认文字选项为 `textContrast=0`、`textGamma=1.4`。保留 3.0.8 的兼容行为：构造参数 `{"gpu": False}` 不能可靠强制 CPU；使用 setter。无 GPU 时离屏任务自动回退 CPU。

Context 的 `.canvas` 是弱父对象访问。保留 Canvas 引用直到绘制和导出调用完成。页面尺寸可不同；不要在每页绘制后再修改 Canvas 宽高。

来源：[Canvas facade](../../../python/py_skia_canvas/_canvas_api.py)、[公共入口](../../../python/py_skia_canvas/__init__.py)、[共享 Canvas 核心](../../../crates/canvas-core/src/canvas.rs)。

## 3. Context：路径、绘制和变换

所有位置/长度为 canvas units；角度为弧度。通常绘制方法返回 `None`，查询方法返回下表指定的值。参数数量、半径、数值有效性及 owner 错误按原实现处理。

| 类别 | 常用签名 | 作用 |
| --- | --- | --- |
| 矩形 | `fillRect(x,y,w,h)`、`strokeRect(...)`、`clearRect(...)` | 填充、描边或清除区域 |
| 当前路径 | `beginPath()`、`closePath()`、`moveTo(x,y)`、`lineTo(x,y)` | 组织当前路径；beginPath 清空当前路径 |
| 曲线 | `bezierCurveTo(c1x,c1y,c2x,c2y,x,y)`、`quadraticCurveTo(cx,cy,x,y)` | 三次/二次 Bézier |
| 圆弧 | `arc(x,y,r,start,end,ccw=False)`、`arcTo(x1,y1,x2,y2,r)` | 圆弧与圆角连接 |
| 椭圆 | `ellipse(x,y,rx,ry,rotation,start,end,ccw=False)` | 旋转角及起止角均为弧度 |
| 矩形路径 | `rect(x,y,w,h)`、`roundRect(x,y,w,h,radii)` | 添加路径；尚未自动填充 |
| 绘制/裁剪 | `fill()`、`fill(path)`、`stroke()`、`stroke(path)`、`clip()`、`clip(path)` | fill/clip 可使用 `"nonzero"` / `"evenodd"` 规则重载 |
| 命中测试 | `isPointInPath(x,y)`、`isPointInPath(path,x,y)`、`isPointInStroke(...)` | 返回 `bool`；路径可选 |
| 状态 | `save()`、`restore()`、`reset()` | 保存/恢复状态，或按原语义重置 Context |
| 变换 | `translate(x,y)`、`scale(x,y)`、`rotate(radians)` | 更新当前变换 |
| 矩阵 | `transform(a,b,c,d,e,f)`、`setTransform(...)`、`resetTransform()`、`getTransform()` | get 返回 DOMMatrix；也支持相应对象重载 |

`save/restore` 用来限定样式、裁剪和变换，不能当作像素撤销历史。每个场景片段明确设置必要状态。

| 样式属性 | 常用值/含义 |
| --- | --- |
| `fillStyle` / `strokeStyle` | CSS 颜色、CanvasGradient、CanvasPattern、CanvasTexture；默认黑色 |
| `lineWidth` / `lineCap` / `lineJoin` / `miterLimit` | 默认 `1` / `"butt"` / `"miter"` / `10` |
| `setLineDash(list)` / `getLineDash()` / `lineDashOffset` | 长度为 canvas units；get 返回独立列表；奇数段按原规则复制 |
| `lineDashMarker` / `lineDashFit` | Path2D marker 与原扩展的虚线适配策略 |
| `globalAlpha` | 0–1，默认 1 |
| `globalCompositeOperation` | 默认 `"source-over"`；如 `"multiply"`、`"screen"` 等原混色模式 |
| `filter` | CSS filter 字符串，如 `"blur(2px)"`；默认 `"none"` |
| `shadowColor` / `shadowBlur` / `shadowOffsetX/Y` | CSS 颜色、模糊及偏移；偏移为 canvas units |
| `imageSmoothingEnabled` / `imageSmoothingQuality` | 图像缩放采样控制 |

来源：[Context 公共接口](../../../python/py_skia_canvas/__init__.py)、[参数规格](../../../python/py_skia_canvas/_argument_specs.py)、[效果绑定](../../../python/py_skia_canvas/_effects.py)、[共享 Context](../../../crates/canvas-core/src/context)。

## 4. Path2D、渐变、pattern 与 texture

| 对象/入口 | 返回及用法 |
| --- | --- |
| `Path2D()` / `Path2D(svg_string)` / `Path2D(path)` | 空路径、SVG 路径或原 COW 复制；原生操作限 owner |
| Path 的 `moveTo/lineTo/arc/ellipse/rect/roundRect/...` | 构造路径，通常返回 `None`；参数单位与 Context 对应方法一致 |
| `path.d` | 读写 SVG path 字符串；构造无效 SVG 与给已有对象设置无效 SVG 的行为不同 |
| `path.bounds` / `path.edges` | 返回 Python 拥有的边界 dict / 路径指令数据；不持有可跨线程绘制的原生 Path |
| `path.contains(x,y)` | 返回点是否在路径内的 `bool` |
| `path.addPath(other, matrix)` | 向原路径添加另一路径；矩阵参数有省略重载 |
| `path.transform(matrix)` | 返回变换后的新 Path2D |
| `difference/intersect/union/xor/complement(other)` | 返回布尔运算后的新 Path2D；不要假定原路径已原地改变 |
| `simplify/unwind/offset/round/trim/jitter/points` | 原路径扩展；特殊参数先查源码签名/ledger，不套用其他库同名算法 |
| `ctx.createLinearGradient(x0,y0,x1,y1)` | 返回 CanvasGradient |
| `ctx.createRadialGradient(x0,y0,r0,x1,y1,r1)` | 返回 CanvasGradient；半径为 canvas units |
| `ctx.createConicGradient(angle,x,y)` | angle 为弧度，返回 CanvasGradient |
| `gradient.addColorStop(offset, color)` | offset 在 0–1，color 为 CSS 字符串；按原 f32 边界校验，返回 `None` |
| `ctx.createPattern(source, repetition)` | 图像/Canvas 等来源；显式传 `"repeat"`、`"repeat-x"`、`"repeat-y"` 或 `"no-repeat"` |
| `pattern.setTransform(matrix)` | 更新平铺变换；与共享样式引用的关系保留原实现 |
| `ctx.createTexture(spacing, options)` | 间距可为数值或二元数组；返回 CanvasTexture |

texture options 常用 `path`、`color`、`line`、`cap`、`angle`、`offset`、`outline`。间距、线宽和偏移为 canvas units，`angle` 为弧度。优先通过 Context 的工厂创建样式对象，不猜测公开类的低层构造参数。

来源：[Path](../../../python/py_skia_canvas/_path.py)、[Gradient](../../../python/py_skia_canvas/_gradient.py)、[Pattern/Texture](../../../python/py_skia_canvas/_shaders.py)。组合用法见 `paths`、`images`、`effects` [示例](DEMOS.md)。

## 5. 文本、TextMetrics 与 FontLibrary

| 入口 | 返回/单位/要点 |
| --- | --- |
| `ctx.font` | CSS 字体字符串，如 `"24px sans-serif"`；默认 `"10px sans-serif"` |
| `fillText(text,x,y[,maxWidth])` / `strokeText(...)` | 绘制；x/y 和 maxWidth 为 canvas units；y 受 textBaseline 控制 |
| `measureText(text[,maxWidth])` | 返回 TextMetrics；测量时使用与绘制相同的字体、排版状态及宽度 |
| `outlineText(text[,maxWidth])` | 返回文字轮廓 Path2D；位置由后续路径/Context 变换安排 |
| `textAlign` / `textBaseline` / `direction` | 常用 `left/center/right/start/end`、`alphabetic/top/middle/...`、`ltr/rtl/inherit` |
| `textWrap` | `True` 配合 maxWidth 启用原多行排版 |
| `fontStretch` / `fontVariant` / `fontHinting` | 原文字扩展状态 |
| `letterSpacing` / `wordSpacing` / `textDecoration` | CSS 间距与装饰描述；先查实际接受的字符串形式 |
| `textTracking` | 保留的上游旧扩展；新代码优先使用明确的间距属性 |

TextMetrics 的 `width`、`actualBoundingBoxLeft/Right/Ascent/Descent`、`fontBoundingBoxAscent/Descent`、`emHeightAscent/Descent`、各 baseline 为 canvas units。`lines` 是行数据列表，其子对象用字典键访问，索引信息遵循 UTF-16 code units。初始顶层字段只读，嵌套列表/字典保持普通可变数据语义；这不是深度不可变结构。

| FontLibrary 入口 | 作用 |
| --- | --- |
| `FontLibrary.use(file_or_list)` | 注册一个或多个字符串路径，返回字体元数据 |
| `FontLibrary.use(alias, file_or_list)` | 用给定 family alias 注册 |
| `FontLibrary.use({alias: file_or_list})` | 注册多组 alias |
| `FontLibrary.families` | 当前可见 family 名称列表快照 |
| `FontLibrary.has(name)` | 按原名称匹配查询 family；不证明字符覆盖 |
| `FontLibrary.family(name)` | family 元数据，未找到返回 `undefined` |
| `FontLibrary.reset()` | 清除调用线程的自定义字体和相关缓存 |

FontLibrary 是单例入口，**注册及缓存属于调用线程**。线程池应在每个绘制 worker 注册所需字体。无效文件、不可读文件、错误参数按原输入/文件错误处理。系统字体可能合法用于本机渲染，但不自动获得再分发授权。

来源：[文本入口](../../../python/py_skia_canvas/_text_api.py)、[文字状态](../../../python/py_skia_canvas/_text_state.py)、[Metrics](../../../python/py_skia_canvas/_metrics.py)、[字体](../../../python/py_skia_canvas/_fonts.py)。

## 6. Image、ImageData 与像素

| 入口 | 参数与返回 |
| --- | --- |
| `await loadImage(source[, options])` | 编码 bytes、本地路径、data URL、HTTP URL → 已加载的 Image |
| `Image(encoded_bytes)` | 同步解码已取得的编码图像；Image 的原生访问限 owner |
| `image.src = source` / `await image.decode()` | 加载/等待图像；decode 返回 Image；支持原 onload/onerror 生命周期 |
| `image.width` / `height` / `complete` | 已解码尺寸/加载状态；加载完成后再绘制 |
| `ImageData(width,height[,settings])` | 分配像素存储；默认 `rgba/srgb` |
| `ImageData(raw_bytes,width,height[,settings])` | 从 raw 像素建立数据；长度/格式必须匹配 |
| `ImageData(image)` / `ImageData(other_data)` | 从图像读回或复制像素 |
| `image_data.data` | 固定长度可写的 clamped 字节视图；不是 PNG/JPG 字节 |
| `await loadImageData(source,width,height[,settings])` | 取得 raw 像素后建立 ImageData；不解码 PNG |
| `ctx.createImageData(width,height[,settings])` | 按尺寸创建空像素存储；复制已有存储用 `ImageData(other_data)` |
| `ctx.getImageData(x,y,w,h[,settings])` | 读回独立 ImageData；默认 rgba 每像素 4 字节 |
| `ctx.putImageData(data,dx,dy[,dirtyX,dirtyY,dirtyW,dirtyH])` | 直接写像素；不要按 drawImage 的变换/混色规则理解 |
| `ctx.drawImage(source,...)` | 原 3/5/9 参数形式，见使用指南 |
| `ctx.drawCanvas(...)` | 原 Canvas 绘制扩展；需要此重载时查 ledger/源码 |

ImageData 的 `width/height/colorSpace/colorType` 为只读元数据。`settings` 的格式名称区分大小写；处理常规 RGBA 时显式使用 `{"colorType":"rgba"}` 可避免对默认布局的误解。其他像素格式要按实际字节数/通道布局处理，不能一律当 RGBA。

图像和网络异常应传播给调用者；不以空图代替加载成功。Python 网络宿主选项与 Node Agent/Stream 对象不等价，详见宿主对应文档。

来源：[图像与像素](../../../python/py_skia_canvas/_imagery.py)、[Python HTTP 宿主](../../../python/py_skia_canvas/_http.py)。

## 7. 导出

| 同步入口 | 异步对应 | 返回值 |
| --- | --- | --- |
| `toBufferSync(extension="png", opts=undefined)` | `toBuffer(...)` | bytes / await bytes |
| `toFileSync(filename, opts=undefined)` | `toFile(...)` | None / await None |
| `toURLSync(extension="png", opts=undefined)` | `toURL(...)` | data URL str / await str |
| `toDataURL(extension="png", quality=undefined)` | — | 同步 data URL；此旧浏览器式入口第二项是 quality |

`canvas.png/jpg/webp/pdf/svg/raw` 是可等待的属性，例如 `png = await canvas.png`。新代码优先用带显式格式和 options 的规范入口。`toSharp()` 需要 Node Sharp，独立 Python 包明确抛缺依赖错误。

| options 键 | 默认/范围 | 含义 |
| --- | --- | --- |
| `quality` | `0.92`，0–1 | 原编码器的有损质量选项，不是所有格式都使用 |
| `density` | `1`，正整数 | raster 输出倍率；2× 的宽高各扩大 2 倍 |
| `matte` | 未指定 | CSS 背景底色；用于合成/不透明输出 |
| `page` | 未指定 | 1-based，负数从末页计数；省略时 PDF 多页、其他单文件最新页 |
| `outline` | False | PDF/SVG 文字轮廓选项 |
| `downsample` | False | 原矢量导出中的图像处理选项 |
| `colorType` | 原格式默认 | raw 像素布局；与 ImageData 的格式名对应 |
| `msaa` | 原设备默认 | 原 GPU 采样选项，支持值与设备有关；不能当作 CPU 渲染开关 |
| `format` | 从 filename 推断 | 文件入口可显式指定格式 |

格式为 `png/jpg/webp/raw/pdf/svg`；PNG/JPG/WebP 为编码图像，raw 不包含宽高等元数据。文件名支持 `page-{2}.png` 的补零页面序列，支持 `@2x` 等密度推断；AI 生成代码时优先显式 options。

异步导出调用须在 owner；原核心在调用时建立可转移的画面快照，后续修改画布不改变旧任务。结果可重复等待，取消一个等待者不保证取消底层编码。`ExportPromise` 是 awaitable，不保证可直接传给 `asyncio.run/create_task`；包一层 coroutine 即可。

缺格式、无效 options、越界页码、不可写路径和编码失败均需处理。Windows 默认并发 PDF/SVG 文件序列继承原版漏字限制；需要时显式部署 `RAYON_NUM_THREADS=1`，详见[排错](TROUBLESHOOTING.md)。

来源：[导出归一化与异步 facade](../../../python/py_skia_canvas/_exports.py)、[共享 Page 核心](../../../crates/canvas-core/src/context/page.rs)。

## 8. DOM 值对象

| 对象 | 常用入口与单位 |
| --- | --- |
| `DOMPoint(x=0,y=0,z=0,w=1)` | 点值；`matrixTransform(matrix)` 返回变换结果；`toJSON()` 返回普通数据 |
| `DOMRect(x=0,y=0,width=0,height=0)` | 矩形值；left/top/right/bottom 为派生边界；支持 fromRect/toJSON |
| `DOMMatrix()` | 默认单位矩阵；可用 6/16 元素序列、CSS transform 字符串构造 |
| Matrix 属性 | `a,b,c,d,e,f`、`m11...m44`、`is2D`、`isIdentity` |
| Matrix 操作 | `translate/scale/rotate/skewX/skewY/multiply/...` 及其 Self 形式；通常不带 Self 返回新矩阵 |
| 转换 | `transformPoint(point)`、`toFloat32Array()`、`toFloat64Array()`、`toJSON()`、`toString()` |

矩阵旋转和 skew 使用**角度**，平移使用调用场景的坐标单位。保留上游特殊行为：`invertSelf()` 在可逆 2D 情况返回新矩阵而不改变原对象；奇异矩阵会写入 NaN 并返回 `undefined`；3D 求逆报未实现错误。不要仅按方法名假定所有 Self 方法遵循浏览器标准。

来源：[DOM 数据](../../../python/py_skia_canvas/_geometry.py)、[原矩阵运算对应](../../../python/py_skia_canvas/_matrix_ops.py)。

## 9. App / Window

App 是单例，Window 是主线程 GPU/桌面对象。CPU 离屏能力不包含软件窗口呈现。

| 入口 | 行为 |
| --- | --- |
| `Window(width,height,options)` / `Window(options)` | 默认 512×512；options 可含 title、visible、resizable、background、canvas 等 |
| `window.canvas` / `window.ctx` / `window.page` | 关联画布、选中页 Context、1-based 页码 |
| `window.on(event,callback)` / `once` / `off` | 监听原绘制、窗口、鼠标、键盘等事件 |
| `window.on("draw", callback)` | callback 接收事件；使用 `event.frame`；每帧重新设置所需绘图状态 |
| `window.close()` / `open()` | 关闭/打开；会影响 App 会话是否继续 |
| `App.fps` | 绘制帧率设置 |
| `App.windows` / `App.running` / `App.eventLoop` | 活动窗口列表、曾启动标记、原事件循环模式名 |
| `App.launch()` | 返回可等待会话；可用 `asyncio.run(App.launch())` |
| `App.quit()` | 请求退出 |

尺寸为逻辑窗口/画布单位；实际像素还受桌面缩放影响。原生后端不可用时明确失败，例如 `No windowing support`。完整自动结束示例见 [ai_demos.py](../../../examples/ai_demos.py)，不要把没有调用事件循环的构造代码当作窗口运行成功。

`App.running` 保留原“曾启动”标记，进入 idle 后仍可为 True；不要仅用它判断窗口仍在运行。

来源：[GUI](../../../python/py_skia_canvas/_gui.py)、[事件对应](../../../python/py_skia_canvas/_events.py)。
