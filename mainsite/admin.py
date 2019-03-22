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
    list_display = ["id", "name"]
    list_display_links = ["id", "name"]
    readonly_fields = ["id"]
    inlines = [BookAuthorBridgeAdmin]


class VolumeInline(admin.StackedInline):
    model = Volume
    fiel = ['name', ]
    fieldsets = [
        [None, {"fields": ['index', ('volume_number', 'name', 'show', 'need_convert'), 'type', ]}],
        [None, {"fields": ['zip_file', 'epub_file', 'mobi_file', 'mobi_push_file']}],
    ]
    extra = 0
    readonly_fields = ['need_convert', 'name', 'show']
    ordering = ['index']


class BookAdmin(admin.ModelAdmin):
    list_display = ["id", "title", "update_time"]
    list_display_links = ['id', 'title']
    fieldsets = [
        ["基本情報", {'fields': ['id', 'title', 'title_chinese', 'update_time', 'end', 'show', 'go_to_book_info_page'], }],
        ["作者", {"fields": ['author']}],
        ["Tag", {"fields": ['tags']}],
        ["Cover", {"fields": ["relative_covers_tags", "cover_id"]}],
        ["Summary", {"fields": ["desc"]}],
    ]
    readonly_fields = ['id', 'update_time', 'relative_covers_tags', 'cover_id']
    filter_horizontal = ['author', 'tags']
    inlines = [VolumeInline]

    # autocomplete_fields = ['author']
    # formfield_overrides = {
    #     models.TextField: {'widget': Textarea(attrs= { 'rows': '1'})},
    # }

    def save_model(self, request, obj, form, change):
        if obj.id is None: obj.save()
        if 'uploaded_image' in request.FILES:
            new_image_model = ImageWithThumb(image=request.FILES['uploaded_image'], thumb_image=File(None, None),
                                             normal_image=File(None, None))
            new_image_model.save()
            obj.covers.add(new_image_model)
            obj.setCover(new_image_model.id)
        else:
            obj.setCover(form.data.get("cover_select_radio", ""))
        super().save_model(request, obj, form, change)



class ImageAdmin(admin.ModelAdmin):
    fields = ['id', 'image', 'image_tag', 'uploaded_time']
    readonly_fields = ['uploaded_time', 'image_tag']


class TagAdmin(admin.ModelAdmin):
    fields = ['name', 'group']


class EbookConvertQueueAdmin(admin.ModelAdmin):
    list_display = ['volume', 'epub_ok', 'mobi_ok', 'mobi_push_ok', 'status', 'added_date']
    ordering = ['added_date']


class EbookConvertOverAdmin(admin.ModelAdmin):
    list_display = ['volume', 'epub_ok', 'mobi_ok', 'mobi_push_ok', 'status', 'over_date']


class HomePageGroupAdmin(admin.ModelAdmin):
    filter_vertical = ['books']


class HomePageSideSpecialAdmin(admin.ModelAdmin):
    list_display = ['name', 'book', 'desc']


admin.site.register(Book, BookAdmin)
admin.site.register(Volume)
admin.site.register(Author, AuthorAdmin)
admin.site.register(VolumeType)
admin.site.register(Tag, TagAdmin)
admin.site.register(ImageWithThumb, ImageAdmin)
admin.site.register(Permission)
admin.site.register(HomePageGroup, HomePageGroupAdmin)
admin.site.register(HomePageSpecialSide, HomePageSideSpecialAdmin)
admin.site.register(EbookConvertQueue, EbookConvertQueueAdmin)
admin.site.register(EbookConvertOver, EbookConvertOverAdmin)
