from django.db import models
from django.contrib.auth.models import User

class Message(models.Model):
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
    text = models.CharField(max_length=64)

    def __unicode__(self):
        return "%s (#%d)" % (
                self.text,
                self.id,
            )


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
    users_have_read = models.ManyToManyField(User, null=True, blank=True)
    heap = models.ForeignKey(Heap)

    def __unicode__(self):
        return "Conversation #%s (%s)" % (
                self.id,
                self.subject,
            )

