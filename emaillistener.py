
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

import asyncore
import base64
import datetime
import email
import email.header
import quopri
import re
import smtpd
import time
import multiprocessing
from django.contrib.contenttypes.models import ContentType
from django.core.exceptions import PermissionDenied
from django.core.urlresolvers import reverse
from django.shortcuts import render, redirect
from hk.models import *


##### SMTP server to receive mail

email_thread = None

def normalize_str(s):
    s = re.sub(r'\r\n', r'\n', s) # Windows EOL
    s = re.sub(r'\xc2\xa0', ' ', s) # Non-breaking space
    return s

def utf8(s, charset):
    if charset is not None:
        return s.decode(charset).encode('utf-8')
    else:
        return s

class FakeSMTPServer(smtpd.DebuggingServer):
    def __init__(*args, **kwargs):
        smtpd.SMTPServer.__init__(*args, **kwargs)

    def process_message(self, peer, mailfrom, rcpttos, data):
        print 'Received mail from %s to %s.' % (mailfrom, rcpttos,)
        mail = email.message_from_string(data)

        subject = email.header.decode_header(mail['Subject'])[0][0]
        message_id = email.header.decode_header(mail['Message-ID'])[0][0]
        in_reply_to = email.header.decode_header(mail['In-Reply-To'])[0][0]

        text = mail.get_payload()
        encoding = mail['Content-Transfer-Encoding']
        if encoding != None:
            if encoding.lower() in ('7bit', '8bit', 'binary'):
                pass # no conversion needed
            elif encoding.lower() == 'base64':
                text = base64.b64decode(text)
            elif encoding.lower() == 'quoted-printable':
                text = quopri.decodestring(text)
            else:
                print('WARNING: Unknown encoding, skipping decoding: '
                            '%s\n'
                            'text:\n%s\n' % (encoding, text))
        charset = mail.get_content_charset()
        text = utf8(text, charset)
        text = normalize_str(text)

        message_from_mail(mailfrom, rcpttos,
                          subject, message_id, in_reply_to,
                          text)


def server_thread(port=25):
    smtp_server = FakeSMTPServer(('0.0.0.0', port), None)
    asyncore.loop()

def run_server_thread(port):
    global email_thread
    if email_thread is not None and email_thread.is_alive():
        print "STMP thread already running!"
        return
    email_thread = multiprocessing.Process(target=server_thread,
                                           args=(int(port),))
    email_thread.start()
    print "STMP thread started."

def stop_server_thread():
    email_thread.terminate()

##### Mail to message

# This is function is almost verbatim from the first generation Hk
def parse_subject(subject):
    """Parses the subject of an email.

    Parses the labels and removes the "Re:" prefix and whitespaces.

    **Argument:**

    - `subject` (str)

    **Returns:** (str, [str]) -- The remaining subject and the labels.
    """

    # last_bracket==None  <=>  we are outside of a [label]
    last_bracket = None
    brackets = []
    i = 0
    while i < len(subject):
        c = subject[i]
        if c == '[' and last_bracket == None:
            last_bracket = i
        elif c == ']' and last_bracket != None:
            brackets.append((last_bracket, i))
            last_bracket = None
        elif c != ' ' and last_bracket == None:
            break
        i += 1

    real_subject = subject[i:]
    if re.match('[Rr]e:', subject):
        subject = subject[3:]
    real_subject = real_subject.strip()

    labels = [ subject[first+1:last].strip() for first, last in brackets ]
    return real_subject, labels

def message_from_mail(mailfrom, rcpttos,
                      subject, message_id, in_reply_to,
                      text):
    # TODO Add access control!!!
    # TODO Should cross posting be allowed?

    heaps = []
    for rcpt in rcpttos:
        heapname = re.search('^([^@].*)@', rcpt).group(1)
        try:
            heap = Heap.objects.get(short_name=heapname)
            heaps.append(heap)
        except Heap.DoesNotExist:
            print '%s attempted to post to nonexistent heap "%s".' % (mailfrom, heapname)

    for heap in heaps:
        # Cross-posting is enabled for now

        now = datetime.datetime.now()
        try:
            r = re.compile('[-._A-Za-z0-9]+@[-._A-Za-z0-9]+')
            match = r.search(mailfrom)
            if match is not None:
                sender_mail = match.group(0)
                author = User.objects.get(email=sender_mail)
            else:
                author = None
        except User.DoesNotExist:
            author = None

        try:
            parent = Message.objects.get(message_id=in_reply_to)
        except Message.DoesNotExist:
            parent = None

        real_subject, labels = parse_subject(subject)

        msg = Message()
        msg.message_id = message_id
        msg.save()
        mv = MessageVersion(
                message=msg,
                author=author,
                creation_date=now,
                version_date=now,
                parent=parent,
                text=text
            )
        mv.save()

        if parent is None:
            conv = Conversation(
                    heap=heap,
                    subject=real_subject,
                    root_message=msg
                )
            conv.save()
            label_target = conv
        else:
            label_target = msg

        label_target.add_label(labels)


##### "smtp" views

def smtp(request):
    # Must be admin to use
    global email_thread

    if not request.user.is_superuser:
        raise PermissionDenied

    if email_thread is None:
        alive = False
    else:
        alive = email_thread.is_alive()

    return render(
               request,
               'smtp.html',
               {'running': alive})

def enable_smtp(request, port=25):
    # Must be admin to use
    if not request.user.is_superuser:
        raise PermissionDenied
    
    run_server_thread(port)
    
    return redirect(reverse('hk.views.smtp'))

def disable_smtp(request):
    # Must be admin to use
    global email_thread

    if not request.user.is_superuser:
        raise PermissionDenied
    
    stop_server_thread()
    
    return redirect(reverse('hk.views.smtp'))
