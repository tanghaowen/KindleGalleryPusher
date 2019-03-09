import sys
import threading,time,os
from django.conf import settings
import logging
from django.core.files import File
from .kcc.kindlecomicconverter import comic2ebook
import tempfile, subprocess, zipfile
from PIL import Image
from io import BytesIO
import shutil
import cv2

# 推送mobi的最大体积（单位MB）
MAX_PUSH_MOBI_SIZE = 45


def start_monitor_thread():
    print("Now Start...")
    monitor_thread = MonitorThread()
    monitor_thread.daemon = True
    monitor_thread.start()
    return monitor_thread


class MonitorThread(threading.Thread):

    def __init__(self):
        super().__init__()

    def init(self):
        self.mainsite_models = __import__('mainsite.models',globals(), locals(),['EbookConvertQueue'])
        # 启动线程时检查下当前是否存在状态为doing的任
        # 有的话意味着这是上次意外退出只进行了一半的任务
        self.error_terminated_tasks = self.mainsite_models.EbookConvertQueue.objects.filter(status='doing')
        if len(self.error_terminated_tasks):
            print("上次有意外终止的待转换任务，数量为%d 重启任务" % len(self.error_terminated_tasks))
        for task in self.error_terminated_tasks:
            task.status = 'pending'
            task.save()


        logging.basicConfig(level = logging.ERROR,format = '%(asctime)s - %(name)s - %(levelname)s - %(message)s')

        self.logger = logging.getLogger(__name__)
        self.logger.setLevel(level=logging.INFO)
        self.handler = logging.FileHandler("convert_error_log.txt")
        self.handler.setLevel(logging.INFO)
        formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
        self.handler.setFormatter(formatter)

        self.console = logging.StreamHandler()
        self.console.setLevel(logging.INFO)

        self.logger.addHandler(self.handler)
        self.logger.addHandler(self.console)

    def run(self):
        time.sleep(10)
        self.init()
        while True:
            print("monitering")
            task = self.pop_task_from_model()
            if task is not None:
                print(task)
                try:
                    res = self.start_convert(task)
                    if res :
                        task.status = "done"
                        task_over = self.mainsite_models.EbookConvertOver(volume = task.volume, epub_ok = task.epub_ok,
                                                              mobi_ok = task.mobi_ok, mobi_push_ok = task.mobi_push_ok,
                                                              status = task.status)
                        # 因为tasker保存时如说全都完成会更新书籍为显示，所以需要调用
                        task.save()
                        task.delete()
                        task_over.save()
                        continue
                    else:
                        task.status = "error"
                        task.save()
                        continue
                except Exception as e:
                    self.logger.error('volume转换失败')
                    self.logger.error('%d %s -  %s' % (task.id,task.volume.book.title,task.volume.name))
                    self.logger.error(e,exc_info = True)

                    task.status = 'error'
                    task.save()
                    continue


            time.sleep(100)

    def pop_task_from_model(self):
        # 检测上次意外结束的任务，这里还得检测下状态，因为意外结束的任务执行完毕调用delete删除记录后
        # 对象依旧会留在self.error_terminated_tasks里

        tasks = self.mainsite_models.EbookConvertQueue.objects.filter(status='pending')
        if tasks.count()>0:
            print("格式转换队列中有任务,数量",len(tasks))
            task = tasks[0]
            task.status = 'doing'
            task.save()
            return task
        else:
            print("队列为空")
            return None

    def start_convert(self, task):
        print("开始转换",task)
        # 转换逻辑
        zip_name = task.volume.zip_file.name
        zip_real_path = os.path.join(settings.MEDIA_ROOT,zip_name)
        zip_dir =os.path.dirname(zip_name)
        cache_path = tempfile.mkdtemp()
        print(zip_real_path)
        if not task.epub_ok:
            print("开始转换为epub")
            arg = ['-p', 'KoAHD', '-m', '-f', 'epub', '-r', '2', '--forcecolor']
            start_time = time.time()
            new_ebook_path = self.use_kcc_to_convert(task, arg,cache_path=cache_path)
            spent_time = time.time() - start_time
            print("**************zip转换为epub耗时%.2f秒(%.2f分)"
                  % (spent_time,spent_time/60.0))
            if new_ebook_path :
                task.epub_ok = True
                task.save()
                print(new_ebook_path)
                os.remove(new_ebook_path)
            else:
                print("转换失败")
                return False
        else:
            print("epub转换已完成，跳过")
        if not task.mobi_ok:
            print("开始转换为mobi")
            print("先转换为临时epub...")
            arg = ['-p', 'KV', '-m', '-f', 'epub', '-r', '2', '--forcecolor']
            start_time = time.time()
            tmp_epub_path = self.use_kcc_to_convert(task,arg,save_quick=False,cache_path=cache_path)
            spent_time = time.time() - start_time
            print("**************zip转换为临时epub耗时%.2f秒(%.2f分)"
                  % (spent_time,spent_time/60.0))
            if tmp_epub_path :
                print("从临时epub转为mobi")
                print(tmp_epub_path)
                if 'win32' in sys.platform:
                    cmd = ['./kindlegen.exe', '-c2', '-verbose', '-dont_append_source']
                elif 'linux' in sys.platform:
                    cmd = ['./kindlegen', '-c2', '-verbose', '-dont_append_source']
                start_time = time.time()
                p = subprocess.Popen(cmd + [tmp_epub_path])
                p.wait()
                spent_time = time.time() - start_time
                print("**************kindlegen从临时epub转为mobi格式耗时%.2f秒(%.2f分)"
                      % (spent_time, spent_time / 60.0))
                new_mobi_path = tmp_epub_path.replace(".epub",".mobi")
                if os.path.exists(new_mobi_path):
                    print("mobi转换成功")
                    print(new_mobi_path)
                    new_mobi_filename = os.path.basename(new_mobi_path)
                    new_mobi_name = os.path.join(zip_dir, new_mobi_filename)
                    task.volume.mobi_file.save(new_mobi_name, File(open(new_mobi_path, 'rb')))
                    task.volume.save()
                    task.mobi_ok = True
                    task.save()
                else:
                    print("mobi转换失败")
                    return False

                # task.mobi_ok = True
                # task.save()
                # print(new_ebook_path)
                # os.remove(new_ebook_path)
            #print(new_ebook_path)
        else:
            print("mobi转换已完成，跳过")
        if not task.mobi_push_ok:
            print("开始处理mobi_push")
            print("检测是否有存在的mobi文件")
            try:
                task.volume.mobi_file
                mobi_path = task.volume.mobi_file.path
                # 判断mobi文件大小，如果小于50M的话，就直接塞入mobi_push
                mobi_file_size = os.path.getsize(mobi_path) / 1024.0 / 1024.0
                print("转换完成的mobi体积：%.2fMB" % mobi_file_size)
                if mobi_file_size <= MAX_PUSH_MOBI_SIZE:
                    print("体积小于推送体积，直接并入mobi_push_file")
                    # task.volume.mobi_push_file = task.volume.mobi_file
                    task.volume.mobi_push_file.name = task.volume.mobi_file.name
                    task.volume.save()
                else:
                    # mobi体积大于50M，开始为epub瘦身
                    print("体积大于推送体积，开始为epub瘦身")

                    if 'tmp_epub_path' in locals():
                        print("上次生成mobi时生成的中间epub存在，开始为此epub瘦身")
                        print(tmp_epub_path)
                        start_time = time.time()
                        slimmed_epub_path = self.slimming_epub(tmp_epub_path)
                        spent_time = time.time() - start_time
                        print("**************图片瘦身耗时%.2f秒(%.2f分)"
                              % (spent_time, spent_time / 60.0))
                        print("转换此epub为推送用mobi")
                        if 'win32' in sys.platform:
                            cmd = ['./kindlegen.exe', '-c2', '-verbose', '-dont_append_source']
                        elif 'linux' in sys.platform:
                            cmd = ['./kindlegen', '-c2', '-verbose', '-dont_append_source']
                        start_time = time.time()
                        p = subprocess.Popen(cmd + [slimmed_epub_path])
                        p.wait()
                        spent_time = time.time() - start_time
                        print("**************kindlegen把瘦身过的epub转为mobi耗时%.2f秒(%.2f分)"
                              % (spent_time, spent_time / 60.0))
                        new_push_mobi_path = slimmed_epub_path.replace(".epub", ".mobi")
                        print("生成的推送用mobi路径",new_push_mobi_path)
                        new_push_mobi_filename = os.path.basename(new_push_mobi_path)
                        new_push_mobi_name = os.path.join(zip_dir, new_push_mobi_filename)
                        task.volume.mobi_push_file.save(new_push_mobi_name, File(open(new_push_mobi_path, 'rb')))
                        task.volume.save()
                        task.mobi_push_ok = True
                        task.save()
                    else:
                        print("上次生成mobi时生成的中间epub不存在！ 无法创建瘦身档")

            except ValueError:
                print("并不存在mobi文件，无法下一步")
                return False
        else:
            print("mobi push转换已完成，跳过")
        print("清空临时目录",cache_path)
        shutil.rmtree(cache_path)
        task.save()
        print("转换成功")
        return True
        # 如果出错的话，status = "error"

    def use_kcc_to_convert(self,task,kcc_arg,save_quick=True,cache_path=None):
        zip_name = task.volume.zip_file.name
        zip_dir = os.path.dirname(zip_name)
        zip_real_path = os.path.join(settings.MEDIA_ROOT,zip_name)
        if cache_path is None:
            temp_path = tempfile.mkdtemp()
        else:
            temp_path = cache_path

        kcc_arg = kcc_arg + ['-o', temp_path,zip_real_path]
        file_basename = os.path.basename(zip_real_path)
        message = "开始转换文件：%s" % (file_basename)
        author_string = task.volume.book.get_authors_string()
        book_title = "%s %s" %(task.volume.book.title, task.volume.name)
        new_ebook_paths = comic2ebook.main(author_string,book_title,kcc_arg)
        if len(new_ebook_paths) > 0:
            new_ebook_path = new_ebook_paths[0]
            if save_quick:
                new_ebook_filename = os.path.basename(new_ebook_path)
                new_ebook_name = os.path.join(zip_dir,new_ebook_filename)
                task.volume.epub_file.save(new_ebook_name,File(open(new_ebook_path,'rb')))
                task.volume.save()
            return new_ebook_path
        return False

    def slimming_epub(self,ori_epub_path):
        temp_dir_path = tempfile.mkdtemp()
        print("临时文件夹:",temp_dir_path)
        z = zipfile.ZipFile(ori_epub_path, "r")
        z.extractall(os.path.join(temp_dir_path, "epub"))
        z.close()

        image_dir_path = os.path.join(temp_dir_path, "epub", "OEBPS", "Images")
        images = []
        for root,dirs,files in os.walk(image_dir_path):
            for file in files:
                full_file_path = os.path.join(root,file)
                file_base_name = os.path.basename(full_file_path)
                f_size = os.path.getsize(full_file_path)
                images.append([file_base_name, full_file_path, f_size])
        images_count = len(images)
        average_size_per_image = MAX_PUSH_MOBI_SIZE * 1024.0 * 1024.0 / images_count
        print("epub中共有图片%d张，平均缩减到每张%.2fKB" % (images_count, average_size_per_image/1024.0))
        self.image_slimming(images, image_dir_path, average_size_per_image)
        new_push_epub_file_path = self.pack_to_epub(temp_dir_path, ori_epub_path)
        print("清空临时文件夹",temp_dir_path)
        shutil.rmtree(temp_dir_path)
        return new_push_epub_file_path

    def image_slimming(self,image_infos,image_path,average_size_per_image):
        ok_image_total_size = 0
        ok_image_count = 0
        total_image_count = len(image_infos)
        for img_info in image_infos:
            image_name, full_path, image_size = img_info
            if image_size <= average_size_per_image:
                ok_image_count += 1
                ok_image_total_size += image_size
        new_average_size_per_heavy_image = (MAX_PUSH_MOBI_SIZE*1024.0*1024.0-ok_image_total_size) / (total_image_count-ok_image_count)

        for img_info in image_infos:
            image_name, full_path, image_size = img_info
            print("图片: %s, %.2f/%.2f/%.2f" % (image_name,image_size/1024.0,average_size_per_image/1024.0,new_average_size_per_heavy_image/1024.0))
            if image_size > average_size_per_image:
                print("开始瘦身此图片")
                self.save_image_to_speciftc_jpeg_size(full_path,new_average_size_per_heavy_image)

    def save_image_to_speciftc_jpeg_size(self,image_path, jpeg_size_limit):
        image = cv2.imread(image_path)
        quanty = 50
        half = 25
        for i in range(1, 6):
            print("质量:%d" % quanty, end="")
            if i == 5:
                cv2.imwrite(image_path, image, [int(cv2.IMWRITE_JPEG_QUALITY), quanty])
                print("")
            else:
                encode_param = [int(cv2.IMWRITE_JPEG_QUALITY), quanty]
                result, encimg = cv2.imencode('.jpg', image, encode_param)
                size = encimg.size
                print(" size %.2f" % (size))
                if size <= jpeg_size_limit:
                    quanty += half
                else:
                    quanty -= half
                half = int(half / 2)
        del image

    def pack_to_epub(self,temp_dir_path,ori_epub_file_path):
        print("开始重新打包为zip...")
        new_epub_path = os.path.join(temp_dir_path,"newepub","new")
        shutil.make_archive(new_epub_path,"zip",
                            os.path.join(temp_dir_path,"epub"))
        print("打包完成")
        if os.path.exists(new_epub_path+".zip"):
            print(new_epub_path)
            new_epub_file_path = ori_epub_file_path.replace(".epub","_push.epub")
            print("打包完成的推送epub文件路径",new_epub_file_path)
            shutil.move(new_epub_path+".zip",new_epub_file_path)
            return new_epub_file_path
        else:
            print("未找到打包完成的zip文件，生成失败")
if __name__ == '__main__':
    monitor_thread = start_monitor_thread()
