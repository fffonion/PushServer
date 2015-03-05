#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
# Copyright 2015 fffonion
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# The Message Queue Handling Module

from __future__ import print_function
from threading import Thread, RLock
from Queue import Queue, Empty
import random
import time
from config import *
from Message import MessageObj
from DataMgr import DataMgr
import Logger

logger = Logger.Logging('logging')


class QueueHandler(Thread):

    def __init__(self, msg_queue):
        self.msg_queue = msg_queue
        self.last_idx = None
        self.alive = True
        self._pause_lock = RLock()
        self._send_func = self._send_func
        Thread.__init__(self)
        self.daemon = True
        self.start()

    def sort(self):
        pass

    def put_msg(self, msg):
        self.msg_queue.msg_queue_put(msg)

    def shutdown(self):
        self.alive = False
        #put None to notify running thread
        self.msg_queue.put(None, False)
        self.join()

    def pause(self):
        self._pause_lock.acquire()

    def resume(self):
        self._pause_lock.release()

    @property
    def qsize(self):
        return self.msg_queue.qsize()

    def _send_func(self, bundle):
        result = 1 if random.random() > 0.7 else 0
        logger.debug('[QH] SENT %s to %s %s' % (bundle.msg.msgid_h, str(bundle.user.guid), 'FAILED' if result else ''))
        bundle.callback(result)


    def run(self):
        while self.alive:
            try:
                _ = self.msg_queue.get()
            except Empty:
                time.sleep(MSG_CHECK_INTERV)
                continue
            if not _ and not self.alive:#force break
                logger.debug('[QH] got exit flag')
                return
            self._pause_lock.acquire()
            self._send_func(_)
            self._pause_lock.release()
            #TODO sleep longer
            time.sleep(random.random())


