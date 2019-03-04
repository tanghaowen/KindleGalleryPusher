from django.db import models
from django.dispatch import receiver
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


class Tag(models.Model):
    name = models.CharField(max_length=255)
    group = models.CharField(max_length=255,blank=True,null=True)

    class Meta:
        verbose_name_plural = "标签"
        verbose_name = "标签"

    def __str__(self):
        return "%s: %s" % (self.name, self.group)


class Author(models.Model):
    name = models.CharField(max_length=255, verbose_name="作者名")

    class Meta:
        verbose_name = "作者"
        verbose_name_plural = "作者"


    def __str__(self):
        return self.name


class ImageWithThumb(models.Model):
    uploaded_time = models.DateTimeField(null=False,verbose_name="上传时间")
    image = models.ImageField(upload_to="img",blank=True)
    thumb_image = models.ImageField(upload_to="img",blank=True)

    def save(self):
        self.uploaded_time = now()
        image_file_name = tools.get_hash_filename(self.image) + os.path.splitext(self.image.name)[1]
        self.image.save(image_file_name, self.image, save=False)
        #self.image.name = image_file_name

        image = PIL.Image.open(self.image)
        thumb_image = PIL.ImageOps.fit(image, (120, 200), PIL.Image.ANTIALIAS, 0, (0.5, 0.5))
        f_memo = BytesIO()
        thumb_image.convert('RGB').save(f_memo,format='JPEG')
        f_memo.seek(0)
        thumb_image_file_name = tools.get_hash_filename(f_memo) + ".jpg"
        self.thumb_image.save(thumb_image_file_name,File(f_memo),save=False)
        super().save()

    def image_tag(self):
        return mark_safe('<img src="/%s" width="100" /><img src="/%s" width="100" /> ' % (self.thumb_image.url,self.image.url))
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
    tags = models.ManyToManyField(Tag,blank=True)
    bangumi_site_path = models.IntegerField(verbose_name="Bangumi网站id",default=0,blank=False)
    mediaarts_site_path = models.IntegerField(verbose_name="メディア芸術データベース网站id",default=0,blank=False)
    sakuhindb_path = models.TextField(verbose_name="sakuhindb网站路径",default=0)
    desc = models.TextField(verbose_name="描述",blank=True)

    def setCover(self,cover_img_id):
        if cover_img_id == "" or cover_img_id is None:
            c = self.covers.order_by('-uploaded_time')
            if len(c) > 0:
                self.cover_id = c[0].id
        else:
            cover_img_id = int(cover_img_id)
            self.cover_id =self.covers.get(id=cover_img_id).id

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
    name = models.CharField(max_length=255,verbose_name='卷名')
    show = models.BooleanField(default=True,verbose_name="显示")
    type = models.ForeignKey(VolumeType,on_delete=models.DO_NOTHING,verbose_name='卷类型',blank=False)
    index = models.IntegerField(default=0,verbose_name='顺序')
    need_convert = models.BooleanField(default=True,verbose_name='是否需要转换')

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
        safe_title = slugify(self.book.title,allow_unicode=True)
        zip_file_dir = os.path.dirname(self.zip_file.name)
        new_name = os.path.join(safe_title,self.zip_file.name)
        if not safe_title in zip_file_dir:
            self.zip_file.save(new_name,self.zip_file,save=False)
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
        if self.epub_ok and self.mobi_ok and self.mobi_push_ok:
            self.delete()

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
