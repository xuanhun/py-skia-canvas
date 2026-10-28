# G2 第三批：Page、缓存、导出与GPU

2026-10-27。继续复用固定v3.0.8源码，未改变Skia版本、默认GPU策略、字体策略或比较标准。没有Python绑定、wheel或发布。

## 迁移范围

- `context/page.rs`中的PageRecorder、RecordingSurface、Page、PageSequence、PageCache、ExportOptions、PDF辅助函数及原cache singleton/计数器移入core。Neon的pages_arg只留在Node adapter，保留原函数体。
- `gpu/`完整模块移入core，包含原Vulkan/Metal offscreen engine及window renderer、RenderCache、设备选择、MSAA、线程局部context、idle watcher、清理与原drop顺序。
- Node GPU模块仅转发core，旧工作副本中的GPU子文件已移走；没有同时保留第二份工作实现。只读reference不改。
- window仍是独立feature；Node window feature转发core/window，原App/Window事件绑定仍留在Node，没有删去任务。
- Core增加的依赖都是原Node已经锁定的依赖。317个第三方package条目不变；原生产策略没有借拆分升级或替换。
- `source-map.json`为G2-page-gpu-3，检查131个选定原方法体逐字一致，并核对GPU整文件仅增加说明、Page仅分离三个Neon import和pages_arg。新增/迁移函数标注参数/单位、返回/错误、线程/所有权及原位置。

## 验证与本地证据

修改前已添加并采集 `tests/fixtures/exports.json` 的7例：sync/async raw缓存、resize/reset、页面索引、density/matte/colorType、MSAA错误后恢复、SVG，以及显式CPU↔GPU切换。官方A与第二批Node先精确匹配：`20261027-exports-original-linux`、`20261027-exports-before-linux`、`20261027-exports-before-comparison`。第三批迁移后7例仍精确匹配：`20261027-exports-after-linux`、`20261027-exports-after-comparison`。

`20261027-page-build-linux/build.log`记录首次release成功构建。独立core的headless检查保留Vulkan/freetype、关闭window，结果在 `20261027-core-headless-linux/check.log`；检查通过，有两个原窗口专用format helper的dead-code警告，不是skip或CPU验收。

最终构建目录为 `20261027-page-final-build-linux/`，最终断言、依赖树和各套差分集中在 `20261027-g2-page-final/`。它们记录精确native SHA、锁文件、source-map、构建/检查命令及JSON/RGBA/PNG结果。旧批次保留，本地test-runs被Git忽略，没有上传。

## 验收边界与下一步

- Linux headless编译和Node差分不代表Python、Windows源码构建、macOS/Metal实际执行或App/Window行为验收。
- 当前GPU设备信息仍为公共getter，缺实际surface/queue调用的native trace。Linux是Mesa llvmpipe软件Vulkan；Windows官方A硬件GPU基线另存，不能混称完成所有GPU验收。
- Linuxstatic-fontconfig发行patch未复现，字体文件fallback尚未逐glyph确认。
- 保留原Rayon导出和materialize规则，但Python取消/GC/重入/解释器关闭仍待独立验证，不能据现有Node Promise场景标G8完成。
- Context/State与Typesetter/FontLibrary仍在Node crate，路径操作也未提取。下一批应机械拆出这些共享类型及原字体逻辑，再实现PyO3同步Canvas PoC；不要先建空包。
