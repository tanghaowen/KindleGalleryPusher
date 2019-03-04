from kindlecomicconverter import comic2ebook
import time,sys,shutil
from multiprocessing import freeze_support
import sys,os,glob,tempfile,zipfile
from PyQt5.QtWidgets import QApplication, QWidget, QMainWindow
from PyQt5.uic import loadUi
from PyQt5.QtCore import QThread, pyqtSignal, QObject
from  PyQt5.QtGui import QTextCursor
from PIL import Image
from io import BytesIO
import subprocess
epub_over_heavy_size = 49

class MainWindow(QMainWindow):
    global epub_over_heavy_size
    def __init__(self, parent=None):
        super().__init__(parent)
        loadUi("UI/MainWindow.ui", self)

        self.setAcceptDrops(True)
        self.list_zipfiles.setAcceptDrops(True)
        self.button_start.clicked.connect(self.startClicked)
        self.button_to_mobi.clicked.connect(self.convertToMobiClicked)
        self.zip_files = []
        self.epub_files = []
        self.epub_over_heavy = []
        self.converted_over_heavy_epub = []
        self.convert_thread = None
        self.zips_base_dir = ""

        #sys.stdout = Stream(newText=self.onUpdateText)
    def startClicked(self):
        if self.convert_thread is not None:
            self.statusbar.showMessage("当前正在进行转换工作....")
            return
        if len(self.zip_files) > 0:
            self.statusbar.showMessage("开始转换...")
            self.convert_thread = ConvertByKccThread(self.zip_files)
            self.convert_thread.convert_over_signal.connect(self.convertToEpubOverSignal)
            self.convert_thread.update_status_bar_signal.connect(self.updateStatusBarSignal)
            self.convert_thread.start()
            self.button_start.setEnabled(False)
    def convertToEpubOverSignal(self):
        self.statusbar.showMessage("转换完毕")
        print("转换完成")
        self.convert_thread = None
        self.updateEpubList()
        if len(self.epub_over_heavy) > 0:
            self.epubSlimming()
        else:
            self.button_start.setEnabled(True)

    def updateStatusBarSignal(self,message):
        self.statusbar.showMessage(message)
    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()
    def dropEvent(self, event):
        del self.zip_files[:]

        for url in event.mimeData().urls():
            file_path = url.toLocalFile() # type:str
            file_dir = os.path.dirname(file_path)
            self.zips_base_dir = file_dir
            if file_path.endswith(".zip") or file_path.endswith(".rar"):
                self.zip_files.append(file_path)

        self.updateFileList()
    def updateFileList(self):
        self.list_zipfiles.clear()

        for file_path in self.zip_files:
            file_basename = os.path.basename(file_path)
            self.list_zipfiles.addItem(file_basename)
    def updateEpubList(self):
        del self.epub_files[:]
        del self.epub_over_heavy[:]
        self.list_epubfiles.clear()

        epub_files = []
        for f in os.listdir(os.path.join(self.zips_base_dir,"epub")):
            epub_files.append( os.path.join(self.zips_base_dir,"epub",f) )

        for file in epub_files:
            file_size = os.path.getsize(file)/1024.0/1024.0
            base_name = os.path.basename(file)

            if file_size<epub_over_heavy_size:
                self.list_epubfiles.addItem("%s %.1fMB"% (base_name ,file_size))
                self.epub_files.append([base_name, file, file_size])
            else:
                self.list_epubfiles.addItem('*** %s %.1fMB'% (base_name ,file_size))
                self.epub_over_heavy.append([base_name, file, file_size])
    def epubSlimming(self):
        self.epub_slimming_thread = SlimmingEpubThread(self.epub_over_heavy,self.converted_over_heavy_epub)
        self.epub_slimming_thread.slimming_over_signal.connect(self.slimmingOverSignal)
        self.epub_slimming_thread.update_status_bar_signal.connect(self.updateStatusBarSignal)
        self.epub_slimming_thread.start()
    def onUpdateText(self, text):
        old_text = self.edit_stdout.toPlainText()
        new_text = old_text +  text
        self.edit_stdout.setPlainText(new_text)
        self.edit_stdout.moveCursor(QTextCursor.End)

    def slimmingOverSignal(self):
        self.statusbar.showMessage("epub瘦身全部结束")
        self.button_start.setEnabled(True)
        self.updateEpubList()
        self.convertToMobiClicked()

    def convertToMobiClicked(self):
        self.thread = ConvertToMobiThread(self.epub_files)
        self.thread.convert_over_signal.connect(self.converMobiOverSignal)
        self.thread.update_status_bar_signal.connect(self.updateStatusBarSignal)
        self.thread.start()
        self.button_to_mobi.setEnabled(False)
    def converMobiOverSignal(self):
        self.button_to_mobi.setEnabled(True)
        self.statusbar.showMessage("转换epub到mobi结束")
    def __del__(self):
        sys.stdout = sys.__stdout__

def saveImageToSpecificSizeJpeg(image_path,jpeg_size_limit):
    image = Image.open(image_path)  # type:Image.Image

    for quality in range(80,9,-5):
        #print("Try quality %d ..." %quality)
        tmp_memo_area = BytesIO()
        image.save(tmp_memo_area,"jpeg",quality=quality,optimize=True, progressive=True)
        jpeg_size = tmp_memo_area.__sizeof__()/1024.0
        #print("jpeg size is %.1fKB/.2f%KB" % (jpeg_size,jpeg_size_limit))
        if jpeg_size < jpeg_size_limit:
            print("OK! save jpeg with quality %d %.2f/%.2f" % (quality,jpeg_size,jpeg_size_limit))
            image.save(image_path, quality=quality, optimize=True, progressive=True)
            break
    image.close()
class ConvertByKccThread(QThread):
    convert_over_signal = pyqtSignal()
    update_status_bar_signal = pyqtSignal(str)
    def __init__(self,file_list):
        QThread.__init__(self)
        self.file_list = file_list

    def run(self):
        arg = ['-p', 'KV', '-m', '-f', 'epub', '-r', '2', '-o','epub','--forcecolor']
        ipad_arg = ['-p', 'KV', '-m', '-f', 'epub', '-r', '2', '-o','epub_ipad','--forcecolor']

        for idx,file in enumerate(self.file_list):
            file_basename = os.path.basename(file)
            file_dir = os.path.dirname(file)
            message = "%d/%d 开始转换文件：%s" % (idx+1,len(self.file_list),file_basename)
            self.update_status_bar_signal.emit(message)
            print( message )

            comic2ebook.main(arg+['-o',os.path.join(file_dir,'epub'),file])
        self.convert_over_signal.emit()
class SlimmingEpubThread(QThread):
    slimming_over_signal = pyqtSignal()
    update_status_bar_signal = pyqtSignal(str)
    def __init__(self,epub_over_heavy,converted_over_heavy_epub):
        QThread.__init__(self)
        self.epub_over_heavy = epub_over_heavy
        self.converted_over_heavy_epub = converted_over_heavy_epub

    def run(self):
        for idx,f in enumerate(self.epub_over_heavy):
            base_name, file, file_size = f

            print("开始处理过大epub：%s" % base_name)
            if base_name in self.converted_over_heavy_epub:
                print("此epub已被转换过，跳过！")
                continue
            self.update_status_bar_signal.emit("%d/%d正在为epub瘦身：%s" % (idx+1,len(self.epub_over_heavy),base_name))
            temp_dir_path = tempfile.mkdtemp()
            z = zipfile.ZipFile(file,"r")
            z.extractall(os.path.join(temp_dir_path,"epub"))
            z.close()

            image_dir_path = os.path.join(temp_dir_path,"epub","OEBPS","Images")
            images = []
            for f in os.listdir(image_dir_path):
                full_path = os.path.join(image_dir_path,f)
                f_size = os.path.getsize(full_path)/1024.0
                f_name = f
                images.append([f_name,full_path,f_size])
            images_count = len(images)
            average_size_per_image = epub_over_heavy_size*1024.0/images_count
            print("epub中共有图片%d张，平均缩减到每张%dKB"% (images_count,average_size_per_image))
            self.imageSlimming(images,image_dir_path,average_size_per_image)
            self.packageToEpub(temp_dir_path,file)
            self.converted_over_heavy_epub.append(base_name)
        self.slimming_over_signal.emit()
    def imageSlimming(self,image_infos,image_path,average_size_per_image):
        ok_image_total_size = 0
        ok_image_count = 0
        total_image_count = len(image_infos)
        for img_info in image_infos:
            image_name, full_path, image_size = img_info
            if image_size <= average_size_per_image:
                ok_image_count += 1
                ok_image_total_size += image_size
        new_average_size_per_heavy_image = (epub_over_heavy_size*1024.0-ok_image_total_size) / (total_image_count-ok_image_count)


        for img_info in image_infos:
            image_name, full_path, image_size = img_info
            print("图片: %s, %.2f/%.2f/%.2f" % (image_name,image_size,average_size_per_image,new_average_size_per_heavy_image))
            if image_size > average_size_per_image:
                print("开始瘦身此图片")
                saveImageToSpecificSizeJpeg(full_path,new_average_size_per_heavy_image)
    def packageToEpub(self,temp_dir_path,ori_epub_file_path):
        print("开始重新打包为zip...")
        new_epub_path = os.path.join(temp_dir_path,"newepub","new")
        shutil.make_archive(os.path.join(temp_dir_path,"newepub","new"),"zip",
                            os.path.join(temp_dir_path,"epub"))
        print("打包完成")
        if os.path.exists(new_epub_path+".zip"):
            shutil.move(new_epub_path+".zip",ori_epub_file_path.replace(".epub","_push.epub"))
        else:
            print("未找到new zip文件，生成失败")
class ConvertToMobiThread(QThread):
    convert_over_signal = pyqtSignal()
    update_status_bar_signal = pyqtSignal(str)
    def __init__(self,epub_list):
        QThread.__init__(self)
        self.epub_list = epub_list
    def run(self):
        cmd = ['./kindlegen.exe', '-c2', '-verbose','-dont_append_source']
        for idx,epub in enumerate(self.epub_list):
            basename, file_path, file_size = epub
            self.update_status_bar_signal.emit("%d/%d 开始转换%s" % (idx+1,len(self.epub_list),basename))
            p = subprocess.Popen(cmd + [file_path])
            p.wait()
        self.convert_over_signal.emit()

class Stream(QObject):
    newText = pyqtSignal(str)

    def write(self, text):
        self.newText.emit(str(text))


if __name__ == '__main__':
    freeze_support()
    sys._excepthook = sys.excepthook
    def exception_hook(exctype, value, traceback):
        print(exctype, value, traceback)
        sys._excepthook(exctype, value, traceback)
        sys.exit(1)
    sys.excepthook = exception_hook

    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())

