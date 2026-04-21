📦 Nuke Repath v2.5

素材路径修复工具（Read 节点批量重链接）
作者：LiaoLiao

🧰 功能介绍

Nuke Repath 是一个用于 批量修复 Read 节点素材路径 的工具，适用于素材丢失、路径变更、跨项目迁移等场景。

✨ 核心功能
📋 显示所有 Read 节点（表格化）
🎨 状态颜色区分（正常 / 丢失）
🔄 批量路径替换（支持正则）
📁 拖拽文件夹自动匹配素材
🎯 双击 / 右键定位节点（等同按 F）
🔍 显示分辨率 / 帧范围 / 色彩空间
🧠 自动识别序列（支持 %04d）
📊 进度条显示处理进度
📂 安装方法
1️⃣ 放置文件

将插件文件放入 Nuke 用户目录：

C:\Users\你的用户名\.nuke\

目录结构：

.nuke/
│
├── repath.py
├── menu.py
2️⃣ 修改 menu.py
import nuke
import importlib

def run_repath():
    try:
        import repath
        importlib.reload(repath)
        repath.show_repath_dialog()
    except Exception as e:
        nuke.message("加载 Repath 失败:\n{}".format(str(e)))

menu = nuke.menu("Nuke")
tools = menu.findItem("Tools") or menu.addMenu("Tools")
tools.addCommand("Repath", run_repath)
3️⃣ 重启 Nuke

打开路径：

Nuke → Tools → Repath
🖥️ 使用说明
📌 主界面功能
功能	说明
重新扫描	刷新所有 Read 节点
重新链接选中	手动为选中节点指定路径
重新链接全部	批量逐个选择路径
批量替换路径	字符串 / 正则替换
拖拽文件夹匹配	自动搜索并匹配素材
🎯 节点定位（核心功能）

双击节点名 或 右键 → 定位节点：

nuke.selectAll()
nuke.invertSelection()
node.setSelected(True)
nuke.zoomToFitSelected()

👉 等同于 按 F 键

🎨 状态说明
状态	颜色	含义
正常	绿色	文件存在
丢失	红色	文件不存在
🔁 批量替换示例
普通替换
查找: D:/old_project
替换: E:/new_project
正则替换
查找: D:/project_\d+
替换: E:/project_final
📁 拖拽匹配说明

直接把素材目录拖入窗口：

✔ 自动递归扫描
✔ 按文件名匹配
✔ 支持序列

🧠 序列识别逻辑

自动识别：

image.1001.exr
→ image.%04d.exr

并设置：

first
last
step
⚠️ 注意事项
❗ 1. 必须在 GUI 模式运行
import nuke
print(nuke.GUI)

✔ True 才有 UI

❗ 2. 文件必须在 .nuke 目录

否则会报错：

No module named 'repath'
❗ 3. 修改后需重启 Nuke

或使用：

import importlib
import repath
importlib.reload(repath)
🚀 可扩展方向（进阶）

可以进一步升级为：

🔍 缺失贴图自动扫描
🧠 智能路径映射（项目迁移）
🎬 Shot / Asset 自动匹配
🗂 多路径 fallback 机制
📦 打包发布工具
💡 一句话总结

👉 Repath = 一键修复 Nuke 所有贴图路径 + 智能匹配 + 可视化管理

🧾 License

仅供学习 / 生产使用，可自由修改。
