from django.conf.urls.defaults import *

# Uncomment the next two lines to enable the admin:
#from django.contrib import admin
#admin.autodiscover()

urlpatterns = patterns('hk.views',
    (r'^testmessage/(?P<msg_id>\d+)/$', 'testgetmsg'),
    (r'^editmessage/(?P<msg_id>\d+)/$', 'editmessage'),
    (r'^conversation/(?P<conv_id>\d+)/$', 'conversation'),
    (r'^heap/(?P<heap_id>\d+)/$', 'heap'),
    (r'^heap/$', 'heaps'),
    (r'^testaddmessage/$', 'testaddmessage'),
)
