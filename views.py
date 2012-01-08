# Create your views here.
from django.shortcuts import get_object_or_404, render_to_response, redirect
from django.http import HttpResponseRedirect, HttpResponse
from django.template import RequestContext
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist
from hk.models import Message, MessageVersion, Conversation, Heap
import datetime

def testgetmsg(request, msg_id):
    message = get_object_or_404(Message, pk=msg_id)
    latest_version = message.latest_version()
    return render_to_response(
            'testgetmsg.html',
            {'msgv': latest_version}
        )

def format_labels(object):
    return '[%s]' % ', '.join([t.text for t in object.labels.all()])

def print_message(l, msg):
    children = msg.get_children()
    l.append("<div class='message'>\n")
    l.append("<a name='message_%d'></a>\n" % msg.id)
    l.append('<h3>\n&lt;%d&gt;\n</h3>\n' % msg.id)
    l.append('<h3>\n%s\n</h3>\n' % msg.latest_version().author)
    l.append('<h3>\n%s\n</h3>\n' % format_labels(msg.latest_version()))
    l.append('<h3>\n%s\n</h3>\n' % msg.latest_version().creation_date)
    l.append("<a href='/editmessage/%d/'>edit</a>\n" % msg.id)
    l.append('<p>\n%s\n</p>\n' % msg.latest_version().text)
    for child in msg.get_children():
        print_message(l, child)
    l.append('</div>\n')

def conversation(request, conv_id):
    conv = get_object_or_404(Conversation, pk=conv_id)
    root = conv.root_message
    l = []
    print_message(l, root)
    ls = [str(m) for m in l]
    return render_to_response(
            'conversation.html',
            {'conv': conv,
             'conv_labels': format_labels(conv),
             'l': '\n'.join(ls)}
        )

def heap(request, heap_id):
    heap = get_object_or_404(Heap, pk=heap_id)
    convs = Conversation.objects.filter(heap=heap)
    return render_to_response(
            'heap.html',
            {'heap': heap,
             'convs': convs}
        )

def heaps(request):
    return render_to_response('heaps.html',
            {'heaps': Heap.objects.all()}
        )

class AddMessageForm(forms.Form):
    parent = forms.IntegerField()
    author = forms.IntegerField()
    text = forms.CharField()

class EditMessageForm(forms.Form):
    parent = forms.IntegerField(required=False)
    author = forms.IntegerField()
    creation_date = forms.DateTimeField()
    text = forms.CharField()

def testaddmessage(request):
    error_message = ''
    if request.method == 'POST':
        form = AddMessageForm(request.POST)
        if not form.is_valid():
            error_message = form.errors
        else:
            # To create a message:
            # - create a message object
            # - create a related message version
            now = datetime.datetime.now()
            msg = Message()
            msg.save()
            mv = MessageVersion(
                    message=Message.objects.get(id=msg.id),
                    parent=Message.objects.get(id=form.cleaned_data['parent']),
                    author=User.objects.get(id=form.cleaned_data['author']),
                    creation_date=now,
                    version_date=now,
                    text=form.cleaned_data['text']
                )
            mv.save()
            error_message = 'Message added.'
    return render_to_response('testaddmessage.html',
            {'error_message': error_message},
            context_instance=RequestContext(request))

def editmessage(request, msg_id):
    error_message = ''
    m = get_object_or_404(Message, pk=msg_id)
    lv = m.latest_version()
    if request.method == 'POST':
        form = EditMessageForm(request.POST)
        if not form.is_valid():
            error_message = form.errors
        else:
            now = datetime.datetime.now()
            try:
                parent = Message.objects.get(id=form.cleaned_data['parent'])
            except ObjectDoesNotExist:
                parent = None
            mv = MessageVersion(
                    message=Message.objects.get(id=msg_id),
                    parent=parent,
                    author=User.objects.get(id=form.cleaned_data['author']),
                    creation_date=form.cleaned_data['creation_date'],
                    version_date=now,
                    text=form.cleaned_data['text']
                )
            mv.save()
            error_message = 'Message saved.'
            root_msg = Message.objects.get(id=msg_id).get_root_message()
            conv_id = Conversation.objects.get(root_message=root_msg).id
            return redirect(
                    '/conversation/%d/#message_%d' %
                        (conv_id, int(msg_id))
                )
    return render_to_response('editmessage.html',
            {'error_message': error_message,
             'msg_id': m.id,
             'cd': lv.creation_date.strftime('%d/%m/%y %H:%M:%S'),
             'lv': lv},
            context_instance=RequestContext(request))
