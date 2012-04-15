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
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import ObjectDoesNotExist, PermissionDenied
from django.http import Http404
from django.core.urlresolvers import reverse
from fsck import fsck
import django.db
from hk.models import *
import datetime

##### Helper functions 

def format_labels(obj, conv=False):
    labels = ['%s <a class="rmlabel" href="%s">x</a>'
                % (label.pk,
                    reverse('hk.views.removeconversationlabel',
                        args=(label.pk, obj.id,)))
                for label in obj.labels.all()]
    if conv:
        labels.append('<a class="addlabel" href="%s">+</a>'
                        % reverse('hk.views.addconversationlabel',
                            args=(obj.id,)))
    return '[%s]' % ', '.join([l for l in labels])

def print_message(l, msg):
    children = msg.get_children()
    edit_url = reverse('hk.views.editmessage', args=(msg.id,))
    reply_url = reverse('hk.views.replymessage', args=(msg.id,))
    delete_url = reverse('hk.views.delmessage', args=(msg.id,))
    l.append("<div class='message'>\n")
    l.append("<a name='message_%d'></a>\n" % msg.id)
    l.append('<h3>\n&lt;%d&gt;\n</h3>\n' % msg.id)
    l.append('<h3>\n%s\n</h3>\n' % msg.latest_version().author)
    l.append('<h3>\n%s\n</h3>\n' % format_labels(msg.latest_version()))
    l.append('<h3>\n%s\n</h3>\n' % msg.latest_version().creation_date)
    l.append("<a href='%s'>edit</a>\n" % edit_url)
    l.append("<a href='%s'>reply</a>\n" % reply_url)
    l.append("<a href='%s'>delete</a>\n" % delete_url)
    l.append('<p>\n%s\n</p>\n' % msg.latest_version().text)
    for child in msg.get_children():
        print_message(l, child)
    l.append('</div>\n')

def add_children_recursively(l, root):
    for child in root.get_children():
        l.append(child)
        add_children_recursively(l, child)

def remove_children_recursively(l, root):
    for child in root.get_children():
        l.remove(child)
        remove_children_recursively(l, child)

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
    if not root.is_deleted():
        print_message(l, root)
    else:
        raise Http404
    ls = [unicode(m) for m in l]
    return render(
            request,
            'conversation.html',
            {'conv': conv,
             'conv_labels': format_labels(conv, conv=True),
             'l': '\n'.join(ls)}
        )

def heap(request, heap_id):
    heap = get_object_or_404(Heap, pk=heap_id)
    heap.check_access(request.user, 0)
    heapadmin = heap.get_effective_userright(request.user) == 3
    convs = Conversation.objects.filter(heap=heap)
    visibility = heap.get_visibility_display

    # We do not display all userrights, only the effective ones, ie. the
    # highest value for each name.
    urights = []
    for user in heap.users():
        right = heap.get_effective_userright(user)
        urights.append({
                'uid': user.id,
                'name': user,
                'verb': ('is'
                    if right == 3
                    else 'can'),
                'right': UserRight.get_right_text(right),
            })
    # For (semi)public heaps, display right granted to 'everyone else'
    if heap.visibility < 2:
        right = 1 if heap.visibility == 0 else 0
        urights.append({
                'uid': -1,
                'name': 'everyone' if len(urights) == 0 \
                    else 'everyone else',
                # Anon is never heapadmin, so verb is always 'can'
                'verb': 'can',
                'right': UserRight.get_right_text(right),
                'controls': ''})

    return render(
            request,
            'heap.html',
            {'heap': heap,
             'visibility': visibility,
             'convs': convs,
             'urights': urights,
             'heapadmin': heapadmin}
        )

def heaps(request):
    heaps = [heap for heap in Heap.objects.all()
                if heap.is_visible_for(request.user)]
    return render(
            request,
            'heaps.html',
            {'heaps': heaps}
        )

def removeconversationlabel(request, label_text, obj_id):
    conv = get_object_or_404(Conversation, pk=obj_id)
    if request.user.id == conv.root_message.latest_version().author.id:
        needed_level = 1
    else:
        needed_level = 2 
    conv.heap.check_access(request.user, needed_level)
    label = get_object_or_404(Label, pk=label_text)
    conv.labels.remove(label)
    conv.save()
    if label.messageversion_set.count() == 0 \
            and label.conversation_set.count() == 0:
        label.delete()
    return redirect(reverse('hk.views.conversation', args=(conv.id,)))

##### Generic framework for form-related views

def make_view(form_class, initializer, creator, displayer,
              creation_access_controller=None,
              display_access_controller=None,
              form_postprocessor=None):
    def generic_view(request, obj_id=None, obj2_id=None):
        variables = \
            {
                'request': request,
                'error_message': '',
                'obj_id': obj_id,
                'obj2_id': obj2_id,
                'form_class': form_class
            }
        initializer(variables)
        if display_access_controller is not None:
            display_access_controller(variables)
        variables['form'] = form_class(initial=variables.get('form_initial'))
        if form_postprocessor is not None:
            form_postprocessor(variables)
        if request.method == 'POST':
            variables['form'] = form_class(request.POST)
            if form_postprocessor is not None:
                form_postprocessor(variables)
            if variables['form'].is_valid():
                if creation_access_controller is not None:
                    creation_access_controller(variables)
                # If the creator returns anything, it is a redirect
                res = creator(variables)
                if res is not None:
                    return res
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
    heap = forms.ModelChoiceField(queryset=Heap.objects.all())
    author = forms.ModelChoiceField(queryset=User.objects.all())
    subject = forms.CharField()
    text = forms.CharField(widget=forms.Textarea())

def addconv_init(variables):
    form_initial = {
                'heap': variables['obj_id'],
                'author': variables['request'].user
            }
    variables['form_initial'] = form_initial

def addconv_creation_access_controller(variables):
    form = variables['form']
    heap = form.cleaned_data['heap']
    # Needs alter level if user wants to start conversation in someone
    # else's name
    if variables['request'].user.id != form.cleaned_data['author'].id:
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
            author=form.cleaned_data['author'],
            creation_date=now,
            version_date=now,
            text=form.cleaned_data['text']
        )
    mv.save()
    conv = Conversation(
            heap=form.cleaned_data['heap'],
            subject=form.cleaned_data['subject'],
            root_message=root_msg
        )
    conv.save()
    variables['form'] = variables['form_class']()
    variables['error_message'] = 'Conversation started.'
    conv_url = reverse('hk.views.conversation', args=(conv.id,))
    return redirect(conv_url)

addconv = make_view(
                AddConversationForm,
                addconv_init,
                addconv_creator,
                make_displayer('addconv.html', ('error_message', 'form')),
                addconv_creation_access_controller
            )

##### "Add heap" view

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
    ur = UserRight(
            user = variables['request'].user,
            heap = heap,
            right = 3
        )
    ur.save()
    variables['form'] = variables['form_class']()
    variables['error_message'] = 'Heap added.'
    heap_url = reverse('hk.views.heap', args=(heap.id,))
    return redirect(heap_url)

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
    parent = forms.ModelChoiceField(queryset=Message.objects.all(),
                                    required=False)
    author = forms.ModelChoiceField(queryset=User.objects.all())
    text = forms.CharField(widget=forms.Textarea())

def addmessage_creation_access_controller(variables):
    form = variables['form']
    parent = form.cleaned_data['parent']
    heap = parent.get_heap()
    if variables['request'].user.id != form.cleaned_data['author'].id:
        needed_level = 2 
    else:
        needed_level = 1
    heap.check_access(variables['request'].user, needed_level)

def addmessage_init(variables):
    variables['form_initial'] = {
            'author': variables['request'].user
        }


def addmessage_creator(variables):
    now = datetime.datetime.now()
    msg = Message()
    msg.save()
    form = variables['form']
    mv = MessageVersion(
            message=Message.objects.get(id=msg.id),
            parent=form.cleaned_data['parent'],
            author=form.cleaned_data['author'],
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
                addmessage_init,
                addmessage_creator,
                make_displayer('addmessage.html', ('error_message', 'form')),
                addmessage_creation_access_controller
            )

##### "Delete message" view

class DelMessageConfirmForm(forms.Form):
    really_delete = forms.BooleanField()

def delmessage_access_controller(variables):
    message = variables['message']
    heap = message.get_heap()
    if variables['request'].user.id != message.latest_version().author.id:
        needed_level = 2 
    else:
        needed_level = 1
    heap.check_access(variables['request'].user, needed_level)

def delmessage_init(variables):
    msg_id = variables['obj_id']
    variables['message'] = Message.objects.get(pk=msg_id)

def delmessage_creator(variables):
    message = variables['message']
    heap = message.get_heap()
    conv = message.get_conversation()
    parent = message.current_parent()
    children = message.get_children()

    # Step 1: if message is root, delete conv and redirect to heap
    if parent is None:
        conv.delete()
        redirect_url = reverse('hk.views.heap',
            args=(heap.id,))
    else:
        # Otherwise redirect back to the conversation
        redirect_url = reverse('hk.views.conversation',
            args=(parent.get_conversation().id,))

    # Step 2: if message has children, give them their own
    # conversations, and remove their parents
    for child in children:
        child.change(parent=None)
        child_conv = Conversation(
                heap=heap,
                subject=conv.subject,
                root_message=child
            )
        child_conv.save()

    # Step 3: delete message
    variables['message'].mark_deleted()
    variables['error_message'] = 'Message deleted.'
    return redirect(redirect_url)

delmessage = make_view(
                DelMessageConfirmForm,
                delmessage_init,
                delmessage_creator,
                make_displayer('deletemessage.html',
                                ('message', 'error_message', 'form')),
                delmessage_access_controller,
                delmessage_access_controller
            )

##### "Edit message" view

class EditMessageForm(forms.Form):
    def editmessage_coerce(id):
        id = int(id)
        if id == 0:
            return None
        else:
            return Message.objects.get(pk=id)

    # parent field created by editmessage_form_postprocessor
    #parent = forms.ModelChoiceField(queryset=Message.objects.all(),
    #                                    required=False)
    parent = forms.TypedChoiceField(
                choices=(),
                empty_value=None,
                coerce=editmessage_coerce,
                required=False)
    author = forms.ModelChoiceField(queryset=User.objects.all())
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
                'author': lv.author,
                'parent': lv.parent.id if lv.parent is not None else 0,
                'text': lv.text
            }
    variables['m'] = m
    variables['lv'] = lv
    variables['form_initial'] = form_initial

def editmessage_form_postprocessor(variables):
    msg = variables['m']
    root = msg.get_root_message()
    possible_parents = [root]
    add_children_recursively(possible_parents, root)
    possible_parents.remove(msg)
    remove_children_recursively(possible_parents, msg)
    choices = [(msg.id, msg) for msg in possible_parents]
    choices.append((0, '(none)'))
    variables['form'].fields['parent'].choices = choices

def editmessage_creator(variables):
    # TODO It is still possible to create a loop via a crafted POST. Such cases
    # should be detected and denied.
    now = datetime.datetime.now()
    form = variables['form']
    msg = Message.objects.get(id=variables['obj_id'])
    msg_conv = msg.get_conversation()
    heap = msg.get_heap()
    curr_parent = msg.latest_version().parent
    try:
        new_parent = form.cleaned_data['parent']
    except DoesNotExist:
        new_parent = None
    mv = MessageVersion(
            message=msg,
            parent=new_parent,
            author=form.cleaned_data['author'],
            creation_date=form.cleaned_data['creation_date'],
            version_date=now,
            text=form.cleaned_data['text']
        )
    mv.save()
    # Joining conversations
    if curr_parent is None and new_parent is not None:
        msg_conv.delete()
    # Breaking conversation
    if curr_parent is not None and new_parent is None:
        new_conv = Conversation(
                heap=heap,
                subject=msg_conv.subject,
                root_message=msg
            )
        new_conv.save()
    # Redirect back to the conversation of the edited post (may differ
    # from msg_conv)
    conv_url = reverse('hk.views.conversation',
                        args=(msg.get_conversation().id,))
    variables['error_message'] = 'Message saved.'
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
                editmessage_display_access_controller,
                editmessage_form_postprocessor
            )

##### "Reply message" view

class ReplyMessageForm(forms.Form):
    author = forms.ModelChoiceField(queryset=User.objects.all())
    text = forms.CharField(widget=forms.Textarea())

def replymessage_init(variables):
    parent = get_object_or_404(Message, pk=variables['obj_id'])
    variables['parent'] = parent
    variables['form_initial'] = {
            'author': variables['request'].user
        }

def replymessage_display_access_controller(variables):
    parent = variables['parent']
    parent.get_heap().check_access(variables['request'].user, 1)

def replymessage_creation_access_controller(variables):
    parent = variables['parent']
    user = variables['request'].user
    if user.id != variables['form'].cleaned_data['author'].id:
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
            author=form.cleaned_data['author'],
            creation_date=now,
            version_date=now,
            text=form.cleaned_data['text']
        )
    mv.save()
    variables['form'] = variables['form_class']()
    variables['error_message'] = 'Message added.'
    form = ReplyMessageForm()
    conv_id = msg.get_conversation().id
    conv_url = reverse('hk.views.conversation', args=(conv_id,))
    return redirect(
            '%s#message_%d' %
                (conv_url, int(variables['obj_id']))
        )
    return redirect(conv_url)

replymessage = make_view(
                ReplyMessageForm,
                replymessage_init,
                replymessage_creator,
                make_displayer('replymessage.html', ('error_message', 'form', 'obj_id')),
                replymessage_creation_access_controller,
                replymessage_display_access_controller
            )

##### "Delete right" view

class DeleteRightConfirmForm(forms.Form):
    really_revoke_right = forms.BooleanField()

def deleteright_init(variables):
    target_user = get_object_or_404(User, pk=variables['obj_id'])
    variables['target_user'] = target_user
    heap = get_object_or_404(Heap, pk=variables['obj2_id'])
    variables['heap'] = heap

def deleteright_access_controller(variables):
    variables['heap'].check_access(variables['request'].user, 3)

def deleteright_creator(variables):
    if variables['form'].cleaned_data['really_revoke_right']:
        heap = variables['heap']
        target_user = variables['target_user']
        affected_rights = heap.userright_set.filter(user=target_user)
        affected_rights.delete()
        return redirect(reverse('hk.views.heap', args=(heap.id,)))

deleteright = make_view(
                DeleteRightConfirmForm,
                deleteright_init,
                deleteright_creator,
                make_displayer('deleteright.html',
                    ('error_message', 'form', 'obj_id', 'obj2_id')),
                deleteright_access_controller,
                deleteright_access_controller
            )

##### "Add right" view

class AddRightForm(forms.ModelForm):
    class Meta:
        model = UserRight
        exclude = ('heap',)

def addright_init(variables):
    heap = get_object_or_404(Heap, pk=variables['obj_id'])
    variables['heap'] = heap

def addright_creator(variables):
    heap = variables['heap']
    target_user = variables['form'].cleaned_data['user']
    given_right_now = heap.get_given_userright(target_user)
    target_right = variables['form'].cleaned_data['right']
    if target_right < given_right_now:
        variables['error_message'] = 'User already has higher privileges.'
        return
    if given_right_now != -1:
        heap.userright_set.filter(user=target_user).delete()  
    new_ur = UserRight(heap=heap, user=target_user,
                        right=target_right)
    new_ur.save()
    variables['error_message'] = 'OKOKOKOK'
    return redirect(reverse('hk.views.heap', args=(heap.id,)))

addright_access_controller = deleteright_access_controller
 
addright = make_view(
                AddRightForm,
                addright_init,
                addright_creator,
                make_displayer('addright.html',
                    ('error_message', 'form', 'obj_id')),
                addright_access_controller,
                addright_access_controller
            )

##### "Add conversation label" view

class AddConversationLabelForm(forms.Form):
    label = forms.CharField()

def addconversationlabel_init(variables):
    conv = get_object_or_404(Conversation, pk=variables['obj_id'])
    variables['conv'] = conv

def addconversationlabel_creator(variables):
    conv = variables['conv']
    label = variables['form'].cleaned_data['label']
    print "Adding label %s to conv %d." % (label, conv.id)
    try:
        label_obj = Label.objects.get(pk=label)
    except Label.DoesNotExist:
        label_obj = Label(text=label)
        label_obj.save()
    conv.labels.add(label_obj)
    conv.save()
    variables['error_message'] = 'OKOKOKOK'
    return redirect(reverse('hk.views.conversation', args=(conv.id,)))

def addconversationlabel_access_controller(variables):
    # If the root post is owned by the user, send (1) is needed,
    # otherwise alter (2).
    conv = variables['conv']
    root_author = conv.root_message.latest_version().author.id
    if variables['request'].user.id == root_author:
        needed_level = 1
    else:
        needed_level = 2 
    conv.heap.check_access(variables['request'].user, needed_level)

addconversationlabel = make_view(
                AddConversationLabelForm,
                addconversationlabel_init,
                addconversationlabel_creator,
                make_displayer('addconversationlabel.html',
                    ('error_message', 'form', 'obj_id')),
                addconversationlabel_access_controller,
                addconversationlabel_access_controller
            )

