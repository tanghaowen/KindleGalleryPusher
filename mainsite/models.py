from django.db import models
from django.dispatch import receiver, Signal
from django.db.models.signals import pre_save, post_save
from django.utils.timezone import now
from django.utils.html import mark_safe
from django.shortcuts import get_object_or_404
from . import tools
from io import BytesIO
from django.core.files.temp import NamedTemporaryFile
from django.core.files import File
from django.db.models.fields.files import ImageFieldFile
from django.conf import settings
from django.template import loader
from django.utils.text import slugify
import PIL.Image
import PIL.ImageOps
import os
from django.core.exceptions import ObjectDoesNotExist
# Create your models here.

new_volume_showed_signal = Signal(providing_args=['volume'])

class Tag(models.Model):
    name = models.CharField(max_length=255)
    group = models.CharField(max_length=255,blank=True,null=True)

    class Meta:
        verbose_name_plural = "标签"
        verbose_name = "标签"

    def __str__(self):
        return "%s" % (self.name)


class Author(models.Model):
    name = models.CharField(max_length=255, verbose_name="作者名")

    class Meta:
        verbose_name = "作者"
        verbose_name_plural = "作者"


    def __str__(self):
        return self.name


class ImageWithThumb(models.Model):
    uploaded_time = models.DateTimeField(default=now,null=False,verbose_name="上传时间")
    image = models.ImageField(upload_to="img",blank=True)
    thumb_image = models.ImageField(upload_to="img",blank=True)
    normal_image = models.ImageField(upload_to="img",blank=True)
    # type目前暂时分为image和avatar，根据类型不同生成不同尺寸的缩略图
    type = models.CharField(max_length=20,default='image')
    @staticmethod
    def generate_new_image_field(field_var_name):
        """
        如果添加了其他尺寸的图片field，则条用这个函数来为已有的图片生成新的尺寸
        具体图片field对应的尺寸之类的，需要在save()里手动指定
        :param field_var_name: 静态变量field的变量名
        :return:
        """
        if hasattr(ImageWithThumb,field_var_name):
            print("开始为ImageWithThumb内的字段%s生成图片" % field_var_name)
            to_update_images = ImageWithThumb.objects.filter(**{field_var_name:''})
            if len(to_update_images) == 0:
                print("此字段的所有图片都已经生成")
            for image in to_update_images:
                image.save()
        else:
            print("要更新的图片字段%s 不存在于ImageWithThumb中")
    def save(self):
        image_file_name = tools.get_hash_filename(self.image) + os.path.splitext(self.image.name)[1]
        print("保存ImageWithThumb")
        print("当前image的name是",self.image.name)
        print("计算出来的hash路径是",image_file_name)
        if self.image.name != image_file_name:
            print("计算出来的路径不同")
            self.image.save(image_file_name, self.image, save=False)

        try:
            self.thumb_image.file
        except ValueError:
            print("缩略图不存在，开始生成缩略图")
            image = PIL.Image.open(self.image)
            if self.type == 'image':
                size = (120,200)
            elif self.type == 'avatar':
                size = (100,100)
            thumb_image = PIL.ImageOps.fit(image, size, PIL.Image.ANTIALIAS, 0, (0.5, 0.5))
            f_memo = BytesIO()
            thumb_image.convert('RGB').save(f_memo,format='JPEG')
            f_memo.seek(0)
            thumb_image_file_name = tools.get_hash_filename(f_memo) + ".jpg"
            self.thumb_image.save(thumb_image_file_name,File(f_memo),save=False)
        try:
            self.normal_image.file
        except ValueError:
            print("普通尺寸图不存在，开始生成Normal尺寸")
            image = PIL.Image.open(self.image)
            if self.type == 'image':
                size = (200, 300)
            elif self.type == 'avatar':
                size = (200,200)
            normal_image = PIL.ImageOps.fit(image, size, PIL.Image.ANTIALIAS, 0, (0.5, 0.5))
            f_memo = BytesIO()
            normal_image.convert('RGB').save(f_memo,format='JPEG')
            f_memo.seek(0)
            normal_image_file_name = tools.get_hash_filename(f_memo) + ".jpg"
            self.normal_image.save(normal_image_file_name,File(f_memo),save=False)
        super().save()

    def image_tag(self):
        return mark_safe('<img src="%s" width="100" /><img src="/%s" width="100" /> ' % (self.thumb_image.url,self.image.url))
    image_tag.short_description = 'Image'
    image_tag.allow_tags = True

    class Meta:
        verbose_name = "图片"
        verbose_name_plural = "图片"

    #
    # thumbal_path = os.path.join(settings.BASE_DIR,thumbal_base_name)
    # image.save()
    # instance.thumb_image.save()


class Book(models.Model):
    title = models.CharField(max_length=255,verbose_name="书名",blank=True)
    title_chinese = models.CharField(max_length=255,verbose_name="中文名",blank=True)
    author = models.ManyToManyField(Author,blank=True)
    update_time = models.DateTimeField(null=True,blank=True,verbose_name="更新时间")
    covers = models.ManyToManyField(ImageWithThumb,blank=True,verbose_name="封面图")
    cover_id = models.IntegerField(default=-1,blank=False,verbose_name="使用哪张图")
    cover_used = models.ForeignKey(ImageWithThumb, on_delete=models.DO_NOTHING,blank=True,null=True,related_name='cover_used')
    tags = models.ManyToManyField(Tag,blank=True)
    bangumi_site_path = models.IntegerField(verbose_name="Bangumi网站id",default=0,blank=False)
    mediaarts_site_path = models.IntegerField(verbose_name="メディア芸術データベース网站id",default=0,blank=False)
    sakuhindb_path = models.TextField(verbose_name="sakuhindb网站路径",default=0)
    desc = models.TextField(verbose_name="描述",blank=True)
    show = models.BooleanField(default=True)

    def get_newest_volume(self):
        q = self.volume_set.all().order_by('-edited_data')
        if len(q)>0:
            return q[0]
        else:
            return False

    def setCover(self,cover_img_id):
        if cover_img_id == "" or cover_img_id is None:
            c = self.covers.order_by('-uploaded_time')
            if len(c) > 0:
                self.cover_id = c[0].id
        else:
            cover_img_id = int(cover_img_id)
            self.cover_id =self.covers.get(id=cover_img_id).id

    def get_authors_string(self):
        author_string = ""
        for a in self.author.all():
            author_string += ("%s " % a.name)

        author_string = author_string[:-1]
        return author_string

    def set_book_info(self,book_info_json):
        title = book_info_json.get("title","")
        if title != "": self.title = title
        title_chinese = book_info_json.get("title_chinese", "")
        if title != "": self.title_chinese = title_chinese
        desc = book_info_json.get("desc", "")
        if desc != "": self.desc = desc

        for a in self.author.all(): self.author.remove(a)
        author = book_info_json.get("author",[])
        for author_name in author:
            try:
                a = Author.objects.get(name=author_name)
                self.author.add(a)
            except ObjectDoesNotExist:
                a = Author(name=author_name)
                a.save()
                self.author.add(a)

        for t in self.tags.all(): self.tags.remove(t)
        tags = book_info_json.get("tags",[])
        for tag_name in tags:
            try:
                tag = Tag.objects.get(name=tag_name)
                self.tags.add(tag)
            except ObjectDoesNotExist:
                tag = Tag(name=tag_name)
                tag.save()
                self.tags.add(tag)
        self.save()

    def relative_covers_tags(self):
        temp = loader.get_template('mainsite/admin_covers.html')
        if self.id is None:
            context = {"covers": [], "cover_id": -1}
        else:
            context = {"covers":self.covers.all().order_by('-uploaded_time'),"cover_id":self.cover_id}
        r = temp.render(context)
        return mark_safe(r)
    relative_covers_tags.short_description = 'Covers'
    relative_covers_tags.allow_tags = True

    class Meta:
        verbose_name = "书籍"
        verbose_name_plural = "书籍"

    def __str__(self):
        return self.title
@receiver(pre_save,sender=Book)
def book_pre_save(sender:Book,instance:Book,**kwargs):
    instance.update_time = now()
    try:
        image = ImageWithThumb.objects.get(id=instance.cover_id)
        instance.cover_used = image
    except ImageWithThumb.DoesNotExist:
        pass


class VolumeType(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self):
        return self.name


class Volume(models.Model):
    zip_file = models.FileField(upload_to="books",verbose_name="zip文件")
    epub_file = models.FileField(upload_to="",verbose_name="epub文件",null=True,blank=True)
    mobi_file = models.FileField(upload_to="",verbose_name="mobi文件",null=True,blank=True)
    mobi_push_file = models.FileField(upload_to="",verbose_name="mobi推送文件",null=True,blank=True)
    book = models.ForeignKey(Book, on_delete=models.DO_NOTHING,verbose_name='关联书籍')
    name = models.CharField(max_length=255,verbose_name='显示名')
    volume_number = models.CharField(max_length=255,verbose_name='第几卷')

    # 默认不显示卷，只有当全部epub mobi mobi_epub等卷都转换完毕后才显示
    # 全部转换完成后由EbookConvertQueue里的逻辑将此字段设置为True
    # TODO: 将EbookConvertQueue里的判断转换完成的逻辑移动到Volume类内，并将EbookConvertQueue移动到ebookconvert这个app下
    show = models.BooleanField(default=False,verbose_name="显示")
    type = models.ForeignKey(VolumeType,on_delete=models.DO_NOTHING,verbose_name='卷类型',blank=False)
    index = models.IntegerField(default=0,verbose_name='顺序')
    need_convert = models.BooleanField(default=True,verbose_name='是否需要转换')
    uploaded_data = models.DateTimeField(default=now,blank=True,verbose_name='此卷的zip上传时间')
    edited_data = models.DateTimeField(default=now,blank=True,verbose_name='此卷被编辑过的时间（格式转换后也算编辑）')
    def get_mobi_file_size_MB(self):
        return "%.2f" % (self.mobi_file.size/1024.0/1024.0)

    def get_mobi_push_file_size_MB(self):
        return "%.2f" % (self.mobi_push_file.size/1024.0/1024.0)

    def get_epub_file_size_MB(self):
        return "%.2f" % (self.epub_file.size / 1024.0 / 1024.0)

    def get_zip_file_size_MB(self):
        return "%.2f" % (self.zip_file.size/1024.0/1024.0)

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        # 每次保存时重建卷名（防止今后修改了卷数信息，卷名信息不被修改）
        if self.volume_number.isdigit():
            volume_number = int(self.volume_number)
            if self.type.name == "单行本":
                self.name = "第 %02d 卷" % volume_number
            elif self.type.name == "连载":
                self.name = "第 %02d 话" % volume_number
            else:
                # 非单行本 连载 的类型，如果为数字，直接按照第几话格式命名
                self.name = "第 %02d 话" % volume_number
        else:
            if self.type.name == "单行本":
                self.name = "第 %s 卷" % self.volume_number
            elif self.type.name == "连载":
                self.name = "第 %s 话" % self.volume_number
            else:
                # 单行本 连载 这两个类型外的非数字
                # 如果文件名内包含有[ ] 则直接命名为[]内的内容，否则还是按照第几话的格式命名
                if '[' in self.volume_number and ']' in self.volume_number:
                    self.name = self.volume_number.replace('[','').replace(']','')
                else:
                    self.name = "第 %s 话" % self.volume_number

        if 'books/' not in self.zip_file.name:
            ori_ext = os.path.splitext(self.zip_file.name)[1]
            author_string = self.book.get_authors_string().replace("/","")
            book_title = self.book.title.replace("/","")
            volume_name = self.name.replace("/","")
            safe_file_name = "[%s] %s %s%s" % (author_string, book_title, volume_name, ori_ext)
            new_name = os.path.join(book_title,safe_file_name)
            self.zip_file.save(new_name,self.zip_file,save=False)

        # 如果是新创建的书籍，先保存下获取到id然后把id赋予给index
        if self.id is None:
            print("此为新创建的volume")
            print(self.book.title,self.name)
            super().save()
            self.index = self.id
            print("id",self.id," index",self.index)
            super().save()
        else:
            self.edited_data = now()
            super().save()

    def __str__(self):
        return self.book.title + " " + self.name

    class Meta:
        verbose_name = "书籍"
        verbose_name_plural = "卷信息"
@receiver(post_save,sender=Volume)
def volume_after_save(sender:Volume,instance:Volume,**kwargs):
    need_convert = False
    for f in [instance.zip_file, instance.epub_file, instance.mobi_file, instance.mobi_push_file]:
        try:
            f.file
        except ValueError:
            need_convert = True
    if need_convert:
        try:
            e_queue = EbookConvertQueue.objects.get(volume=instance)
            e_queue.volume = instance
            if e_queue.status == 'error':
                e_queue = EbookConvertQueue(volume=instance)
        except EbookConvertQueue.DoesNotExist:
            e_queue = EbookConvertQueue(volume=instance)
        e_queue.save()
    else:
        try:
            e_queue = EbookConvertQueue.objects.get(volume=instance)
            e_queue.delete()
        except EbookConvertQueue.DoesNotExist:
            pass


class EbookConvertQueue(models.Model):
    volume = models.ForeignKey(Volume,on_delete=models.CASCADE,verbose_name="待转换书籍")
    epub_ok = models.BooleanField(default=False,verbose_name="epub转换完成")
    mobi_ok = models.BooleanField(default=False,verbose_name="mobi转换完成")
    mobi_push_ok = models.BooleanField(default=False,verbose_name="mobi推送版转换完成")
    status = models.CharField(default="pending",verbose_name="状态",max_length=100)

    def update_convert_status(self):
        print("EbookConvertQueue: 更新格式转换队列中的卷信息...")
        try:
            self.volume.epub_file.file
            self.epub_ok = True
        except ValueError:
            pass
        try:
            self.volume.mobi_file.file
            self.mobi_ok = True
        except ValueError:
            pass
        try:
            self.volume.mobi_push_file.file
            self.mobi_push_ok = True
        except ValueError:
            pass
        print("完成")
        # 如果转换完成，则删除自己这个任务并且将此卷设置为前端可见
        # 最后的not selfe.volume.show是用来防止多次调用这个判断函数后，多次发送推送信号
        if self.epub_ok and self.mobi_ok and self.mobi_push_ok and (not self.volume.show):
            print("所有格式都转换完成")
            self.volume.show = True
            self.volume.book.update_time = now()
            self.volume.save()
            # volume被设置为可见，发送信号，将这卷和订阅的用户送入待推送队列
            new_volume_showed_signal.send(EbookConvertQueue, volume=self.volume)



    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        self.update_convert_status()
        super().save()

    def __str__(self):
        return self.volume.__str__()

    class Meta:
        verbose_name = "格式待转换队列"
        verbose_name_plural = "格式待转换队列"

class EbookConvertOver(models.Model):
    volume = models.ForeignKey(Volume,on_delete=models.CASCADE,verbose_name="待转换书籍")
    epub_ok = models.BooleanField(default=False,verbose_name="epub转换完成")
    mobi_ok = models.BooleanField(default=False,verbose_name="mobi转换完成")
    mobi_push_ok = models.BooleanField(default=False,verbose_name="mobi推送版转换完成")
    status = models.CharField(default="pending",verbose_name="状态",max_length=100)


class HomePageGroup(models.Model):
    name = models.CharField(max_length=100)
    books = models.ManyToManyField(Book)

    class Meta:
        verbose_name = "首页分组"
        verbose_name_plural = "首页分组"

    def __str__(self):
        return self.name