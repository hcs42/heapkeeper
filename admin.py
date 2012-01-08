import hk.models
from django.contrib import admin

class MessageVersionInline(admin.StackedInline):
    model = hk.models.MessageVersion
    fieldsets = [
        (None, {'fields': ['author', 'parent']}),
        ('Header information',
            {
                'fields': ['creation_date', 'version_date', 'labels'],
                'classes': ['collapse']
            }
        ),
        (None, {'fields': ['text']}),
    ]
    fk_name = "message"
    extra = 1


class MessageAdmin(admin.ModelAdmin):
    inlines = [MessageVersionInline]
    readonly_fields = ('latest_version_link', 'get_root_message', 'get_children') 


class UserRightInline(admin.TabularInline):
    model = hk.models.UserRight
    extra = 1


class HeapAdmin(admin.ModelAdmin):
	inlines = [UserRightInline]


admin.site.register(hk.models.Heap, HeapAdmin)
admin.site.register(hk.models.Conversation)
admin.site.register(hk.models.Message, MessageAdmin)
admin.site.register(hk.models.MessageVersion)
admin.site.register(hk.models.Label)
admin.site.register(hk.models.UserRight)
