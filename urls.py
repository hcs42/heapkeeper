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
# Copyright (C) 2012 Csaba Hoch

from django.conf.urls.defaults import *
from django.conf import settings

# Uncomment the next two lines to enable the admin:
#from django.contrib import admin
#admin.autodiscover()

urlpatterns = patterns('hk.views',
    url(r'^testmessage/(?P<msg_id>\d+)/$',
        view='testgetmsg',
        name='testgetmsg'),
    url(r'^editmessage/(?P<obj_id>\d+)/$',
        view='editmessage',
        name='editmessage'),
    url(r'^replymessage/(?P<obj_id>\d+)/$',
        view='replymessage',
        name='replymessage'),
    url(r'^conversation/(?P<conv_id>\d+)/$',
        view='conversation',
        name='conversation'),
    url(r'^heap/(?P<heap_id>\d+)/$',
        view='heap',
        name='heap'),
    url(r'^heap/$',
        view='heaps',
        name='heaps'),
    url(r'^addmessage/$',
        view='addmessage',
        name='addmessage'),
    url(r'^delmessage/(?P<obj_id>\d+)/$',
        view='delmessage',
        name='delmessage'),
    url(r'^addheap/$',
        view='addheap',
        name='addheap'),
    url(r'^addconv/(?P<obj_id>\d+)/$',
        view='addconv',
        name='addconv'),
    url(r'^addconv/$',
        view='addconv',
        name='addconv'),
    url(r'^delright/(?P<obj_id>\d+)/from/(?P<obj2_id>\d+)/$',
        view='deleteright',
        name='deleteright'),
    url(r'^addright/(?P<obj_id>\d+)/$',
        view='addright',
        name='addright'),
    url(r'^remove-conversation-label/(?P<label_text>[^/]+)/(?P<obj_id>\d+)/$',
        view='removeconversationlabel',
        name='removeconversationlabel'),
    url(r'^add-conversation-label/(?P<obj_id>\d+)/$',
        view='addconversationlabel',
        name='addconversationlabel'),
    url(r'^remove-message-label/(?P<label_text>[^/]+)/(?P<obj_id>\d+)/$',
        view='removemessagelabel',
        name='removemessagelabel'),
    url(r'^add-message-label/(?P<obj_id>\d+)/$',
        view='addmessagelabel',
        name='addmessagelabel'),
    url(r'^edit-subject/(?P<obj_id>\d+)/$',
        view='editsubject',
        name='editsubject'),
    url(r'^fsck/$',
        view='fsck',
        name='fsck'),
    url(r'^smtp/$',
        view='smtp',
        name='smtp'),
    url(r'^enable-smtp/(?P<port>\d+)/$',
        view='enable_smtp',
        name='enable_smtp'),
    url(r'^enable-smtp/$',
        view='enable_smtp',
        name='enable_smtp'),
    url(r'^disable-smtp/$',
        view='disable_smtp',
        name='disable_smtp'),

    url(r'^$',
        view='front',
        name='front'),

    url(r'^register/$',
        view='register',
        name='register'),
)

urlpatterns += patterns('django.contrib.auth.views',
    url(r'^login/$',
        view='login',
        name='login'),
    url(r'^logout/$',
        view='logout',
        kwargs={'next_page': '..'},
        name='logout'),
    url(r'^change-password/$',
        view='password_change',
        name='password_change',
        kwargs={'template_name': 'registration/password_change_form.html'}),
    url(r'^change-password/done/$',
        view='password_change_done',
        name='password_change_done',
        kwargs={'template_name': 'registration/password_change_done.html'}),
    url(r'^reset-password/$',
        view='password_reset',
        name='password_reset',
        kwargs={'template_name': 'registration/password_reset_form.html',
                'email_template_name': 'registration/password_reset_email.html'}),
    url(r'^reset-password/(?P<uidb36>[0-9A-Za-z]{1,13})-'
        r'(?P<token>[0-9A-Za-z]{1,13}-[0-9A-Za-z]{1,20})/$',
        view='password_reset_confirm',
        name='password_reset_confirm',
        kwargs={'template_name': 'registration/password_reset_confirm.html'}),
    url(r'^reset-password/done/$',
        view='password_reset_done',
        name='password_reset_done',
        kwargs={'template_name': 'registration/password_reset_done.html'}),
    url(r'^reset-password/complete/$',
        view='password_reset_complete',
        name='password_reset_complete',
        kwargs={'template_name': 'registration/password_reset_complete.html'}),
)

if settings.DEBUG:
    urlpatterns += patterns('',
        (r'^site_media/(?P<path>.*)$',
         'django.views.static.serve',
         {'document_root': settings.STATIC_DOC_ROOT}),
    )
