# 来源资料

## 固定上游

[skia-canvas v3.0.8](https://github.com/samizdatco/skia-canvas/tree/v3.0.8)，commit `042312a3f40b660b1d7dc0beba541486171bc5cc`。快照在 [upstream/skia-canvas-3.0.8](upstream/skia-canvas-3.0.8)，包括 Rust 源码、JS 包装、类型声明、依赖锁文件、字体配置及构建流程参考。

没有复制 `.git`、node_modules、原生二进制或上游整个测试资产目录。需要完整上游仓库时，应按固定 commit 获取，不以当前 main 替代。

快照来自固定 commit 的干净 checkout；`.gitattributes` 对该目录关闭换行转换，防止 Windows/Linux clone 后文件指纹被自动 CRLF/LF 处理改变。项目自己编写的文本统一使用 LF。

运行 `python scripts/refresh_reference_index.py` 可从快照确定性再生 [source-manifest.json](source-manifest.json) 和 [native-api-index.json](native-api-index.json)；普通校验使用 `validate_bootstrap.py`，不会重写指纹以掩盖来源变化。

`Cargo.toml` 锁定 `skia-safe 0.88.0`，`Cargo.lock` 记录实际 crate 解析和校验和。此信息不等于已证明 npm 发布物的所有 C++ 构建参数；新项目必须核对实际 Skia revision、字体后端、编译器、features、GN 参数与预编译缓存来源。

## 可参考但不直接替代的项目

- [phyron-skia-canvas](https://github.com/phyrondev/phyron-skia-canvas)：有独立 Rust API，Node 入口按 feature 分离；0.2 系列声明使用 Skia M148，并扩展线性色彩/HDR。可学边界拆分，不能当作 v3.0.8 像素等价实现。
- [meo-skia-canvas](https://docs.rs/meo-skia-canvas/latest/meo_skia_canvas/)：有独立 Canvas/Context2D Rust API；同样需要审查行为、线程和版本变化，不自动引入。
- [rust-skia](https://github.com/rust-skia/rust-skia)：保留真实 Skia C++，不替换成 tiny-skia 或手写光栅器。

## Python 打包资料

- [PyO3 构建与分发](https://pyo3.rs/main/building-and-distribution)：Rust Python 扩展、解释器配置与 ABI。
- [PyO3 线程安全](https://pyo3.rs/main/class/thread-safety)：不能把未满足约束的线程局部对象强行声明 Send/Sync。
- [Maturin 项目结构](https://www.maturin.rs/project_layout.html) 与 [分发](https://www.maturin.rs/distribution.html)：mixed layout、manylinux 合规及 wheel。
- [PyPI Trusted Publisher 首次创建项目](https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/) 与 [已有项目配置](https://docs.pypi.org/trusted-publishers/adding-a-publisher/)：GitHub 仓库权限不等于 PyPI 发布权限。
- [PyPI 存储限制](https://docs.pypi.org/project-management/storage-limits/)：发行前检查真实 wheel 大小，不通过改标签或省略必要原生库规避。

## 资料与实现边界

这里的来源文件和历史观察是研发输入；新 pip 包不能运行时读取这些资料或其他本机工作区。未来构建应使用仓库中受控的核心、锁定依赖和打包资源，目标机器从 wheel 安装不需要 Node/Rust/C++ 编译环境。
