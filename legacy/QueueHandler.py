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
from Queue import Queue, Empty
from Message import MessageObj
from DataMgr import DataMgr
import Logger

logger = Logger.Logging('logging')


class QueueHandler(object):

    def __init__(self, data_mgr_instance):
        self._msg_queue = []
        self.dm_obj = data_mgr_instance
        self.last_idx = None


    def sort(self):
        pass

    def put_msg(self, msg):
        self.dm_obj.msg_queue_put(msg)

    def get_next(self):
        idx, msg = self.dm_obj.msg_queue_pop_next(sort_func = lambda x:x._pr())
        if idx == None:
            logger.warning('queue is empty')
        else:
            self.last_idx = idx
            #logger.debug('NEXT idx = %d' % idx)
            return msg
        return None

    def mod_last(self, msg):
        self.dm_obj.msg_queue_set(self.last_idx, msg)

    def set_dm(self, dm):
        if not isinstance(dm, DataMgr):
            raise ValueError(" dm argument is not a DataMgr")
        self.dm_obj = dm

if __name__ == '__main__':
    from DataMgr import DataMgr
    dm = DataMgr()
    qh = QueueHandler(dm)
    ms = MessageObj(1, "a test msg with PR 1")
    qh.put_msg(ms)
    ms = MessageObj(2, "a test msg with PR 2")
    qh.put_msg(ms)
    _ = qh.get_next()
    logger.debug('payload is: "%s"' % _)
    _ = qh.get_next()
    logger.debug('payload is: "%s"' % _)
    logger.debug('msg queue size %d' % dm.msg_queue_size())
