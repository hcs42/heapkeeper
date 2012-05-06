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

from hk.models import *
import datetime
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.shortcuts import render

def get_admin_url(object):
    model = object.__class__
    content_type = ContentType.objects.get_for_model(model)
    return reverse('admin:%s_%s_change' % (content_type.app_label,
                                               content_type.model),
                       args=(object.id,))

##### "fsck" view

def fsck(request):
    # TODO add more useful admin links

    # Must be admin to use
    if not request.user.is_superuser:
        raise PermissionDenied

    res = "\n"
    all_ok = True
    start = datetime.datetime.now()
    print 'fsck operation initiated at %s' % start

    test = 'Test 1: Messages without message versions\n\n'
    print test
    res += test
    problem = []
    for msg in Message.objects.all():
        if MessageVersion.objects.filter(message=msg).count() == 0:
            problem.append(msg)
    for msg in problem:
        error = 'Message #%d has no message versions!' % msg.id
        print error
        res += error + ' <a href="%s">edit</a>' % get_admin_url(msg)
        all_ok = False

    test = '\n\n\nTest 2: Parentless non-deleted message with zero or multiple conversation\n\n'
    print test
    res += test
    zero = []
    many = []
    for msg in Message.objects.all():
        msg_lv = msg.latest_version()
        if msg_lv is None:
            continue # This has been covered in Test 1
        if (msg_lv.parent is None
                and not msg_lv.deleted):
            count = Conversation.objects.filter(root_message=msg).count()
            if count == 0:
                zero.append(msg)
            if count > 1:
                many.append(msg)
    for msg in zero:
        error = 'Root message #%d has no matching conversation!' % msg.id
        print error
        res += error + ' <a href="%s">edit</a>\n' % get_admin_url(msg)
        all_ok = False
    for msg in many:
        error = 'Root message #%d has multiple matching conversations!' % msg.id
        print error
        res += error + ' <a href="%s">edit</a>\n' % get_admin_url(msg)
        all_ok = False

    test = '\n\n\nTest 3: deleted message as parent\n\n'
    print test
    res += test
    problem = []
    for msg in Message.objects.all():
        msg_lv = msg.latest_version()
        if msg_lv.deleted:
            for msg_child in Message.objects.all():
                if msg_child.current_parent() == msg:
                    problem.append((msg, msg_child,))
    for msg, child in problem:
        error = 'Deleted message #%d is parent of message #%d!' % (msg.id, child.id,)
        print error
        res += error + ' <a href="%s">edit parent</a>' % get_admin_url(msg)
        res += ' <a href="%s">edit child</a>\n' % get_admin_url(child)
        all_ok = False

    test = '\n\n\nTest 4: parent message loops\n\n'
    print test
    res += test
    problem = []
    for msg in Message.objects.all():
        try:
            _ = msg.get_root_message(exception=True)
        except LoopException as loop:
            problem.extend(loop.messages)
            problem = list(set(problem))
    for msg in problem:
        error = 'Message #%d is in a parent loop!' % msg.id
        print error
        res += error + ' <a href="%s">edit</a>\n' % get_admin_url(msg)
        all_ok = False

    test = '\n\n\nTest 5: deleted message as conversation root\n\n'
    print test
    res += test
    problem = []
    for msg in Message.objects.all():
        if msg.is_deleted():
            count = Conversation.objects.filter(root_message=msg).count()
            if count > 0:
                problem.append(msg)
    for msg in problem:
        error = 'Deleted message #%d is the root of a conversation!' % msg.id
        print error
        res += error + ' <a href="%s">edit</a>\n' % get_admin_url(msg)
        all_ok = False

    test = '\n\n\nTest 6: conv with root that has parent\n\n'
    print test
    res += test
    problem = []
    for conv in Conversation.objects.all():
        if conv.root_message.current_parent() is not None:
            problem.append((conv, conv.root_message,))
    for conv, root in problem:
        error = 'Conversation #%d has root message (#%d) that has a parent!'\
                    % (conv.id, root.id)
        print error
        res += error + ' <a href="%s">edit</a>\n' % get_admin_url(root)
        all_ok = False
            
    test = '\n\n\nTest 7: unused labels\n\n'
    print test
    res += test
    problem = []
    for label in Label.objects.all():
        if label.messageversion_set.count() == 0 \
                and label.conversation_set.count() == 0:
            problem.append(label)
    for label in problem:
        error = "Label '%s' is unused!" % label.pk
        print error
        # TODO add link to admin page
        res += error
        all_ok = False

    test = '\n\n\nTest 8: heap without admin\n\n'
    print test
    res += test
    problem = []
    for heap in Heap.objects.all():
        if heap.userright_set.filter(right=3).count() == 0:
            problem.append(heap)
    for heap in problem:
        error = "Heap '%s' has no admin!" % heap.short_name
        print error
        # TODO add link to admin page
        res += error
        all_ok = False

    if all_ok:
        res = "Database checked, no errors found."
        print res
    return render(
               request,
               'fsck.html',
               {'res': res})

