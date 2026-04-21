# -*- coding: utf-8 -*-
"""
Nuke Repath - 素材路径修复工具
版本: 2.5
功能: 显示所有Read节点，颜色区分状态，批量替换路径，拖拽文件夹匹配，定位节点
"""

import nuke
import os
import re
import glob
from pathlib import Path

try:
    from PySide2 import QtWidgets, QtCore, QtGui
except ImportError:
    from PySide6 import QtWidgets, QtCore, QtGui


def normalize_path(path):
    if not path:
        return path
    path = path.replace('\\', '/')
    if path.endswith('/'):
        path = path.rstrip('/')
    return path


def get_sequence_info(file_path):
    dirname = os.path.dirname(file_path)
    basename = os.path.basename(file_path)
    pattern = r'(.*?)(\d+)\.([^\.]+)$'
    match = re.match(pattern, basename)
    if not match:
        return None, None, None, None, None
    prefix, frame_str, ext = match.groups()
    frame = int(frame_str)
    padding = len(frame_str)
    search_pattern = os.path.join(dirname, f"{prefix}*{ext}")
    files = glob.glob(search_pattern)
    frames = []
    for f in files:
        m = re.match(pattern, os.path.basename(f))
        if m and m.group(1) == prefix and m.group(3) == ext:
            frames.append(int(m.group(2)))
    if not frames:
        return None, None, None, None, None
    frames.sort()
    step = 1
    if len(frames) > 1:
        step = frames[1] - frames[0]
    return (os.path.join(dirname, prefix), frames[0], frames[-1], step, padding)


def relink_node(node, new_path, force_keep_type=False):
    try:
        new_path = normalize_path(new_path)
        if force_keep_type:
            node['file'].setValue(new_path)
            return True
        seq_info = get_sequence_info(new_path)
        if seq_info[0] is not None:
            base, first, last, step, pad = seq_info
            frame_expr = f"%0{pad}d"
            seq_expr = f"{base}.{frame_expr}.{os.path.splitext(new_path)[1][1:]}"
            node['file'].setValue(seq_expr)
            node['first'].setValue(first)
            node['last'].setValue(last)
        else:
            node['file'].setValue(new_path)
        return True
    except Exception as e:
        print(f"Failed to relink {node.name()}: {e}")
        return False


def get_read_info(node):
    file_path = node['file'].value()
    norm_path = normalize_path(file_path)
    width = node.width() if hasattr(node, 'width') else 0
    height = node.height() if hasattr(node, 'height') else 0
    first = node['first'].value() if node.knob('first') else 0
    last = node['last'].value() if node.knob('last') else 0
    colorspace = node['colorspace'].value() if node.knob('colorspace') else 'Unknown'
    return {
        'path': norm_path,
        'width': width,
        'height': height,
        'first': first,
        'last': last,
        'colorspace': colorspace
    }


def find_file_by_name(folder, target_filename):
    target_basename = os.path.basename(target_filename)
    base_name, ext = os.path.splitext(target_basename)
    base_name = re.sub(r'\d+$', '', base_name)
    for root, dirs, files in os.walk(folder):
        for f in files:
            if f.startswith(base_name) and f.endswith(ext):
                return os.path.join(root, f)
    return None


class RepathUI(QtWidgets.QDialog):
    def __init__(self, parent=None):
        try:
            parent = parent or nuke.getQMainWindow()
        except:
            parent = None
        super(RepathUI, self).__init__(parent)
        self.setWindowTitle("Repath v2.5 - 素材路径修复")
        self.setMinimumSize(1000, 600)
        self.setAcceptDrops(True)
        self.all_read_nodes = []
        self.setup_ui()
        self.scan_all_reads()

    def setup_ui(self):
        layout = QtWidgets.QVBoxLayout(self)

        btn_layout = QtWidgets.QHBoxLayout()
        self.scan_btn = QtWidgets.QPushButton("重新扫描")
        self.scan_btn.clicked.connect(self.scan_all_reads)
        btn_layout.addWidget(self.scan_btn)

        self.relink_selected_btn = QtWidgets.QPushButton("重新链接选中")
        self.relink_selected_btn.clicked.connect(self.relink_selected)
        btn_layout.addWidget(self.relink_selected_btn)

        self.relink_all_btn = QtWidgets.QPushButton("重新链接全部")
        self.relink_all_btn.clicked.connect(self.relink_all)
        btn_layout.addWidget(self.relink_all_btn)

        self.batch_replace_btn = QtWidgets.QPushButton("批量替换路径")
        self.batch_replace_btn.clicked.connect(self.batch_replace)
        btn_layout.addWidget(self.batch_replace_btn)

        self.folder_match_btn = QtWidgets.QPushButton("拖拽文件夹匹配")
        self.folder_match_btn.setToolTip("将包含正确素材的文件夹拖入窗口，自动按文件名匹配")
        btn_layout.addWidget(self.folder_match_btn)

        layout.addLayout(btn_layout)

        self.table = QtWidgets.QTableWidget(0, 6)
        self.table.setHorizontalHeaderLabels([
            "节点名", "当前路径", "分辨率", "帧范围", "色彩空间", "状态"
        ])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.setSelectionMode(QtWidgets.QAbstractItemView.ExtendedSelection)
        self.table.horizontalHeader().setStretchLastSection(True)
        self.table.setColumnWidth(0, 120)
        self.table.setColumnWidth(1, 500)
        self.table.setColumnWidth(2, 100)
        self.table.setColumnWidth(3, 100)
        self.table.setColumnWidth(4, 120)
        self.table.setColumnWidth(5, 80)
        self.table.setContextMenuPolicy(QtCore.Qt.CustomContextMenu)
        self.table.customContextMenuRequested.connect(self.show_context_menu)
        self.table.itemDoubleClicked.connect(self.on_item_double_clicked)
        layout.addWidget(self.table)

        self.progress_bar = QtWidgets.QProgressBar()
        self.progress_bar.setVisible(False)
        layout.addWidget(self.progress_bar)

        self.status_label = QtWidgets.QLabel("就绪")
        layout.addWidget(self.status_label)

        self.setStyleSheet("""
            QTableWidget { gridline-color: #ccc; }
            QPushButton { padding: 6px; }
            QProgressBar { text-align: center; }
        """)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        urls = event.mimeData().urls()
        folders = [u.toLocalFile() for u in urls if os.path.isdir(u.toLocalFile())]
        if folders:
            self.match_from_folder(folders[0])
        else:
            QtWidgets.QMessageBox.information(self, "提示", "请拖入包含正确素材的文件夹")

    def on_item_double_clicked(self, item):
        if item.column() == 0:
            row = item.row()
            node = self.all_read_nodes[row]
            self._locate_node(node)

    def _locate_node(self, node):
        """在节点图中定位并选中节点（类似按F键）"""
        try:
            nuke.selectAll()
            nuke.invertSelection()
            node.setSelected(True)
            nuke.zoomToFitSelected()
        except Exception as e:
            print(f"定位节点失败: {e}")

    def show_context_menu(self, pos):
        index = self.table.indexAt(pos)
        if not index.isValid():
            return
        row = index.row()
        node = self.all_read_nodes[row]
        menu = QtWidgets.QMenu(self)
        copy_path_action = menu.addAction("复制路径")
        copy_path_action.triggered.connect(lambda: self._copy_path(row))
        open_folder_action = menu.addAction("打开所在文件夹")
        open_folder_action.triggered.connect(lambda: self._open_folder(row))
        browse_link_action = menu.addAction("浏览并链接")
        browse_link_action.triggered.connect(lambda: self._browse_and_link(row))
        locate_action = menu.addAction("定位节点")
        locate_action.triggered.connect(lambda: self._locate_node(node))
        menu.exec_(self.table.viewport().mapToGlobal(pos))

    def _copy_path(self, row):
        item = self.table.item(row, 1)
        if item:
            clipboard = QtWidgets.QApplication.clipboard()
            clipboard.setText(item.text())
            self.status_label.setText(f"已复制: {item.text()[:80]}...")

    def _open_folder(self, row):
        node = self.all_read_nodes[row]
        cur_path = node['file'].value()
        if cur_path:
            folder = os.path.dirname(cur_path)
            if os.path.exists(folder):
                os.startfile(folder)
            else:
                QtWidgets.QMessageBox.warning(self, "错误", f"文件夹不存在: {folder}")

    def _browse_and_link(self, row):
        node = self.all_read_nodes[row]
        current_path = node['file'].value()
        dir_path = os.path.dirname(current_path) if current_path else ""
        new_path, _ = QtWidgets.QFileDialog.getOpenFileName(
            self, f"选择 {node.name()} 的新路径", dir_path,
            "图像序列 (*.exr *.jpg *.png *.dpx *.tif);;所有文件 (*.*)"
        )
        if new_path:
            new_path = normalize_path(new_path)
            if relink_node(node, new_path, force_keep_type=False):
                self.scan_all_reads()
                self.status_label.setText(f"已链接 {node.name()}")

    def scan_all_reads(self):
        self.all_read_nodes = nuke.allNodes('Read')
        self.table.setRowCount(len(self.all_read_nodes))
        for row, node in enumerate(self.all_read_nodes):
            info = get_read_info(node)
            exists = os.path.exists(info['path'])

            name_item = QtWidgets.QTableWidgetItem(node.name())
            name_item.setFlags(name_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row, 0, name_item)

            path_item = QtWidgets.QTableWidgetItem(info['path'])
            path_item.setFlags(path_item.flags() & ~QtCore.Qt.ItemIsEditable)
            if exists:
                path_item.setForeground(QtGui.QColor(0, 150, 0))
            else:
                path_item.setForeground(QtGui.QColor(200, 0, 0))
            self.table.setItem(row, 1, path_item)

            res_item = QtWidgets.QTableWidgetItem(f"{info['width']}x{info['height']}" if info['width'] else "?")
            res_item.setFlags(res_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row, 2, res_item)

            frame_item = QtWidgets.QTableWidgetItem(f"{info['first']}-{info['last']}" if info['first'] else "?")
            frame_item.setFlags(frame_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row, 3, frame_item)

            cs_item = QtWidgets.QTableWidgetItem(info['colorspace'])
            cs_item.setFlags(cs_item.flags() & ~QtCore.Qt.ItemIsEditable)
            self.table.setItem(row, 4, cs_item)

            status_text = "正常" if exists else "丢失"
            status_item = QtWidgets.QTableWidgetItem(status_text)
            status_item.setFlags(status_item.flags() & ~QtCore.Qt.ItemIsEditable)
            if exists:
                status_item.setForeground(QtGui.QColor(0, 150, 0))
            else:
                status_item.setForeground(QtGui.QColor(200, 0, 0))
            self.table.setItem(row, 5, status_item)

        self.status_label.setText(f"共 {len(self.all_read_nodes)} 个 Read 节点")

    def get_selected_rows(self):
        rows = set()
        for idx in self.table.selectedIndexes():
            rows.add(idx.row())
        return sorted(rows)

    def relink_selected(self):
        rows = self.get_selected_rows()
        if not rows:
            QtWidgets.QMessageBox.warning(self, "提示", "请先选中要重新链接的行")
            return
        self._relink_rows(rows, force_keep_type=False)

    def relink_all(self):
        rows = list(range(self.table.rowCount()))
        self._relink_rows(rows, force_keep_type=False)

    def _relink_rows(self, rows, force_keep_type=False):
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(rows))
        success = 0
        for i, row in enumerate(rows):
            self.progress_bar.setValue(i)
            QtWidgets.QApplication.processEvents()
            node = self.all_read_nodes[row]
            current_path = node['file'].value()
            dir_path = os.path.dirname(current_path) if current_path else ""
            new_path, _ = QtWidgets.QFileDialog.getOpenFileName(
                self, f"选择 {node.name()} 的新路径", dir_path,
                "图像序列 (*.exr *.jpg *.png *.dpx *.tif);;所有文件 (*.*)"
            )
            if not new_path:
                continue
            new_path = normalize_path(new_path)
            if relink_node(node, new_path, force_keep_type):
                success += 1
        self.progress_bar.setVisible(False)
        self.scan_all_reads()
        self.status_label.setText(f"成功重新链接 {success} 个文件")

    def batch_replace(self):
        dialog = QtWidgets.QDialog(self)
        dialog.setWindowTitle("批量替换路径")
        dialog.setModal(True)
        layout = QtWidgets.QVBoxLayout(dialog)

        layout.addWidget(QtWidgets.QLabel("查找 (支持正则表达式):"))
        old_edit = QtWidgets.QLineEdit()
        layout.addWidget(old_edit)

        layout.addWidget(QtWidgets.QLabel("替换为:"))
        new_edit = QtWidgets.QLineEdit()
        layout.addWidget(new_edit)

        use_regex_cb = QtWidgets.QCheckBox("使用正则表达式")
        layout.addWidget(use_regex_cb)

        keep_type_cb = QtWidgets.QCheckBox("保持原素材类型（不自动转换序列）")
        keep_type_cb.setChecked(True)
        layout.addWidget(keep_type_cb)

        btn_box = QtWidgets.QDialogButtonBox(QtWidgets.QDialogButtonBox.Ok | QtWidgets.QDialogButtonBox.Cancel)
        btn_box.accepted.connect(dialog.accept)
        btn_box.rejected.connect(dialog.reject)
        layout.addWidget(btn_box)

        if dialog.exec() != QtWidgets.QDialog.Accepted:
            return

        old = old_edit.text().strip()
        new = new_edit.text().strip()
        if not old:
            QtWidgets.QMessageBox.warning(self, "错误", "请输入要查找的字符串")
            return
        use_regex = use_regex_cb.isChecked()
        keep_type = keep_type_cb.isChecked()

        rows = self.get_selected_rows() or range(self.table.rowCount())
        success = 0
        for row in rows:
            node = self.all_read_nodes[row]
            cur_path = node['file'].value()
            cur_path_norm = normalize_path(cur_path)
            if use_regex:
                try:
                    new_path = re.sub(old, new, cur_path_norm)
                    if new_path == cur_path_norm:
                        continue
                except Exception as e:
                    print(f"正则错误: {e}")
                    continue
            else:
                old_norm = normalize_path(old)
                if old_norm not in cur_path_norm:
                    continue
                new_path = cur_path_norm.replace(old_norm, normalize_path(new), 1)
            if relink_node(node, new_path, force_keep_type=keep_type):
                success += 1
        self.scan_all_reads()
        self.status_label.setText(f"批量替换成功 {success} 个文件")

    def match_from_folder(self, folder):
        if not os.path.isdir(folder):
            QtWidgets.QMessageBox.warning(self, "错误", "无效的文件夹路径")
            return
        rows = range(self.table.rowCount())
        success = 0
        self.progress_bar.setVisible(True)
        self.progress_bar.setRange(0, len(rows))
        for i, row in enumerate(rows):
            self.progress_bar.setValue(i)
            QtWidgets.QApplication.processEvents()
            node = self.all_read_nodes[row]
            cur_path = node['file'].value()
            target_filename = os.path.basename(cur_path)
            matched_file = find_file_by_name(folder, target_filename)
            if matched_file:
                if relink_node(node, matched_file, force_keep_type=False):
                    success += 1
        self.progress_bar.setVisible(False)
        self.scan_all_reads()
        self.status_label.setText(f"文件夹匹配成功 {success} 个文件")


def show_repath_dialog():
    global _repath_win
    try:
        _repath_win.close()
        _repath_win.deleteLater()
    except:
        pass
    _repath_win = RepathUI()
    _repath_win.show()


def add_menu():
    menubar = nuke.menu("Nuke")
    tools_menu = menubar.findItem("Tools")
    if not tools_menu:
        tools_menu = menubar.addMenu("Tools")
    tools_menu.addCommand("Repath", "import repath; repath.show_repath_dialog()")


if __name__ == "__main__":
    add_menu()
    print("Repath v2.5 已加载，请在 Tools 菜单中找到 'Repath'")
