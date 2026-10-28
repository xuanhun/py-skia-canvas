# G6 大目标：图像、像素与图像样式

日期：2026-10-28。固定官方 skia-canvas 3.0.8；本地 Linux x86_64 / CPython 3.13 wheel 0.1.0a13，未发布。

## 已完成的功能迁移

已接通 Image 构造、尺寸/complete/src、decode、loadImage、loadImageData、load/error 与 onload/onerror、on/once/off；支持 bytes、data URL、本地文件和 HTTP 加载。图像解码完整复用原 bitmap→SVG 流程，SVG 的固有尺寸、缺省 viewBox 比例与 sticky autosized 原样保留。同步 Buffer/data URL 立即完成，文件/网络为 owner asyncio loop 上的 awaitable；工作线程只读字节，Skia 解码/字体/GPU 始终留在创建线程。无运行时 Node/Pillow/skia-python 解码替代。

已实现 ImageData 的尺寸、Buffer、已有 ImageData、Image 四类构造及 createImageData，保留原 floor(abs)、高度推断、颜色校验和错误顺序。bytes/bytearray/memoryview 按 Buffer 拷贝；返回 data 为固定长度的 bytearray 子类，支持 clamped 写入和 set，已有 ImageData 构造继续共享 data。尺寸/colorSpace/colorType/bytesPerPixel/data 顶层只读，字节本身可变；纯值不依赖 Canvas 或 owner，能跨线程使用。

drawImage 支持 Image、ImageData、Canvas，drawCanvas 保留 Canvas 的 vector 分支；两者支持原 2/4/8 坐标、裁剪和负尺寸。getImageData 支持 density、matte、msaa、原颜色布局和负尺寸/越界；putImageData 支持 dirty rect，沿用原 blit 忽略变换/clip/alpha 的语义。imageSmoothingEnabled/Quality 共用原 State 和 sampling。PNG/JPEG/WebP/BMP/GIF/SVG 均有官方差分场景。25 种 colorType 字符串单独覆盖；其中 BGR101010x 在本机官方后端读取失败，记录同一 Error，不冒充支持。

CanvasPattern/createPattern 的 Image、ImageData、Canvas 来源、四种 repetition、SVG autosize、共享 setTransform 已接通。CanvasTexture/createTexture 的 spacing/offset、Path2D、color/line/cap/angle/outline 直接调用原共享 shader。样式与 State 保留原 Rc 共享；原 JS shader 引用缓存不随 restore 恢复的行为也保留，不把错误的测试假设改成新策略。

原 drawImage 对 snap_rects_to_bounds 的返回值未采用，drawCanvas 则采用；迁移保持这一差别。零尺寸 getImageData 经原 ImageData Buffer 构造可能抛 dimensions-mismatch TypeError，已对官方确认，更新早期仅接收 ValueError/RuntimeError 的生命周期断言。

逐项参数、单位、返回、异常、所有权和来源见 [图像 API 状态](imaging-api-status.json)。

## 验收方式调整

用户于本轮明确要求日常只保证 Python 与官方原版 Node 一致。此后以 Python↔官方 A 的功能、指标、异常、RGBA/解码 PNG 为门禁，开发用 Node B 不再每批重编或强制差分。唯一 Rust core 和开发 Node adapter 架构继续保留，源码完整性仍检查。此前 A/B 证据不删除；本轮早期 B 编译/基线是调整前证据，不作为最终主验收条件。

## 来源与生命周期

Image 解码从 src/image.rs:set_data 机械迁至 core image/loading.rs；layout/draw/blit 从 context/api.rs 迁至 image/operations.rs。Node/Python 都转发唯一工作副本，来源快照不变。scripts/image_extraction.py 逐项规定允许的参数/borrow/返回/异常边界替换，并对生成源码精确校验；234 个完整原函数体继续一致，含新增三项 enum helper，24 个既有 Context 片段和其余受控片段继续检查。

Image/Pattern/Texture 采用既有 ID-only owner TLS 注册和外线程延迟析构，不新增 unsafe Send/Sync。16 项新生命周期覆盖数据独立性、外线程访问与 GC、owner 退出、Canvas 自绘制、pattern 快照/共享矩阵、texture Path 持有、加载失败、src 覆盖、waiter 取消及解释器退出；累计 64 项。61 项 bootstrap 包含 SVG 缺省尺寸、原 ignored snap 和 dirty 负尺寸原点的篡改负例。

## 实际证据

修改前源/lock/58 项 bootstrap 在 `20261028-imaging-before`。新增 images30、pixels46、image-edges34、patterns11、textures6、image-formats11，共 138 场景。原版默认/STRICT 和调整前 B 基线独立保存。首轮 pixels 对 BGR101010x 的读取失败、首次 Node 转发返回类型编译失败、首次 PyO3 多 impl 编译失败、候选测试及 oracle 脚本错误均保留；新目录重新验证，不覆盖旧结果。

最终入口为 `test-runs/20261028-imaging-final-2/run.json`：实际同一 alpha13 wheel 在仓库外 cwd、空 PATH 的独立 CPython 3.13.18 venv 安装运行。439 个不同 Python 场景对官方 A 精确一致；新增 138 场景另在 STRICT 进程比较，不重复计为额外独立功能场景。33 份普通比较和 6 份 STRICT 比较，JSON 数值与 RGBA 无容差、alpha=0 的 RGB 仍计数，PNG 解码逐像素核对。64 项生命周期、61 项 bootstrap、6 项 ledger、原 font/text/decoration parser300/213/227 与 2864 个标量位串继续通过。

首个全量最终候选在两项 STRICT 错误消息比较失败：原 rustError 使用 substr(1) 去除 U+26A0 后仍留下 U+FE0F。修正为保留同一字符，失败候选保存在 `20261028-imaging-final`，最终 wheel 另在 `20261028-imaging-wheel-final-build-linux-2` 构建验收，未覆盖旧字节。内部 Rust crate 版本同步为 0.1.0-alpha.13。

`20261028-imaging-loading-linux` 的 18 组官方↔Python 记录逐项精确核对 Buffer/file/data URL/HTTP/redirect、字节像素、原异常消息、once/on、回调替换、损坏 src、连续切换 src 和 decode。只用本项目合成素材和自建 loopback server，完整原错误保留；Node 仅由独立测试 oracle 进程使用。

`20261028-imaging-native-trace-linux` 用同一 wheel 绘制 bitmap/SVG、ImageData blit、Canvas bitmap/vector 来源、pattern 和 texture 后导出，记录 Vulkan surface 与 Skia submit；fresh CPU 控制另存。只代表 Linux Mesa llvmpipe 软件 Vulkan，不代表 Windows 硬件 GPU、Metal、driver 入口或 native surface 尺寸认证。实际输出 PNG 另作视觉审阅。

最终 wheel、来源/依赖/素材清单和 SHA 均写入独立证据；第三方 Cargo 条目 327 个不变，无新依赖，Skia C++ 复用已验证缓存。合成素材按本仓库 MIT 许可保存，不复制系统字体或用户文件。没有 commit、push、上传或发布。

## 仍保留的边界

本大目标完成普通公共图像/像素/pattern/texture 的迁移闭环；完整 JS host/proxy/valueOf/Buffer detachment、全量 EventEmitter 工具、Node URL/Sharp/toSharp、完整 request/agent/proxy 选项及极端对象契约仍属 G0。src 在无运行中 asyncio loop 时保留请求，decode() 被 await 时启动文件/网络 I/O。原 native 对超过 8 个绘图坐标存在切片越界，Python 显式 NotImplementedError，该输入不算完成对齐。

G5 缺字/安全 cluster/实际绘制字形来源、G7 剩余效果/混色、G8 多页与异步导出、App/Window、Windows/Metal、static-fontconfig/manylinux、完整许可及发布继续保留。
