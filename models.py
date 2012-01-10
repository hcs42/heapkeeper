
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

from django.db import models
from django.contrib.auth.models import User

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
        url = '/admin/hk/messageversion/%d/' % latest.id
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

