
# This file is part of Heapkeeper.
#
# Heapkeeper is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# Heapkeeper is distributed in the hope that it will be useful, but WITHOUT ANY
# WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR
# A PARTICULAR PURPOSE.  See the GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License along with
# Heapkeeper.  If not, see <http://www.gnu.org/licenses/>.

# Copyright (C) 2012 Attila Nagy

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
