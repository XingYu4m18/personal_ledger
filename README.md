# 个人账本

Windows 桌面记账工具，支持导入微信和支付宝账单、识别重复交易与退款，并按分类和月份查看收支。账本保存在本地 SQLite 数据库中。

## 运行

在项目目录执行以下命令，之后可双击 `双击运行.bat` 启动。

```powershell
uv venv --python 3.12 .venv312
uv pip install --python .venv312\Scripts\python.exe -r requirements.txt
.\双击运行.bat
```

## 许可

本项目原创内容采用 [CC BY-NC-SA 4.0](LICENSE)。允许非商业使用、修改和分享。分享时须署名并注明修改，分享改编作品须沿用相同许可或兼容许可。原版和改编版均限非商业使用。第三方依赖遵循各自的许可证。
