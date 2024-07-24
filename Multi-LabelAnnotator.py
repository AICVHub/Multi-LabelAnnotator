import sys
import os
import json

from PyQt5.QtCore import Qt
from PyQt5.QtGui import QPixmap, QKeySequence
from PyQt5.QtWidgets import QApplication, QMainWindow, QMessageBox, QLabel, QStyle, QWidget, \
    QFileDialog, QAction, QDialog, QTextEdit, QVBoxLayout, QDialogButtonBox, QHBoxLayout, \
    QComboBox, QShortcut


def json_load(json_file):
    with open(json_file, 'rb') as f:
        return json.load(f)


class ClsAnnotator(QMainWindow):

    def __init__(self):
        super().__init__()
        self.zoom_level = 1.0
        self.label_list_widget = None
        self.imageLabel = None
        self.img_path_list = []
        self.img_idx = 0
        self.save_path = None
        # 默认从json文件中初始化属性及类别标签
        self.attribute_labels = json.load(open("./attribute_labels.json", "r")) if \
            os.path.exists("./attribute_labels.json") else {}
        self.comboBoxes = {}  # 存储属性对应的下拉框引用

        self.base_title = "多标签图像分类标注工具"
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle(self.base_title)
        self.setGeometry(200, 100, 1280 + 300, 720 + 30)
        self.setWindowIcon(self.style().standardIcon(QStyle.SP_FileDialogStart))

        # 创建菜单栏
        menubar = self.menuBar()
        fileMenu = menubar.addMenu('文件')
        aboutMenu = menubar.addMenu('关于')

        # 添加"打开文件夹"的菜单项
        openFolderAction = QAction('选择图像数据集文件夹', self)
        openFolderAction.triggered.connect(self.open_folder)
        fileMenu.addAction(openFolderAction)
        # 添加"设置标注结果保存路径"的菜单项
        setSavePathAction = QAction('选择标注结果保存路径', self)
        setSavePathAction.triggered.connect(self.set_save_path)
        fileMenu.addAction(setSavePathAction)
        # 添加"预设标签"的菜单项
        presetLabelAction = QAction('预设/更改标签', self)
        presetLabelAction.triggered.connect(self.preset_multi_label)
        fileMenu.addAction(presetLabelAction)
        # 添加退出菜单项
        exitAction = QAction('退出', self)
        exitAction.triggered.connect(self.simple_close)
        fileMenu.addAction(exitAction)
        # 添加"关于"的菜单项
        aboutAction = QAction('关于', self)
        aboutAction.triggered.connect(self.about_info)
        aboutMenu.addAction(aboutAction)
        # 添加"快捷键"的菜单项
        shortcutAction = QAction('快捷键', self)
        shortcutAction.triggered.connect(self.shortcut_info)
        aboutMenu.addAction(shortcutAction)
        # 添加"帮助"
        helpAction = QAction('帮助', self)
        helpAction.triggered.connect(self.help_info)
        aboutMenu.addAction(helpAction)

        # 创建一个垂直布局用于复选框
        self.checkbox_layout = QVBoxLayout()
        # 创建一个QWidget作为复选框的容器
        self.checkbox_widget = QWidget(self)
        self.checkbox_widget.setLayout(self.checkbox_layout)
        # self.checkbox_widget.setGeometry(QRect(QPoint(self.width() - 300, self.menuBar().height()),
        #                                        QSize(300, self.height() - self.menuBar().height())))
        self.checkbox_widget.setGeometry(self.width() - 300, self.menuBar().height(),
                                         300, self.height() - self.menuBar().height())
        # 创建用于展示图片的 QLabel
        self.imageLabel = QLabel(self)
        self.imageLabel.setGeometry(0, self.menuBar().height(), self.width() - self.checkbox_widget.width(),
                                    self.height() - self.menuBar().height())
        self.imageLabel.setStyleSheet("background-color: #aaaaaa;")
        self.imageLabel.setAlignment(Qt.AlignCenter)  # 居中显示图片

        self.update_checkboxes()

        # 创建快捷键
        self.next_image_shortcut = QShortcut(QKeySequence("D"), self)
        self.next_image_shortcut.activated.connect(self.next_image)
        self.prev_image_shortcut = QShortcut(QKeySequence("A"), self)
        self.prev_image_shortcut.activated.connect(self.prev_image)
        self.zoom_in_shortcut = QShortcut(QKeySequence("Alt++"), self)
        self.zoom_in_shortcut.activated.connect(self.zoom_in)
        self.zoom_out_shortcut = QShortcut(QKeySequence("Alt+-"), self)
        self.zoom_out_shortcut.activated.connect(self.zoom_out)

        # 设置窗口背景色
        # self.setStyleSheet("background-color: #ffffff;")

        # 添加图片展示功能
        self.show_image()

    def open_folder(self):
        # 使用QFileDialog.getExistingDirectory获取文件夹路径
        folder_path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if folder_path:
            QMessageBox.information(self, 'Folder Selected', f"You selected: {folder_path}")
            self.img_path_list = [os.path.join(folder_path, img_name) for img_name in os.listdir(folder_path)
                                  if img_name.lower().endswith((".jpg", ".png", ".jpeg", ".bmp", ".tif", ".tiff"))
                                  ]
            self.show_image()

    def set_save_path(self):
        # 使用QFileDialog.getExistingDirectory获取文件夹路径
        folder_path = QFileDialog.getExistingDirectory(self, "Select Directory")
        if folder_path:
            QMessageBox.information(self, 'Folder Selected', f"You selected: {folder_path}")
            self.save_path = folder_path
            os.makedirs(self.save_path, exist_ok=True)

    def preset_multi_label(self):
        # 创建自定义对话框
        self.dialog = QDialog(self)
        self.dialog.setWindowTitle('预设标签')
        layout = QVBoxLayout(self.dialog)

        # 添加文本编辑框
        text_edit = QTextEdit()
        text_edit.setPlaceholderText('请输入【属性-标签】的json格式，例如：\n'
                                     '{\n"属性1":["标签1", "标签2","标签3"],'
                                     '"属性2":["标签1", "标签2","标签3"]\n}')
        layout.addWidget(text_edit)

        # 添加确认和取消按钮
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        layout.addWidget(buttons)

        # 连接按钮的clicked信号
        buttons.accepted.connect(lambda: self.get_attributes_labels(text_edit.toPlainText()))
        buttons.rejected.connect(self.dialog.reject)

        # 执行对话框
        self.dialog.exec_()

        # 在添加标签后，更新复选框
        self.update_checkboxes()

    def get_attributes_labels(self, text):
        try:
            self.attribute_labels = json.loads(text)
            self.dialog.accept()
        except:
            QMessageBox.warning(self, 'Warning', '请输入正确的json格式！')

    def update_checkboxes(self):
        # 重新创建
        # 创建一个垂直布局用于复选框
        self.checkbox_layout = QVBoxLayout()
        # 创建一个QWidget作为复选框的容器
        self.checkbox_widget = QWidget(self)
        self.checkbox_widget.setLayout(self.checkbox_layout)
        # self.checkbox_widget.setGeometry(QRect(QPoint(self.width() - 300, self.menuBar().height()),
        #                                        QSize(300, self.height() - self.menuBar().height())))
        self.checkbox_widget.setGeometry(self.width() - 300, self.menuBar().height(),
                                         300, self.height() - self.menuBar().height())

        # 创建属性对应的标签和下拉选择框，并使它们横向排列
        for attribute, labels in self.attribute_labels.items():
            # 创建一个水平布局
            horizontal_layout = QHBoxLayout()
            horizontal_layout.setSpacing(10)  # 设置组件之间的间隔
            horizontal_layout.setContentsMargins(0, 0, 0, 0)  # 设置布局的边距

            # 创建属性标签
            attr_label = QLabel(attribute + ":")
            # 设置属性标签的固定宽度，例如100像素
            attr_label.setFixedWidth(100)
            # 设置属性标签的对齐方式，使其在布局中居中对齐
            attr_label.setAlignment(Qt.AlignLeft)

            # 创建下拉框
            combo_box = QComboBox(self.checkbox_widget)
            combo_box.addItems(labels)
            combo_box.setCurrentIndex(0)

            # 将属性标签和下拉框添加到水平布局中，并设置伸展比例
            horizontal_layout.addWidget(attr_label, alignment=Qt.AlignLeft)
            horizontal_layout.addStretch(1)  # 在标签后添加伸展空间
            horizontal_layout.addWidget(combo_box, stretch=10)
            horizontal_layout.addStretch(1)  # 在下拉框后添加伸展空间

            # 将水平布局添加到垂直布局中
            self.checkbox_layout.addLayout(horizontal_layout)

            # 存储属性和对应的下拉框引用
            self.comboBoxes[attribute] = combo_box

            # 连接信号，以便在选中时更新状态
            # combo_box.activated.connect(lambda _, attr=attribute: self.on_combo_box_activated(attr))

        # 刷新复选框容器，以显示新添加的标签和下拉框
        self.checkbox_widget.update()

    def on_combo_box_activated(self, attribute):
        # 当下拉框的选项改变时更新标签列表
        # 获取当前选中的索引
        index = self.comboBoxes[attribute].currentIndex()
        print("{}: {}".format(attribute, self.comboBoxes[attribute].itemText(index)))

    def save_anno_info(self):
        if len(self.img_path_list) == 0:
            return False
        if self.save_path is None:
            QMessageBox.warning(self, 'Warning', '请先设置标注结果保存路径！')
            return False
        img_filename = os.path.split(self.img_path_list[self.img_idx])[-1]
        anno_path = os.path.join(self.save_path, os.path.splitext(img_filename)[0] + ".json")

        anno = {
            "img_filename": img_filename,
        }
        for attribute in self.comboBoxes:
            index = self.comboBoxes[attribute].currentIndex()
            label = self.comboBoxes[attribute].itemText(index)
            anno[attribute] = label

        with open(anno_path, "w") as f:
            json.dump(anno, f, indent=4)

        return True

    def simple_close(self):
        # 直接关闭窗口，不显示任何消息框
        self.close()  # 该方法会触发closeEvent事件，与直接点击X效果一致

    def about_info(self):
        QMessageBox.information(self, 'About',
                                '多标签图像分类标注工具\n作者：@AICVHub\n主页：https://liwensong.blog.csdn.net\n版本：V1.0.0')

    def help_info(self):
        message = """
        <html><head><meta charset='utf-8'></head><body>
        <h3>使用帮助</h3>
        <p>欢迎使用本应用程序，以下是基本的使用步骤：</p>
        <ul>
            <li><strong>选择图像数据集文件夹：</strong>通过菜单栏选择“文件”->“选择图像数据集文件夹”。</li>
            <li><strong>选择标注结果保存路径：</strong>通过菜单栏选择“文件”->“选择标注结果保存路径”。</li>
            <li><strong>预设标签（label）：</strong>通过菜单栏选择“文件”->"预设/更改标签"。</li>
            <li><strong>开始标注：</strong>使用鼠标+键盘进行操作：
                <ul style='list-style-type: disc;'>
                    <li>A：向上翻页（自动保存）。</li>
                    <li>D：向下翻页（自动保存）。</li>
                    <li>针对每张图片，可以使用鼠标点击，选择标签。</li>
                </ul>
            </li>
        </ul>
        <p>如果需要更多帮助，请参阅用户手册或联系技术支持。</p>
        </body></html>
        """
        QMessageBox.information(self, '帮助', message)

    def shortcut_info(self):
        message = """
        <html><head><meta charset='utf-8'></head><body>
        <h3>快捷键</h3>
        <p>欢迎使用本应用程序，以下是基本的快捷键：</p>
        <ul>
            <li><strong>A：</strong>向上翻页（自动保存）。</li>
            <li><strong>D：</strong>向下翻页（自动保存）。</li>
            <li><strong>Alt+：</strong>放大图片。</li>
            <li><strong>Alt-：</strong>缩小图片。</li>
            <li><strong>鼠标滚轮：</strong>放大/缩小图片。</li>
            <li><strong>Tab：</strong>选择属性。</li>
            <li><strong>空格：</strong>展示所选属性的所有标签。</li>
            <li><strong>上下箭头：</strong>选择标签。</li>
            <li><strong>Enter：</strong>确认选择。</li>
        </ul>
        <p>如果需要更多帮助，请参阅用户手册或联系技术支持。</p>
        </body></html>
        """
        QMessageBox.information(self, '快捷键', message)

    def show_image(self):
        if len(self.img_path_list) > 0:
            # 根据当前索引加载图片
            img_path = self.img_path_list[self.img_idx]
            # 使用QPixmap来加载图片
            pixmap = QPixmap(img_path)
            # 调整图片大小使其最大不能超过self.imageLabel
            # if pixmap.width() > self.imageLabel.width() or pixmap.height() > self.imageLabel.height():
            #     pixmap = pixmap.scaled(self.imageLabel.size(), Qt.KeepAspectRatio)
            pixmap = pixmap.scaled(
                int(self.imageLabel.width() * self.zoom_level),
                int(self.imageLabel.height() * self.zoom_level),
                Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
            # 设置QLabel显示图片
            self.imageLabel.setPixmap(pixmap)
            # 更新窗口标题，显示当前图片的索引及文件名
            self.setWindowTitle("{}: [{}/{}]{}".format(
                self.base_title, self.img_idx + 1, len(self.img_path_list), os.path.split(img_path)[-1])
            )

            # 读取标注信息，并更新当前的复选框状态
            if self.save_path:
                img_filename = os.path.split(img_path)[-1]
                anno_path = os.path.join(self.save_path, os.path.splitext(img_filename)[0] + ".json")
                if os.path.isfile(anno_path):
                    json_dict = json_load(anno_path)
                    for attribute in self.comboBoxes:
                        if attribute in json_dict:
                            label = json_dict[attribute]
                            index = self.comboBoxes[attribute].findText(label)
                            self.comboBoxes[attribute].setCurrentIndex(index)
        else:
            self.imageLabel.clear()  # 如果没有图片路径，清空图片显示区域

    def next_image(self):
        if not self.save_anno_info():
            return
        # 显示下一张图片
        if self.img_idx < len(self.img_path_list) - 1:
            self.img_idx += 1
            self.show_image()
        else:
            QMessageBox.information(self, '提示', '已经是最后一张图片了！')

    def prev_image(self):
        if not self.save_anno_info():
            return
            # 显示上一张图片
        if self.img_idx > 0:
            self.img_idx -= 1
            self.show_image()
        else:
            QMessageBox.information(self, '提示', '已经是第一张图片了！')

    def zoom_in(self):
        # 放大操作
        self.zoom_level *= 1.1
        self.apply_zoom()

    def zoom_out(self):
        # 缩小操作
        self.zoom_level *= 0.9
        self.apply_zoom()

    def apply_zoom(self):
        # 应用当前的缩放级别
        self.zoom_level = max(0.1, min(self.zoom_level, 10.0))  # 限制缩放级别在10%-1000%
        self.show_image()

    def wheelEvent(self, event):
        # 根据滚轮滚动的方向来缩放图片
        if event.angleDelta().y() > 0:
            self.zoom_level *= 1.1  # 放大
        else:
            self.zoom_level *= 0.9  # 缩小

        # 限制缩放级别在一定范围内，例如20%-200%
        self.zoom_level = max(0.2, min(self.zoom_level, 2.0))

        self.show_image()  # 重新显示图片以应用缩放
        event.accept()  # 接受事件，防止父类处理

    def resizeEvent(self, event):
        self.checkbox_widget.setGeometry(self.width() - 300, self.menuBar().height(),
                                         300, self.height() - self.menuBar().height())
        self.imageLabel.setGeometry(0, self.menuBar().height(), self.width() - self.checkbox_widget.width(),
                                    self.height() - self.menuBar().height())

        super().resizeEvent(event)  # 调用父类的resizeEvent


def main():
    app = QApplication(sys.argv)
    ex = ClsAnnotator()
    ex.show()
    sys.exit(app.exec_())


if __name__ == '__main__':
    main()

