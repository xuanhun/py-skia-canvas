# G2 第四批：Context、字体和独立 Rust 绘制

日期：2026-10-27。基线仍为 skia-canvas 3.0.8；本批没有升级第三方依赖，也没有 Python 绑定或 wheel。

## 实现范围

将原 Canvas、Context2D/State/Dye、FontLibrary、Typesetter/FontSpec/Spacing 及相关布局逻辑机械迁入唯一 `canvas-core`。Neon 参数读取、JS CSS font 解析、字体文件读取/WOFF 解码、返回对象组装留在 Node adapter。Path2D 扩展和 GUI 绑定仍在 Node；此前提取的 GPU 窗口代码继续保留。

Node 的 `Resource<T>` 只实现语言对象的包装/Finalize，核心不持有 Neon 对象。渐变、pattern 和 texture 继续共享原 Rc/RefCell；字体库继续使用原线程局部管理器及原缓存。没有更改 UTF-16 range、变量字体 wght-1、文字 shaping、布局、混色或 GPU 设备选择。

`crates/source-map.json` 标记为 `G2-context-fonts-4`。校验覆盖 223 个原函数体，以及 filter、Page、GPU、Canvas、Context、字体与 typography 的受控整文件分离。新增方法注明来源、参数/单位、返回/错误和线程/所有权条件；可见性变化和语言包装单独登记。

## 验证与证据

本批前后的字体/文本专项为 13 例，包含默认字体、maxWidth、wrap、baseline、装饰、轮廓、字体 reset、孤立 surrogate 和 shadow。首次原 oracle 对 em spacing 抛 TypeError，失败原样保存在 `20261027-text-original-linux`；之后 fixture 显式观察原错误，没有改写核心以让样例成功。

最终 Node 构建与全部回归在 `test-runs/20261027-g2-context-final/run.json`，构建来源在 `20261027-context-verified-build-linux/run.json`。9 组对照包含：29 个 starter、16 个滤镜、20 个 paint、2 个 SVG pattern、7 个导出、13 个文本、1 个最小核心场景，以及普通/STRICT 各 5 个契约执行。JSON、RGBA、解码 PNG 精确比较，alpha 为零时 RGB 也比较。比较状态仅为 `MATCHED_RECORDS`。

`crates/canvas-core/examples/core_gpu.rs` 是独立 Rust 可执行程序，直接调用共享核心创建 Canvas/Context、绘制分数矩形及黑字/彩字、测量文字、GPU 读回与 PNG 导出。它没有 Node/Python adapter。`scripts/capture_core_probe.py` 在空 PATH 下运行它，验证字体内容和动态依赖，并与固定官方 Node 的同一场景比较。最终证据在 `20261027-context-final-rust-core-linux` 和上述批次目录的 `comparison-rust-core.json`。这是独立 Rust 核心闭环，不是 Python 实现或跨线程 GC 验收。

40 项 bootstrap 断言与 6 项 Node ledger 断言用于来源和采集工具验证；317 个原第三方 Cargo package 条目保持不变。视觉审阅另存 `review.json`，不由像素比较自动推导。

## 未完成项

- 没有 Python 绑定、wheel、Python GC/线程/解释器关闭验证；尚未选择或宣称安全的 PyO3 GPU 对象所有权方案。
- 当前新增构建与独立 Rust 运行只验证 Linux x86_64 的软件 Vulkan；Windows 源码构建、Metal、原生 queue/surface trace 尚未验收。
- 系统字体内容指纹已验证，但每个 glyph 的 fallback、完整 CJK/emoji/variable 字体契约尚未验收。
- Linux 重建依赖系统 Fontconfig，未复现上游发行容器的 static-fontconfig patch；不可据此称 manylinux 或发行 provenance 完成。
- 公共 API ledger 的人工语义审计、CSS font/文件解码/Path 扩展等语言边界及完整导出异步桥仍有任务。独立 Rust 示例不是公共 API 的替代实现。

下一步是 G3：以共享核心实现真正的 Python Canvas/Context 与同步 raw/PNG，先解决线程所有权和销毁，再构建并在无 Node 的干净环境验收 CPython 3.13 wheel。
