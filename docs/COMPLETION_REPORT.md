# 剩余迁移与双平台交付

2026-10-28，版本 **0.1.0a18**。已完成本批 G0–G9 剩余迁移及 Windows/Linux 本地 alpha 验收；尚未 commit/push、执行远端 Actions、创建 Release 或发布包索引。

兼容基线为官方 `skia-canvas@3.0.8`，Node 22.23.2；使用用户确认的 [Python 宿主方案](PYTHON_HOST_PROFILE.md)。Canvas/Path/字体/排版/混色/Vulkan 核心只有一份，默认 GPU 策略保留。有限场景的精确一致不等于提供完整 JavaScript VM/Proxy/宿主对象身份。

| 平台 | 实际验收环境 | wheel SHA256 |
| --- | --- | --- |
| windows | Windows / NVIDIA RTX 5080，CPython 3.13.17 | `9efce11f1340a9bfbb69387f0757abe1635b3ff45528ce07e69dc30771049b74` |
| linux | Linux / WSLg Mesa llvmpipe Vulkan，CPython 3.13.18 | `2e641429ceedaca260037abba217e13189a16a1168571fa430857e06b2734071` |

发行 wheel 为 Windows `win_amd64` 和 Linux `manylinux_2_28_x86_64`，均为 CPython 3.13 专用。文件和大小以 `test-runs/20261028-completion-review-1/run.json` 及 `dist/0.1.0a18/release-manifest.json` 为准。macOS/其他 ABI/架构未验收。

## 实现与来源

文本 fill/stroke/outline、路径扩展和静态重载、样式输入、弱父对象、EventEmitter、HTTP options/URL/PathLike、Sharp 缺依赖入口已补齐。408 条清单全部保留：399 条实际功能绑定、2 条用户确认的 Sharp 宿主终态、7 条官方运行时本就不存在的声明/内部项。17 个公开 export 和 401 个实际运行时条目均存在；presence 与语义验证分开登记，见 alpha-api-status.json。

原 Rust/Skia 算法没有重写。292 个完整原函数体保持字节级提取校验；另有原 layout/surface 中的精确观测插入、既有 Vulkan 初始化互斥调用及 Windows owner 退出清理钩子。观测不改变匹配、shaping、layout、paint、shader 或设备选择。所有原操作片段和新增宿主代码在 source-map 中保留来源与哈希。

Windows 原 wheel 的工作线程在绘制后 join 超时；Python threading.local 令资源和原 VK_CONTEXT Option 在 owner 线程仍存活时释放，前后独立证据由 TIMEOUT 变为 EXITED。没有给 GPU 对象添加 Send/Sync，也没有搬到 Python 线程池。公开 getImageData 在弱父 Canvas 已回收时保留实际原版的 TypeError；ctx.canvas 为 undefined。

Linux Fontconfig 与官方二进制均为 2.17.1。使用原 Skia 内嵌 FreeType 的实际能力配置静态库，未添加缺失功能假桩。仅 vendored skia-bindings 0.88.0 的两个 Linux 构建支持文件应用静态链接改造，其余源码由固定 crate SHA 校验。生产 wheel 不依赖系统 Fontconfig/FreeType、Node/Neon/N-API、skia-python、旧包、参考快照或本地工作区。Windows 使用同版官方 rust-skia 缓存。

V8 的独立 IEEE 数学和 dtoa 仅用于原语言数值语义，来源固定 Node 22.23.2 commit，保留 BSD/Sun 许可；没有 V8/Node runtime。

## 实际检查

- 每个平台：3,476 个普通场景、3,175 个 STRICT 场景，77 组比较均精确匹配；JSON 数字、raw RGBA、PNG 解码像素无容差，透明 RGB 也计数。
- 每个平台：118 项真实 wheel 生命周期测试、76,876 个 f64 字符串样本、2,864 项标量位比较、127 项事件契约；实际加载 18 项、HTTP options 16 项。Linux 另验 11 种 STRICT 环境值及 CSS parser 300/213/227/471 项。
- 每个平台实际绘制 12 组字体场景：CJK、RTL/组合字、music、emoji、variable、粗斜体、换行和 stroke。观测同一绘制 Paragraph 的 glyph、UTF16 grapheme range 和四表字体指纹，缺字/来源不唯一/非法 range 均为零；实际 Vulkan surface >0，独立 CPU 控制为零。未保存或分发原字体/表字节。
- Linux 普通/STRICT 各 206 项导出、各 224 个文件，通过解码像素、PDF 所有页和结构、SVG、JPEG/WebP 元数据检查；Windows 单线程诊断各 206 项/228 文件同样精确。
- Windows/Linux GUI 属性契约各 97 项（普通和 STRICT 分别运行）；原版危险 viewport 单独登记。Linux 7 组实际 X11 渲染/输入，Windows 5 组实际 HWND 客户区、缩放/输入均精确匹配。客户区采集仅针对测试进程，最终 Windows 证据使用自有白色背景隔离透明合成区域。早期未隔离背景的 GDI 证据不进入发行包。
- Linux 原生 GDB 捕获真实 Vulkan surface、Skia queue submit 与 GUI 包装/呈现调用，CPU 控制无命中；Windows actual surface 计数与实际 NVIDIA 客户区呈现共同验证硬件 GPU。
- 73 项 bootstrap/源码负控制、原 ledger 断言、许可证与四份 workflow YAML/固定 action SHA 检查通过。这些检查不冒充 GPU 或远端 CI 成功。

独立复核：`test-runs/20261028-completion-review-1/run.json`。主记录：Linux `20261028-completion-final-linux-2`；Windows `20261028-completion-final-windows-5`。GUI 最终记录：Linux render-17、gui-cases-linux-15；Windows gui-present-windows-3、gui-contracts-windows-1。所选图已实际视觉审阅，跨 OS 使用各自系统字体，不宣称两 OS 像素互相相同。

## 继承限制与用户决定

**Windows 默认并发的 PDF/SVG 文件序列可能随机漏字或改变字体子集**。官方 A 自身重复导出不一致，Python 同样可复现，见 `20261028-windows-vector-nondeterminism-1`。用户已明确同意保留原实现并作为 alpha 已知限制。`RAYON_NUM_THREADS=1` 只是两端相同的诊断环境；库和发行 wheel 的默认线程/GPU 策略没有改变，不将串行结果写成默认并发完全通过。

Windows 首批两个 hinted 文本场景有 13/7 像素差；原官方 A 同输入重采也出现变化，最终完整 A/P 复测均精确，早期记录仍保留。没有做像素补偿或容差。

官方 Windows node pump 的预设位置隐藏窗口会在首帧前关闭，Python 保留相同行为；原 A 对照见 `20261028-windows-original-node-position-1`。取消等待者测试使用未预设位置的实际窗口，避免将原版提前关闭与取消混为一谈。IME 等平台输入覆盖有限；不声称穷尽全部 OS 输入法。

JS Proxy/Symbol/原型/native RustClass 反射、Node Buffer/Promise/Agent/Stream 身份采用已确认的 Python 对应；Sharp 返回原缺依赖错误。非正 viewport、危险循环递归、分数页索引原 panic、重入 App.quit 为明确拒绝的危险 profile，不返回空资源或假成功。

## 许可、源码包与发行

每个最终 wheel 的 762 份第三方许可文件逐字节对照来源库存。Windows/Linux 构建所需许可文本缺项为零；另外六个未构建目标/开发包的库存缺项仍明确登记。系统字体不捆绑。pathfinder_geometry 按原双许可选择 Apache-2.0 并保留版权声明。

源码包见 `20261028-completion-sdist-7`。工具只在临时包里去掉 10 个不用的 Node 开发锁项，保留 319 个包的固定 pin，并验证 Windows/Linux 的生产依赖和 feature 树完全相同。显式恢复原文件字节，防止本机打包路径出现 NUL 文件；仓库锁不变。源码包从 /tmp 展开、没有 references/upstream 或 .local，使用明确的固定原生库构建缓存，以 --locked 成功构建；随后在干净环境做实际 GPU 差分与全部数字字符串检查。该新 wheel 只用于源码包验证，**不替换发行验收的 wheel**。

Actions workflow、固定 base image、构建脚本、同字节 staging/publish 校验均已准备；详见 [发行流程](RELEASE_WORKFLOW.md)。尚未获得外部同步/发布授权或验证 Trusted Publisher，故 GitHub Actions 实际执行、Release、TestPyPI、PyPI 各自仍为待执行外部门禁，不称为已发布。

G11 是其他使用方的单独集成任务，本项目为通用 Canvas 库；本批未改其他工作区或引入 PPT 模型。
