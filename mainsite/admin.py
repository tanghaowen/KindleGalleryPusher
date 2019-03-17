from django.contrib import admin
from .models import *
from django.core.files import File
from django.forms import TextInput, Textarea
# Register your models here.
from django.contrib.auth.models import Permission

class BookAuthorBridgeAdmin(admin.TabularInline):
    model = Book.author.through


class BookTagBridgeAdmin(admin.TabularInline):
    model = Book.tags.through


class AuthorAdmin(admin.ModelAdmin):
    list_display = ["id","name"]
    list_display_links = ["id","name"]
    readonly_fields = ["id"]
    inlines = [BookAuthorBridgeAdmin]


class VolumeInline(admin.StackedInline):
    model = Volume
    fiel = ['name',]
    fieldsets = [
        [None,{"fields":['index',('volume_number','name','show','need_convert'),'type',]}],
        [None,{"fields":[ 'zip_file', 'epub_file', 'mobi_file', 'mobi_push_file']}],
    ]
    extra = 0
    readonly_fields = ['need_convert','name','show']
    ordering = ['index']





class BookAdmin(admin.ModelAdmin):
    list_display = ["id","title","update_time"]
    list_display_links = ['id','title']
    fieldsets = [
        ["基本信息",{'fields':['id','title','title_chinese','update_time','end','show'],}],
        ["关联网站",{"fields":[('mangazenkan_site_path','get_info_from_mangazenkan'),('bangumi_site_path','get_info_from_bangumi'),('mediaarts_site_path','get_info_from_mediaarts')]}],
        ["作者",{"fields":['author']}],
        ["标签",{"fields":['tags']}],
        ["封面",{"fields":["relative_covers_tags","cover_id"]}],
        ["简介",{"fields":["desc"]}],
    ]
    readonly_fields = ['id','update_time','relative_covers_tags','cover_id','get_info_from_mediaarts','get_info_from_bangumi','get_info_from_mangazenkan']
    filter_horizontal = ['author','tags']
    inlines = [VolumeInline]
    # autocomplete_fields = ['author']
    # formfield_overrides = {
    #     models.TextField: {'widget': Textarea(attrs= { 'rows': '1'})},
    # }

    def save_model(self, request, obj, form, change):
        if obj.id is None: obj.save()
        if 'uploaded_image' in request.FILES:
            new_image_model = ImageWithThumb(image=request.FILES['uploaded_image'],thumb_image=File(None,None),normal_image=File(None,None))
            new_image_model.save()
            obj.covers.add(new_image_model)
            obj.setCover(new_image_model.id)
        else:
            obj.setCover(form.data.get("cover_select_radio",""))
        super().save_model(request,obj,form,change)

    def get_info_from_bangumi(self,obj):
        if obj.id is None:
            return mark_safe("""<div></div>""")
        return mark_safe("""
            <div>
            <button id="update_book_info_banmgumi" type="button" book_id=%d>获取信息</button>
            </div>
        """ % obj.id)
    def get_info_from_mangazenkan(self,obj):
        if obj.id is None:
            return mark_safe("""<div></div>""")
        return mark_safe("""
            <div>
            <button id="update_book_info_mangazenkan" type="button" book_id=%d>获取信息</button>
            </div>
        """ % obj.id)
    def get_info_from_mediaarts(self,obj):
        if obj.id is None:
            return mark_safe("""<div></div>""")
        return mark_safe("""
            <div>
            <button id="update_book_info_mediaarts" type="button" book_id=%d>获取信息</button>
            </div>
        """% obj.id)


    class Media:
        js=['admin/get_book_info.js']

class ImageAdmin(admin.ModelAdmin):
    fields = ['image','image_tag','uploaded_time']
    readonly_fields = ['uploaded_time','image_tag']


class TagAdmin(admin.ModelAdmin):
    fields = ['name', 'group']


class EbookConvertQueueAdmin(admin.ModelAdmin):
    list_display = ['volume','epub_ok','mobi_ok','mobi_push_ok','status','added_date']


class EbookConvertOverAdmin(admin.ModelAdmin):
    list_display = ['volume','epub_ok','mobi_ok','mobi_push_ok','status','over_date']



class HomePageGroupAdmin(admin.ModelAdmin):
    filter_vertical = ['books']


class HomePageSideSpecialAdmin(admin.ModelAdmin):
    list_display = ['name','book','desc']




admin.site.register(Book, BookAdmin)
admin.site.register(Volume)
admin.site.register(Author, AuthorAdmin)
admin.site.register(VolumeType)
admin.site.register(Tag, TagAdmin)
admin.site.register(ImageWithThumb, ImageAdmin)
admin.site.register(Permission)
admin.site.register(HomePageGroup,HomePageGroupAdmin)
admin.site.register(HomePageSpecialSide,HomePageSideSpecialAdmin)
admin.site.register(EbookConvertQueue,EbookConvertQueueAdmin)
admin.site.register(EbookConvertOver,EbookConvertOverAdmin)