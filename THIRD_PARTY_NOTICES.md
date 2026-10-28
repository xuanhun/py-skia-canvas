# 第三方来源与许可

`references/upstream/skia-canvas-3.0.8` 中的文件来自 [samizdatco/skia-canvas v3.0.8](https://github.com/samizdatco/skia-canvas/tree/v3.0.8)，commit `042312a3f40b660b1d7dc0beba541486171bc5cc`，保留其 [MIT LICENSE](references/upstream/skia-canvas-3.0.8/LICENSE) 与原文件头。

本仓库原有 MIT LICENSE 的版权归属不改写为上游作者。未来派生核心必须同时保留适用的上游版权/许可，而不是只保留新项目 LICENSE。

现有 `crates/node` 与 `crates/canvas-core` 派生自上述固定版本，各自保留上游 `LICENSE`。原文件与工作副本的映射及指纹见 `crates/source-map.json`；滤镜函数体和采样规则没有重写。

Skia、rust-skia、Vulkano 等核心依赖以及 Python adapter 的 PyO3 0.27.2 均按 Cargo.lock 锁定。PyO3 采用 MIT/Apache-2.0 双许可；Maturin 1.9.6 仅作构建工具，不是运行依赖。Neon 只在开发 Node adapter，不能进入 Python wheel 的依赖图。

wheel 包含项目/上游 MIT 许可、Maturin 收集的 Cargo 依赖许可及 `third_party/licenses` 中的固定依赖许可和版权文件。`third_party/license-inventory.json` 记录来源、SHA、Windows/Linux 构建依赖范围与非构建目标的缺项。它包含开发依赖的来源登记，不表示 Neon 进入生产 wheel。CPython 开发解释器未捆绑进 wheel。

Linux 发行构建静态使用 Fontconfig 2.17.1，保留其 COPYING/AUTHORS；FreeType、HarfBuzz、ICU、libpng、libjpeg-turbo、libwebp、zlib 等使用固定 Skia revision 的来源和许可。系统字体只记录指纹，不进入 wheel。`pathfinder_geometry` 的原源码明确允许 Apache-2.0 或 MIT，分发选择 Apache-2.0，并保留原版权声明；该 crate 所记 GitHub 历史 commit 当前不可读取，未伪造历史 MIT 文件。完整清单和校验工具为 `third_party/license-inventory.json` 与 `scripts/validate_licenses.py`。

语言数字转字符串使用同版 V8 的独立 dtoa 源码，BSD 许可在 `crates/python/vendor/v8-numbers/LICENSE`。这些纯数值函数不带 Node/V8 运行时。来源与原函数体由 `scripts/validate_number_source.py` 校验。

DOMMatrix 的原 JS 三角函数语义使用 Node 22.23.2（commit aa4c77582be995286fc6e00aaf530dc7ade102a9）中 V8 12.4.254.21-node.56 的独立 ieee754.cc/h 与 overflowing-math.h。原文件、来源 URL/SHA 和工作副本分别在 references/math/node-v22.23.2 与 crates/python/vendor/v8；完整保留 V8 BSD LICENSE 和 Sun fdlibm 许可声明，并包含在 wheel。只静态导出四个纯数值函数，不捆绑或依赖 Node/V8 运行时。cc 1.2.38（MIT/Apache-2.0）仅用于构建该独立代码，未替换 Rust/Skia 绘制核心；完整发行许可审核仍待完成。

CSS font 的语言解析边界按原 css.js 及 string-split-by 1.0.0、parenthesis 3.1.8 的默认分词算法迁移。两包原文件、npm resolved/integrity 和逐文件 SHA 保存在 references/css；string-split-by 的 README 声明 © 2018 Dmitry Yv、MIT，parenthesis 保留 © 2016 Dmitry Ivanov 的原 MIT LICENSE。对应通知在 crates/python/vendor/css 并包含在 wheel。它们只作为语言值解析来源，不是 Node/npm 运行依赖；未修改字体匹配、shaping 或绘制算法。

测试 JSON、SVG 和工具为本项目新增内容，适用根目录 MIT 许可。未捆绑任何 Windows 系统字体、用户 PPT 或原专有 artifact-tool 源码。历史数据只保留公开示例的观测摘要，不构成字体再分发授权。
