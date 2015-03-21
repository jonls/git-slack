
"""Slack integration functions"""

import time
import urllib2
import json
from threading import Thread
from Queue import Queue
import logging
import string
from collections import Mapping

logger = logging.getLogger(__name__)


class AttachmentColor(object):
    """Predefined colors of attachments"""
    Good = 'good'
    Warning = 'warning'
    Danger = 'danger'


class Markup(unicode):
    """Markup-safe string that does not need escaping"""
    @classmethod
    def escape(cls, s):
        """Escape string into Markup object

        If already escape, or is an object that provides a custom
        markup, the result of the __markup__ method is returned.
        """
        if hasattr(s, '__markup__'):
            return s.__markup__()
        else:
            return Markup(s.replace('&', '&amp;').
                          replace('<', '&lt;').
                          replace('>', '&gt;'))

    def __markup__(self):
        return self

    def __add__(self, other):
        return Markup(super(Markup, self).__add__(Markup.escape(other)))

    def __radd__(self, other):
        return Markup.escape(other).__add__(self)

    def __mul__(self, count):
        return Markup(super(Markup, self).__mul__(count))

    def __rmul__(self, count):
        return Markup(super(Markup, self).__rmul__(count))

    def __mod__(self, arg):
        if isinstance(arg, tuple):
            arg = tuple(_MarkupEscapeHelper(x, Markup.escape) for x in arg)
        else:
            arg = _MarkupEscapeHelper(arg, Markup.escape)
        return Markup(super(Markup, self).__mod__(arg))

    def join(self, iterable):
        return Markup(super(Markup, self).join(
            Markup.escape(x) for x in iterable))

    def format(self, *args, **kwargs):
        formatter = _MarkupEscapeFormatter(Markup.escape)
        kwargs = _MagicFormatMapping(args, kwargs)
        return Markup(formatter.vformat(self, args, kwargs))

    def __repr__(self):
        return (self.__class__.__name__ +
                '(' + super(Markup, self).__repr__() + ')')


class _MagicFormatMapping(Mapping):
    """Workaround mapping for Python standard library bug"""

    def __init__(self, args, kwargs):
        self._args = args
        self._kwargs = kwargs
        self._last_index = 0

    def __getitem__(self, key):
        if key == '':
            index = self._last_index
            self._last_index += 1
            try:
                return self._args[index]
            except LookupError:
                pass
            key = str(index)
        return self._kwargs[key]

    def __iter__(self):
        return iter(self._kwargs)

    def __len__(self):
        return len(self._kwargs)


class _MarkupEscapeFormatter(string.Formatter):
    """Formatter for Markup.format"""
    def __init__(self, escape):
        self._escape = escape

    def format_field(self, value, format_spec):
        if hasattr(value, '__markup__'):
            if format_spec:
                raise ValueError('Format specification not allowed'
                                 ' with __markup__ object.')
            s = value.__markup__()
        else:
            s = super(_MarkupEscapeFormatter, self).format_field(
                value, format_spec)
        return unicode(self._escape(s))


class _MarkupEscapeHelper(object):
    """Helper for Markup.__mod__"""

    def __init__(self, obj, escape):
        self._obj = obj
        self._escape = escape

    __getitem__ = lambda s, x: self.__class__(s._obj[x], s._escape)
    __str__ = __unicode__ = lambda s: unicode(s._escape(s._obj))
    __repr__ = lambda s: str(s._escape(repr(s._obj)))
    __int__ = lambda s: int(s._obj)
    __float__ = lambda s: float(s._obj)


class Link(object):
    """URL link in Slack text"""
    def __init__(self, url, title=None):
        self._url = url
        self._title = title

    def __markup__(self):
        if self._title is None:
            return Markup('<{}>').format(self._url)
        return Markup('<{}|{}>').format(self._url, self._title)


class Message(object):
    """Slack WebHook message"""
    def __init__(self, text=None, username=None,
                 channel=None, attachments=None):
        self.text = text
        self.username = username
        self.channel = channel
        self.attachments = attachments

    def document(self):
        doc = {}
        if self.text is not None:
            doc['text'] = Markup.escape(self.text)
        if self.username is not None:
            doc['username'] = self.username
        if self.channel is not None:
            doc['channel'] = self.channel
        if self.attachments is not None:
            doc['attachments'] = [a.document() for a in
                                  self.attachments]
        return doc


class Attachment(object):
    """Slack message attachment"""
    def __init__(self, fallback, color=None, pretext=None,
                 author=None, title=None, title_link=None,
                 text=None, image_url=None):
        self.fallback = fallback
        self.color = color
        self.pretext = pretext
        self.author = author
        self.title = title
        self.title_link = title_link
        self.text = text
        self.image_url = image_url

    def document(self):
        doc = {'fallback': self.fallback}
        if self.color is not None:
            doc['color'] = self.color
        if self.pretext is not None:
            doc['pretext'] = Markup.escape(self.pretext)
        if self.author is not None:
            doc['author_name'] = self.author.name
            if self.author.link is not None:
                doc['author_link'] = self.author.link
            if self.author.icon is not None:
                doc['author_icon'] = self.author.icon
        if self.title is not None:
            doc['title'] = Markup.escape(self.title)
        if self.title_link is not None:
            doc['title_link'] = self.title_link
        if self.text is not None:
            doc['text'] = Markup.escape(self.text)
        if self.image_url is not None:
            doc['image_url'] = self.image_url
        return doc


class Author(object):
    """Slack message attachment author"""
    def __init__(self, name, link=None, icon=None):
        self.name = name
        self.link = link
        self.icon = icon


class SlackWebHook(Thread):
    """Threaded interface to WebHooks API"""

    def __init__(self, endpoint=None, min_post_delay=6.0):
        super(SlackWebHook, self).__init__()
        self._endpoint = endpoint
        self._min_post_delay = min_post_delay
        self._message_queue = Queue()
        self._running = True

    def enqueue(self, message):
        self._message_queue.put(message)

    def stop(self):
        self._running = False
        self._message_queue.put(None)

    def run(self):
        while self._running:
            message = self._message_queue.get()
            if message is None:
                continue

            logger.info('Posting message {}'.format(message.document()))

            # Post to endpoint
            data = json.dumps(message.document())
            req = urllib2.Request(self._endpoint, data,
                                  {'Content-Type': 'application/json'})
            try:
                f = urllib2.urlopen(req)
                response = f.read()
                f.close()
                retry_after = 0
            except urllib2.HTTPError as e:
                if e.code == 429:
                    retry_after = int(e.headers.get('Retry-After', '0'))
                else:
                    raise

            # Wait to avoid flooding
            wait_time = max(retry_after, self._min_post_delay)
            logger.info('Waiting for {} seconds'.format(wait_time))
            time.sleep(wait_time)
