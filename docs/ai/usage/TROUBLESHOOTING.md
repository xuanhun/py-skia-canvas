# 使用排错

中文 | [English](TROUBLESHOOTING.en.md)

记录 `python --version`、包版本与文件路径、操作系统/架构、`canvas.engine`、输入尺寸/格式及异常全文。最小程序优先只画一个不透明矩形，再逐步加入文本、图像、效果和多页。

| 现象 | 排查顺序与处理 |
| --- | --- |
| pip 提示没有匹配发行物 | 确认 CPython 3.13、Windows AMD64 或 glibc 2.28+ Linux x86_64；使用固定 `==0.1.0a18`；首发没有其他 ABI wheel 或 PyPI sdist |
| Windows 安装许可文件时报路径不存在/过长 | 使用较短虚拟环境路径；参考 MAX_PATH 部署边界，不需要重编渲染器 |
| import 后版本或路径不符 | 核对运行脚本的解释器；检查 `py_skia_canvas.__version__` / `__file__`；确认当前目录没有同名文件/旧包遮蔽 |
| engine 是 CPU | 离屏应用可正常使用原 CPU 回退。若任务明确要求 GPU/窗口，再检查驱动、Vulkan 与桌面，并保留真实缺项 |
| 设置构造 `gpu=False` 后仍有 GPU 行为 | 使用创建后的 `canvas.gpu = False`；构造标记保留上游 3.0.8 的行为差异 |
| Window 报 No windowing support | 该原版呈现后端需要 GPU/桌面；确认在主线程创建，服务器任务用离屏 Canvas |
| 中文/emoji 缺字、换行与另一台机器不同 | 核对同一字体文件、face/alias、注册线程和实际字符覆盖；`FontLibrary.has` 只检查 family；不要给 shaping 添加逐字补偿 |
| 图像尺寸为零或图没出现 | `await loadImage(...)` / `await image.decode()` 完成后绘制；检查源数据是编码图像还是 raw、路径是否可读 |
| 像素颜色/长度不符 | 默认 ImageData 是 rgba/srgb，每像素四字节；显式 colorType 改变布局；注意 alpha、matte 和颜色空间，不把任意 raw 当 PNG |
| 文字位置偏移 | `fillText` y 是所选 baseline；设置 font/textBaseline/textAlign 后用同一参数测量；注意 DOMMatrix 角度与 Context 弧度 |
| 保存结果只有最后一页 | 非 PDF 单文件默认最新页；选 `page=1` 或使用 PNG 文件序列；PDF 可包含全部页 |
| 调整宽高后图/状态变化 | 尺寸 setter 重置当前页；在绘制前确定尺寸，或显式重绘 |
| 传 opts=None 报错 | None 对应 JS null；省略参数或用字典，而不是将 None 当作“默认 options” |
| Coroutine/awaitable 调用报 asyncio.run 类型错误 | 在 `async def main()` 中 `await canvas.toBuffer(...)`，再 `asyncio.run(main())` |
| 跨线程 RuntimeError | 在对象创建线程使用；worker 内创建独立 Canvas，返回 bytes，不传递 Context/Path/Image/样式资源 |
| ctx.canvas 变成 undefined | 保持原 Canvas 的强引用；Context 对父 Canvas 的访问为弱引用 |
| Windows 多文件 PDF/SVG 偶发漏字 | 原版默认并发序列限制；在进程启动前设置 `RAYON_NUM_THREADS=1` 并验证目标输出 |
| toSharp 报缺少依赖 | 此 Python 宿主 profile 保留同名缺依赖错误；取得 bytes 后交给所需的 Python 图像工具 |
| 不合规参数似乎没抛错 | 部分 setter/方法按上游行为忽略输入；先看当前值/状态。STRICT 在进程启动前设置，不能假设所有错误都统一抛异常 |

## 提交可重现问题

提供一个只使用公开 API 的最小脚本、固定版本、输入文件的许可/来源、backend/字体信息、预期与实际结果。可用 [hello 示例](../../../examples/ai_demos.py) 起步。保留原输出；需要像素差分时比较完整 RGBA，透明像素 RGB 也计入。

库维护者需要额外构建候选 wheel、对照固定官方 Node A，并保留独立证据，见[开发指南](../development/README.md)。用户代码不要依赖 `_native`、`_debug_*` 等内部调试接口。
