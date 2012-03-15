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

from django.db import models
from django.contrib.auth.models import User
from django.core import urlresolvers
from django.core.exceptions import PermissionDenied

class Message(models.Model):
    users_have_read = models.ManyToManyField(User, null=True, blank=True)

    def __unicode__(self):
        return "Message #%d" % (
                self.id,
            )

    def latest_version(self):
        version_list = list(MessageVersion.objects.filter(message=self))
        version_list.sort(key=lambda l: l.version_date)
        if len(version_list) == 0:
            return None
        else:
            return version_list[-1]

    def latest_version_link(self):
        latest = self.latest_version()
        url = urlresolvers.reverse(
                'admin:hk_messageversion_change',
                args=(latest.id,)
            )
        return '<a href="%s">%s</a>' % (url, latest)
    latest_version_link.allow_tags = True

    def current_parent(self):
        return self.latest_version().parent

    def get_root_message(self):
        # Does not check for cycles -- causes endless loop.
        msg = self
        while True:
            latest_parent = msg.latest_version().parent 
            if latest_parent is None:
                return msg
            msg = latest_parent

    def get_conversation(self):
        root_message = self.get_root_message
        return Conversation.objects.get(root_message=root_message)

    def get_heap(self):
        return self.get_conversation().heap

    def get_children(self):
        return [m for m in Message.objects.all() if m.current_parent() == self]


class Label(models.Model):
    text = models.CharField(max_length=64, primary_key=True)

    def __unicode__(self):
        return "%s" % self.text


class MessageVersion(models.Model):
    message = models.ForeignKey(Message, related_name='message')
    parent = models.ForeignKey(Message, related_name='parent', null=True, blank=True)
    author = models.ForeignKey(User)
    creation_date = models.DateTimeField('message creation date')
    version_date = models.DateTimeField('version creation date')
    text = models.TextField('the text of the message')
    labels = models.ManyToManyField(Label, null=True, blank=True)

    def __unicode__(self):
        labels = ', '.join([label.text for label in self.labels.all()])
        return "MessageVersion #%d (labels: %s, text: %s)" % (
                self.id,
                labels or '<none>',
                self.text[0:32],
            )


class Heap(models.Model):
    HEAP_VISIBILITY_CHOICES = (
           (0, 'Public'),
           (1, 'Semipublic'),
           (2, 'Private'),
       )
    visibility = models.SmallIntegerField(choices=HEAP_VISIBILITY_CHOICES)
    short_name = models.CharField(max_length=64)
    long_name = models.CharField(max_length=256)
    user_fields = models.ManyToManyField(User, through='UserRight')

    def __unicode__(self):
        return "Heap '%s'" % (
                self.short_name,
            )

    def check_access(self, user, level_needed):
        print 'user %d is trying to perform action with needed level %d' \
                % (user.id, level_needed)
        print 'effective user right: %d' \
                % self.get_effective_userright(user)
        print 'user is%s superuser' \
                % (' not' if not user.is_superuser else '')
        if self.get_effective_userright(user) < level_needed:
            raise PermissionDenied

    def get_given_userright(self, user):
        # This is the right actually assigned to the user via a UserRight
        # object. The visibility of the heap and superuser status is not taken
        # into account.
        if not user.is_authenticated():
            return -1
        highest = None
        for uright in self.userright_set.filter(user=user):
            if highest is None or uright.right > highest.right:
                highest = uright
        return highest.right if highest is not None else -1

    def get_effective_userright(self, user):
        # Superusers are heapadmins on all heaps
        if user.is_superuser:
            return 3
        given_right = self.get_given_userright(user)
        visibility = self.visibility
        visibility_rights_dict = \
            {
                0: 1, # Public heaps can at least be sent to,
                1: 0, # Semipublic heaps cat at least be read,
                2: -1 # Private heaps give no rights to anyone.
            }
        visibility_right = visibility_rights_dict[visibility]
        return max(given_right, visibility_right)

    def users(self):
        return list(set(self.user_fields.all()))


class UserRight(models.Model):
    RIGHT_CHOICES = (
           (0, 'read'),
           (1, 'send'),
           (2, 'alter'),
           (3, 'heapadmin'),
       )
    user = models.ForeignKey(User)
    heap = models.ForeignKey(Heap)
    right = models.SmallIntegerField(choices=RIGHT_CHOICES)
    unique_together = ('user', 'heap')

    def __unicode__(self):
        return "%s: %s is %s" % (
                self.heap,
                self.user,
                self.get_right_display(),
            )


class Conversation(models.Model):
    subject = models.CharField(max_length=256) 
    labels = models.ManyToManyField(Label, null=True, blank=True)
    root_message = models.ForeignKey(Message)
    heap = models.ForeignKey(Heap)

    def __unicode__(self):
        return "Conversation #%s (%s)" % (
                self.id,
                self.subject,
            )

class HkException(Exception):
    """A very simple exception class used."""

    def __init__(self, value):
        """Constructor.

        **Argument:**

        - `value` (object) -- The reason of the error.
        """
        Exception.__init__(self)
        self.value = value

    def __unicode__(self):
        """Returns the string representation of the error reason.

        **Returns:** str
        """

        value = self.value
        if isinstance(value, unicode):
            return value
        elif isinstance(value, str):
            return unicode(value)
        else:
            return repr(value)
