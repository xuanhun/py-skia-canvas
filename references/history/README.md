# 历史发现：为什么另建 Python Canvas 项目

这些是原 PPT 工作区已经记录的观察摘要，不是新库的测试报告。旧工作区原始日志、系统字体、二进制包和用户 PPT 没有复制。新会话须重新采集；不能用此页声明新库已通过。

## 原基线与差异

原 Node 包为 `skia-canvas 3.0.8`，默认走 GPU；此前 Python `skia-python` 路线走 CPU。原 Node native 文件 SHA-256 记录如下，仅供核对原发行物，不代表可从源码直接重建出相同文件：

| 平台 | native SHA-256 |
| --- | --- |
| Windows | `4e5b185ccdffceede5468b47c4646e2ce66f4e85ec35a753007ec32cb8720498` |
| Linux | `2363537634644a50b69d785411713d12ae62453c1238bb98842e65b9919777f9` |

- 默认 GPU 与 Python CPU 比较，Office 字体 8 例曾出现 Windows 2471 像素、Linux 3719 像素差异。此数据不是新的 `py-skia-canvas` 差异。
- 双方显式走 CPU 后，这 8 例的指标和像素在两平台均全等。Linux 扩展 32 例 CPU 控制也全等；Windows 透明色仍有 80 个 RGB 像素的 1 通道值差异，alpha 不变。
- 另一组 13 个真实 CPU literal 场景，Linux 全等；Windows 非 BMP emoji 仍有 **438 像素**未关闭。不能把它归因于 GPU/CPU 后就声明消失。
- 这些记录推动用户选择：不继续为 `skia-python` 补 Vulkan 入口，改为复用原 `skia-canvas` Rust 核心，新增独立 PyO3 绑定。

此前为 `skia-python` 补 Paragraph 测量接口的工作见 [上游 PR #394](https://github.com/skia-python/skia-python/pull/394)。它属于旧路线的背景，不是本新库的依赖，也不意味着可用它替代原 Node 的 Vulkan 核心。

## 重要陷阱

1. v3.0.8 的 `new Canvas(w,h,{gpu:false})` 会改变部分显示状态，却不等于实际使用 CPU；显式 `canvas.gpu=false` 才真正选择 CPU。默认 GPU 对照不要被构造选项误导。应采集 `.gpu` 与 `.engine`，必要时加 native trace。
2. 旧 Linux GDB 后续有效采样区分了 GPU surface/Ganesh glyph 与 CPU raster/Bitmap glyph 调用。早期只看到模块加载的采样无效，不能当已覆盖绘制。
3. `round(255*x)` 与近似 256 混色差异不是“换一个取整公式”就可补偿的依据。不要按样例写颜色修正。
4. 同版本内部 SKP 控制与公共 API 是不同层次；原包并没有可直接依赖的公共 SKP 导出契约。
5. 同 CPU 全等、旧 wheel 回归通过、资料检查通过，都不能替代本项目原默认 GPU 的 1:1 验收。

## 新项目需携带的回归类别

默认 GPU 与显式 CPU 对照；黑字/彩字；透明底与不透明底；分数坐标；alpha=0 的 RGB；Office/Theme 字体解析；CJK/RTL/组合字符；emoji ZWJ/非 BMP；TextMetrics 全字段；字体 alias/reset；缓存及异步生命周期。

本项目的 [starter 场景](../../tests/fixtures/scenarios.json) 覆盖其中一部分。Office 字体与平台 emoji 需要新环境显式登记字体来源、版本、哈希和许可；这里不分发它们。跨 OS 各自对齐本机 Node，不拿不同系统字体图片做“跨平台像素相同”断言。
