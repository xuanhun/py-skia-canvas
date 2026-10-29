# 文档示例图

中文 | [English](README.en.md)

本目录的 15 张 PNG 是 [ai_demos.py](../../../examples/ai_demos.py) 在已发布 **0.1.0a18 Windows AMD64 wheel** 上实际运行产生的原始字节，用于[使用指南](../usage/README.md)与[示例图册](../usage/DEMOS.md)。绘制使用原 Vulkan GPU 后端；文字依赖当时的系统字体。

所有图形与输入图像由项目 demo 创建，未复制用户图片、系统字体文件或本机 node_modules。PNG 没有经过缩放、修色或后期编辑；Markdown 页面可按显示宽度缩放。

[manifest.json](manifest.json)记录脚本 SHA、wheel SHA、backend、每张图的原始 run 路径、尺寸、字节数和 SHA。脚本在运行时生成 `result.json` / `summary.json`，可用以下命令重现相同场景：

```shell
python examples/ai_demos.py all --backend gpu --out test-runs/NEW_DOC_ASSETS/gpu
python examples/ai_demos.py window --hidden --backend gpu --out test-runs/NEW_DOC_ASSETS/window
```

重新生成时，必须在实际要求的环境成功运行，先检查输出再更新图片和 manifest。不同平台/字体/驱动的重新运行不保证编码文件字节相同；库兼容验收仍按同环境官方 Node A 的精确规则执行。图片不能替代完整像素、字体、窗口和发布证据。
