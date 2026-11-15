# 个人账本维护指南

## 本地运行

Windows、Python 3.12、PySide6、SQLite。首次配置见 README。开发时运行 `.\.venv312\Scripts\python.exe main.py`。双击启动脚本会优先打开 `dist/个人账本/个人账本.exe`，调试源码请直接运行 Python 入口。

## 代码入口

- `app/parser/` 分别解析微信和支付宝账单。`models.py` 定义流水及去重键，`refunds.py` 关联退款，`transfers.py` 识别本人账户划转。
- `app/database.py` 与 `app/storage.py` 处理持久化，`app/portable.py` 决定数据目录。源码版与目录版各自使用程序旁的 `data/`，两个目录可以是不同账本。
- `app/rules/` 管理分类规则。新用户从空规则开始。个人关键词、银行卡及分类映射只写入用户数据。
- `app/ui/` 包含明细表、规则管理、双月日期选择器和统计页。统计图由 Qt 绘制，布局以折线为主、环形图为辅。

## 修改后怎么验证

- 导入或统计有改动时，用临时账本重复导入同一批模拟流水，检查笔数及净额。覆盖支付宝未付款关闭、跨月退款和部分退款。微信等额退款还需文字或单号佐证，多笔候选时检查是否保留待核对状态。本人账户划转应从收支统计中排除。
- 表格或图表有改动时，试窄窗口和高 DPI。检查日期数字、图表标注、列宽拖动及重开后的列设置，并实际操作日期筛选和图表明细入口。
- 原始账单、SQLite、个人规则、界面设置及本地资料均留在用户机器。清理旧构建时先检查其中的 `data/`，其中可能有独立账本。

## 打包与发布

在项目根目录执行以下命令，生成 `releases/` 下的 Windows 目录版。

```powershell
uv pip install --python .venv312\Scripts\python.exe pyinstaller
.\build.ps1
```

从刚构建且尚未启动的目录制作 ZIP，附上 LICENSE。检查包内没有用户数据，再解压到另一个可写目录，双击 EXE 确认主窗口正常启动。发布时将 ZIP 附到对应提交的 GitHub Release，并核对 SHA-256。项目原创内容使用 CC BY-NC-SA 4.0。
