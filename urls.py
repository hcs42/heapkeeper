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

from django.conf.urls.defaults import *
from django.conf import settings

# Uncomment the next two lines to enable the admin:
#from django.contrib import admin
#admin.autodiscover()

urlpatterns = patterns('hk.views',
    (r'^testmessage/(?P<msg_id>\d+)/$', 'testgetmsg'),
    (r'^editmessage/(?P<obj_id>\d+)/$', 'editmessage'),
    (r'^replymessage/(?P<obj_id>\d+)/$', 'replymessage'),
    (r'^conversation/(?P<conv_id>\d+)/$', 'conversation'),
    (r'^heap/(?P<heap_id>\d+)/$', 'heap'),
    (r'^heap/$', 'heaps'),
    (r'^addmessage/$', 'addmessage'),
    (r'^addheap/$', 'addheap'),
    (r'^addconv/(?P<obj_id>\d+)/$', 'addconv'),
    (r'^addconv/$', 'addconv'),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^site_media/(?P<path>.*)$',
         'django.views.static.serve',
         {'document_root': settings.STATIC_DOC_ROOT}),
    )
