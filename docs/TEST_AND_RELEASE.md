# 测试与发布规则

## 同环境差分

原发布Node A、同核Node B、Python必须使用同样的case、尺寸、scale、颜色、字体数据、系统fallback、实际GPU backend/device/driver。分别保留三者环境，不把GPU和CPU的输出视为同组基线。

当前启动工具采集A，并精确比较标准结果格式；Python runner待实现。不得用第二次A运行冒充Python结果。`ORACLE_CAPTURED`不是等价PASS。

基础测试集需覆盖创建/resize、状态/变换/clip、路径填充规则与stroke、渐变/composite/shadow/filter、图像裁剪/像素、文字/测量/字距、字体/variable/fallback、导出/缓存、生命周期/异步、所有权、API错误、GPU选择及无Node安装。当前JSON仅是可执行starter，完整API ledger另补重载和全方法边界。

比较策略：

- JSON按字段/类型比较；数值不加epsilon，bool不等于1。非有限数值和undefined使用显式tag。
- raw RGBA逐字节比较；尺寸和格式不同时直接失败，不缩放、混底、改gamma、premultiply或丢弃透明RGB。
- decoded PNG与raw各自留证；PNG比压缩字节需要更窄的声明。编码metadata另检查DPI/alpha/color profile。
- diff输出独立RGB差图和opaque changed mask，避免RGBA差图alpha为0看不见变化。
- GPU-required作业不能skip或CPU替代；资源缺失状态须明确。System emoji等不满足资源条件不得当作正常通过。
- Windows和Linux各对同host Node；不同OS字体不等不要求彼此PNG相同。

## 结果状态

| 状态 | 能证明什么 |
| --- | --- |
| BOOTSTRAP_VALIDATED | 资料、指纹、场景和比较器的声明检查通过 |
| ORACLE_CAPTURED | 固定Node成功采集所选case；没有Python等价断言 |
| CANDIDATE_CAPTURED | 未来候选实现已采集；仍未比较，不等于通过 |
| MATCHED_RECORDS | 启动比较器确认所选记录一致；可能是Node对Node，不自动认证Python/GPU |
| INCOMPLETE | 缺资源、执行失败或精确差异未关闭 |
| PARITY_PASSED | 指定两实现、同环境、选定cases精确一致；不代表完整API |
| NEEDS_REVIEW | 程序检查满足，相关实图还未审阅 |
| RELEASE_VERIFIED | 指定目标从实际发行URL全新安装且完成声明测试 |

并行/多次同集合执行的计数不相加为独立覆盖。报告实现名、backend、版本、字体和case集合，不只写一个PASS。

## wheel构建和部署

首批Windows AMD64/Linux glibc x86_64 CPython3.13。用Maturin构建PyO3扩展；锁定rust-skia/Skia、features、原生patch、编译器、GN参数、MSRV与Cargo.lock。优先原包同一套Vulkan和字体后端，不复用旧m144 skia-python二进制。

Linux需manylinux合规环境和真实依赖检查，不将WSL `linux_x86_64` 文件改名后上传。Windows检查DLL依赖与VC runtime。Vulkan驱动/loader及用户字体属于部署前提，README列清楚；不把专有显卡driver塞入wheel。

纯Python安装测试移走源码工作目录、清理受控PATH中的Node/npm入口，并屏蔽旧工作区路径；验证不会生成Node子进程、不导入skia-python/Neon、不从用户缓存加载旧runtime、不在import阶段联网。build端可以有Rust/C++工具链，wheel消费端不能要求现场编译。

sdist若发布，必须包含完整可构建的受控核心、锁文件、patch和必要资源；不能引用本机 `.local` 或资料快照路径。许可证文件随wheel/sdist发行；受限系统字体不得附带。

## 发布流水线

1. 固定项目名、版本和兼容范围；记录发布源码commit及依赖。
2. 构建候选wheel/sdist，保存产物hash和构建来源；不自动上传。
3. 各平台全新venv从候选文件安装，检查原生库、真实GPU、字体、API/像素、生命周期和无Node。
4. 需要时走TestPyPI；配置该索引自己的Trusted Publisher/项目，不能假定PyPI授权通用。
5. 用户/发布者配置PyPI Pending Trusted Publisher：仓库`xuanhun/py-skia-canvas`、实际workflow文件名、受保护environment；使用OIDC，不把token放进代码或日志。
6. 审阅后上传**同一批已经验收的字节**；GitHub Release同时附SHA、provenance、许可、支持矩阵与限制。不要发布时重新构建未经检查的文件。
7. 从正式PyPI URL在干净环境`pip install --only-binary=:all:`，核对实际安装wheel、版本、SHA和GPU测试，再标对应RELEASE_VERIFIED。

普通GitHub hosted runner能构建不代表能跑Vulkan。配置Linux软件Vulkan和Windows真实GPU的专用受控测试；自托管GPU runner不接受不受信任PR直接执行。PR构建和具有发布权限的workflow隔离，OIDC权限只给发布job。

版本、hash和已有Release不能覆盖。失败版使用新版本或按PyPI规则处理yank，不能删除证据。名字查询404也不保证发布时一定可注册。
