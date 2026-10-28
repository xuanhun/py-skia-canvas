# G2 第二批：paint与图像内容资源

2026-10-27。基线仍为skia-canvas v3.0.8，commit `042312a3f40b660b1d7dc0beba541486171bc5cc`，Skia 0.88.0。没有改变GPU默认策略或增加像素补偿；没有Python绑定或wheel。

## 迁移内容

- 将Gradient/CanvasGradient及其原shader、stop插入、opacity逻辑移入唯一core；linear/radial/conic工厂只分离已解析参数与Rust资源构造。
- 将Texture/CanvasTexture的原path effect、矩阵、颜色/alpha、outline/clipping策略移入core。
- 将Stamp/CanvasPattern的bitmap/vector shader、shared stamp、变换及原SVG autosizing逻辑移入core。
- 将Content及ImageData、原crop-to-bounds、image_info、raster创建、完成/可绘制状态和clone实现移入core。原Broken/Loading clone行为保留，没有顺便修复。
- to_degrees、to_color_space、to_color_type移入core，Node原名转发同一实现；此前to_radians仍在core。
- Neon Finalize通过Node-only `Resource<T>`持有资源，不进入core；Context状态保存core值，其clone仍共享原Rc/RefCell。没有把它们变成跨线程对象。
- 原Content::from_context在Node extension trait中保留原函数体，等Context2D迁移后再收回core；没有为core创建第二份Context。

每个已迁移方法有功能、参数/单位、返回/错误、线程/所有权和上游位置说明。`crates/source-map.json`更新为G2-paint-2；此前映射保存在本地 `test-runs/20261027-g2-paint-extraction/source-map-before.json`。source guard逐字检查27个资源/helper方法体及滤镜整文件，其余GPU/字体等未迁移文件仍核验原字节。

## 场景与证据

新增 `paints.json` 20例，覆盖三种渐变、重复offset与共享修改、pattern repetition/transform/save/restore、Canvas快照、ImageData pattern、texture线路/路径/outline和alpha、rgba/bgra/Alpha8、Canvas源绘制。另有 `paint-svg.json` 两例，使用本项目MIT SVG确认原无固有尺寸autosizing。

迁移前官方A与第一批开发Node的20例精确匹配，证据在 `20261027-paints-original-linux`、`20261027-paints-before-linux`、`20261027-paints-before-comparison`。迁移后20例同样精确匹配，见 `20261027-paints-after-linux`、`20261027-paints-after-comparison`。

最终本地验收目录为 `test-runs/20261027-g2-paint-final/`，构建为 `20261027-paint-final-build-linux/`。记录最终native字节SHA、source-map、工具/依赖/命令和每份JSON/RGBA/PNG附件；测试及比较状态逐项记录，不冒充Python验收。所有test-runs仅本地存在、被Git忽略，没有上传。

首次资源构建因trait impl多余的pub修饰失败，原日志保留在 `20261027-paint-build-linux/build.log`；只修正Rust边界声明，未改原方法体。随后release构建通过，日志在 `20261027-paint-build-linux-2/build.log`。最终源码另做无警告release构建和相关回归。

## 尚未关闭

- JS CSS/颜色解析、参数验证、异常映射、DOM matrix重载仍在adapter，不能声称整个公共paint API已可供Python使用。
- 字体、Context/State、Path操作、Page/ExportOptions/GPU和导出尚待拆分；图像解码和FontLibrary依赖仍在Node。
- 仅Linux同host源码差分；Windows当前只有官方A基线，没有源码B验收。
- Linux本次仍使用系统Fontconfig，未复现上游static-fontconfig发行patch；native GPU surface trace和glyph fallback审计仍缺。
- 尚未验证Python生命周期、跨线程GC、异步、独立安装或发布。

下一步应拆Page/ExportOptions与GPU边界，或按字体/Context依赖继续机械迁移；保持原参数与绘制顺序，先A↔B再接Python。
