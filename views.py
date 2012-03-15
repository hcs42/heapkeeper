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

from django.shortcuts import get_object_or_404, render, redirect
from django.http import HttpResponseRedirect, HttpResponse
from django.template import RequestContext
from django import forms
from django.contrib.auth.models import User
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.core.urlresolvers import reverse
import django.db
from hk.models import *
import datetime

##### Helper functions 

def format_labels(object):
    return '[%s]' % ', '.join([t.text for t in object.labels.all()])

def print_message(l, msg):
    children = msg.get_children()
    edit_url = reverse('hk.views.editmessage', args=(msg.id,))
    reply_url = reverse('hk.views.replymessage', args=(msg.id,))
    l.append("<div class='message'>\n")
    l.append("<a name='message_%d'></a>\n" % msg.id)
    l.append('<h3>\n&lt;%d&gt;\n</h3>\n' % msg.id)
    l.append('<h3>\n%s\n</h3>\n' % msg.latest_version().author)
    l.append('<h3>\n%s\n</h3>\n' % format_labels(msg.latest_version()))
    l.append('<h3>\n%s\n</h3>\n' % msg.latest_version().creation_date)
    l.append("<a href='%s'>edit</a>\n" % edit_url)
    l.append("<a href='%s'>reply</a>\n" % reply_url)
    l.append('<p>\n%s\n</p>\n' % msg.latest_version().text)
    for child in msg.get_children():
        print_message(l, child)
    l.append('</div>\n')

##### Simple views

def testgetmsg(request, msg_id):
    message = get_object_or_404(Message, pk=msg_id)
    latest_version = message.latest_version()
    message.get_heap().check_access(request.user, 0)
    return render(
            request,
            'testgetmsg.html',
            {'msgv': latest_version}
        )

def conversation(request, conv_id):
    conv = get_object_or_404(Conversation, pk=conv_id)
    conv.heap.check_access(request.user, 0)
    root = conv.root_message
    l = []
    print_message(l, root)
    ls = [unicode(m) for m in l]
    return render(
            request,
            'conversation.html',
            {'conv': conv,
             'conv_labels': format_labels(conv),
             'l': '\n'.join(ls)}
        )

def heap(request, heap_id):
    heap = get_object_or_404(Heap, pk=heap_id)
    heap.check_access(request.user, 0)
    convs = Conversation.objects.filter(heap=heap)
    visibility = heap.get_visibility_display

    # We do not display all userrights, only the effective ones, ie. the
    # highest value for each name.
    urights = []
    for user in heap.users():
        right = heap.get_effective_userright(user)
        urights.append({
                'name': user,
                'verb': ('is'
                    if right == 3
                    else 'can'),
                'right': UserRight.get_right_text(right)
            })
    # For (semi)public heaps, display right granted to 'everyone else'
    if heap.visibility < 2:
        right = 1 if heap.visibility == 0 else 0
        urights.append({
                'name': 'everyone else',
                # Anon is never heapadmin, so verb is always 'can'
                'verb': 'can',
                'right': UserRight.get_right_text(right)})

    return render(
            request,
            'heap.html',
            {'heap': heap,
             'visibility': visibility,
             'convs': convs,
             'urights': urights}
        )

def heaps(request):
    heaps = [heap for heap in Heap.objects.all()
                if heap.is_visible_for(request.user)]
    return render(
            request,
            'heaps.html',
            {'heaps': heaps}
        )

##### Generic framework for form-related views

def make_view(form_class, initializer, creator, displayer,
              creation_access_controller=None,
              display_access_controller=None):
    def generic_view(request, obj_id=None):
        variables = \
            {
                'request': request,
                'error_message': '',
                'obj_id': obj_id,
                'form_class': form_class
            }
        initializer(variables)
        if display_access_controller is not None:
            display_access_controller(variables)
        variables['form'] = form_class(initial=variables.get('form_initial'))
        if request.method == 'POST':
            variables['form'] = form_class(request.POST)
            if variables['form'].is_valid():
                if creation_access_controller is not None:
                    creation_access_controller(variables)
                creator(variables)
        return displayer(variables)

    return generic_view

def make_displayer(template, template_vars):
    def generic_displayer(variables):
        template_dict = dict([(tv, variables[tv]) for tv in template_vars])
        return render(
                variables['request'],
                template,
                template_dict)

    return generic_displayer

##### "Front page" view

def front(request):
    user = request.user
    if user.is_authenticated():
        username = user.username
    else:
        username = None
    heaps = [heap for heap in Heap.objects.all()
                if heap.is_visible_for(user)]
    return render(
               request,
               'front.html',
               {'username': username,
                'heaps': heaps})

##### "Register" view

def create_user(request, username, password1, password2, email_address,
                captcha):

    if captcha.strip() != '6':
        raise HkException('Some fields are invalid.')
    elif password1 != password2:
        raise HkException('The two passwords do not match.')
    #elif len(password1) < 6:
    #    raise HkException('The password has to be at least 6 '
    #                             'characters long!')
    else:

        try:
            user = User.objects.create_user(username, email_address, password1)
        except django.db.IntegrityError:
            raise HkException('This username is already used.')

        user.save()

        # Should be 'messages.succes(request, 'text')
        print 'Successful registration. Please log in!'

        front_url = reverse('hk.views.front', args=[])
        return HttpResponseRedirect(front_url)


def register(request):

    class RegisterForm(forms.Form):
        username = forms.CharField(max_length=255,
                                   label='Username')
        password1 = forms.CharField(max_length=255,
                                    widget=forms.PasswordInput,
                                    label='Password')
        password2 = forms.CharField(max_length=255,
                                    widget=forms.PasswordInput,
                                    label='Password again')
        email = forms.CharField(max_length=255,
                                        label='Email address')
        c = forms.CharField(max_length=255,
                            label='3 + 3 =')

    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            username = form.cleaned_data['username']
            password1 = form.cleaned_data['password1']
            password2 = form.cleaned_data['password2']
            email_address = form.cleaned_data['email']
            captcha = form.cleaned_data['c']
            try:
                return create_user(request, username, password1, password2,
                                   email_address, captcha)
            except HkException, e:
                # Should be 'messages.succes(request, 'text')
                print e.value
        else:
            # Should be 'messages.succes(request, 'text')
            print 'Some fields are invalid.'

    elif request.method == 'GET':
        form = RegisterForm()

    else:
        assert(False)

    return render(
               request,
               'registration/register.html',
               {'form':  form})

##### "Add conversation" view

class AddConversationForm(forms.Form):
    heap = forms.IntegerField()
    author = forms.IntegerField()
    subject = forms.CharField()
    text = forms.CharField(widget=forms.Textarea())

def addconv_init(variables):
    form_initial = {
                'heap': variables['obj_id']
            }
    variables['form_initial'] = form_initial

def addconv_creation_access_controller(variables):
    form = variables['form']
    heap = Heap.objects.get(pk=form.cleaned_data['heap'])
    # Needs alter level if user wants to start conversation in someone
    # else's name
    if variables['request'].user.id != form.cleaned_data['author']:
        needed_level = 2 
    else:
        needed_level = 1
    heap.check_access(variables['request'].user, needed_level)

def addconv_creator(variables):
    now = datetime.datetime.now()
    root_msg = Message()
    root_msg.save()
    form = variables['form']
    mv = MessageVersion(
            message=Message.objects.get(id=root_msg.id),
            author=User.objects.get(id=form.cleaned_data['author']),
            creation_date=now,
            version_date=now,
            text=form.cleaned_data['text']
        )
    mv.save()
    conv = Conversation(
            heap_id=form.cleaned_data['heap'],
            subject=form.cleaned_data['subject'],
            root_message=root_msg
        )
    conv.save()
    variables['form'] = variables['form_class']()
    variables['error_message'] = 'Conversation started.'


addconv = make_view(
                AddConversationForm,
                addconv_init,
                addconv_creator,
                make_displayer('addconv.html', ('error_message', 'form')),
                addconv_creation_access_controller
            )

##### "Add heap" view

# TODO: user has to be non-anonymous to add heaps
class AddHeapForm(forms.Form):
    short_name = forms.CharField()
    long_name = forms.CharField()

def addheap_creator(variables):
    form = variables['form']
    heap = Heap(
            short_name=form.cleaned_data['short_name'],
            long_name=form.cleaned_data['long_name'],
            visibility=0
        )
    heap.save()
    variables['form'] = variables['form_class']()
    variables['error_message'] = 'Heap added.'

def addheap_access_controller(variables):
    if variables['request'].user.is_anonymous():
        raise PermissionDenied

addheap = make_view(
                AddHeapForm,
                lambda x: None,
                addheap_creator,
                make_displayer('addheap.html', ('error_message', 'form')),
                addheap_access_controller,
                addheap_access_controller
            )

##### "Add message" view

class AddMessageForm(forms.Form):
    parent = forms.IntegerField()
    author = forms.IntegerField()
    text = forms.CharField(widget=forms.Textarea())

def addmessage_creation_access_controller(variables):
    form = variables['form']
    parent = Message.objects.get(pk=form.cleaned_data['parent'])
    heap = parent.get_heap()
    if variables['request'].user.id != form.cleaned_data['author']:
        needed_level = 2 
    else:
        needed_level = 1
    heap.check_access(variables['request'].user, needed_level)

def addmessage_creator(variables):
    now = datetime.datetime.now()
    msg = Message()
    msg.save()
    form = variables['form']
    mv = MessageVersion(
            message=Message.objects.get(id=msg.id),
            parent=Message.objects.get(id=form.cleaned_data['parent']),
            author=User.objects.get(id=form.cleaned_data['author']),
            creation_date=now,
            version_date=now,
            text=form.cleaned_data['text']
        )
    mv.save()
    variables['form'] = variables['form_class']()
    variables['error_message'] = 'Message added.'
    form = AddMessageForm()


addmessage = make_view(
                AddMessageForm,
                lambda x: None,
                addmessage_creator,
                make_displayer('addmessage.html', ('error_message', 'form')),
                addmessage_creation_access_controller
            )

##### "Edit message" view

class EditMessageForm(forms.Form):
    parent = forms.IntegerField(required=False)
    author = forms.IntegerField()
    creation_date = forms.DateTimeField()
    text = forms.CharField(widget=forms.Textarea())

def editmessage_creation_access_controller(variables):
    form = variables['form']
    heap = variables['m'].get_heap()
    user = variables['request'].user
    msg = variables['m']
    # Editing someone else's post and giving a post to someone else
    # both require alter rights
    if user.id != msg.latest_version().author.id \
        or user.id != form.cleaned_data['author']:
        needed_level = 2 
    else:
        needed_level = 1
    heap.check_access(variables['request'].user, needed_level)

def editmessage_display_access_controller(variables):
    heap = variables['m'].get_heap()
    user = variables['request'].user
    msg = variables['m']
    if user.id != msg.latest_version().author.id:
        needed_level = 2 
    else:
        needed_level = 1
    heap.check_access(variables['request'].user, needed_level)

def editmessage_init(variables):
    m = get_object_or_404(Message, pk=variables['obj_id'])
    lv = m.latest_version()
    form_initial = {
                'creation_date': lv.creation_date,
                'author': lv.author_id,
                'parent': lv.parent_id,
                'text': lv.text
            }
    variables['m'] = m
    variables['lv'] = lv
    variables['form_initial'] = form_initial

def editmessage_creator(variables):
    now = datetime.datetime.now()
    form = variables['form']
    try:
        parent = Message.objects.get(id=form.cleaned_data['parent'])
    except ObjectDoesNotExist:
        parent = None
    mv = MessageVersion(
            message=Message.objects.get(id=variables['obj_id']),
            parent=parent,
            author=User.objects.get(id=form.cleaned_data['author']),
            creation_date=form.cleaned_data['creation_date'],
            version_date=now,
            text=form.cleaned_data['text']
        )
    mv.save()
    variables['error_message'] = 'Message saved.'
    root_msg = Message.objects.get(id=variables['obj_id']).get_root_message()
    conv_id = Conversation.objects.get(root_message=root_msg).id
    conv_url = reverse('hk.views.conversation', args=(conv_id,))
    return redirect(
            '%s#message_%d' %
                (conv_url, int(variables['obj_id']))
        )

editmessage = make_view(
                EditMessageForm,
                editmessage_init,
                editmessage_creator,
                make_displayer('editmessage.html', ('error_message', 'form', 'obj_id')),
                editmessage_creation_access_controller,
                editmessage_display_access_controller
            )

##### "Reply message" view

class ReplyMessageForm(forms.Form):
    author = forms.IntegerField()
    text = forms.CharField(widget=forms.Textarea())

def replymessage_init(variables):
    parent = get_object_or_404(Message, pk=variables['obj_id'])
    variables['parent'] = parent

def replymessage_display_access_controller(variables):
    parent = variables['parent']
    parent.get_heap().check_access(variables['request'].user, 1)

def replymessage_creation_access_controller(variables):
    parent = variables['parent']
    user = variables['request'].user
    if user.id != variables['form'].cleaned_data['author']:
        needed_level = 2 
    else:
        needed_level = 1
    parent.get_heap().check_access(variables['request'].user,
                                   needed_level)

def replymessage_creator(variables):
    now = datetime.datetime.now()
    msg = Message()
    msg.save()
    form = variables['form']
    mv = MessageVersion(
            message=Message.objects.get(id=msg.id),
            parent=variables['parent'],
            author=User.objects.get(id=form.cleaned_data['author']),
            creation_date=now,
            version_date=now,
            text=form.cleaned_data['text']
        )
    mv.save()
    variables['form'] = variables['form_class']()
    variables['error_message'] = 'Message added.'
    form = AddMessageForm()

replymessage = make_view(
                ReplyMessageForm,
                replymessage_init,
                replymessage_creator,
                make_displayer('replymessage.html', ('error_message', 'form', 'obj_id')),
                replymessage_creation_access_controller,
                replymessage_display_access_controller
            )
