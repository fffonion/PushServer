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

import os
import os.path as opath
from threading import RLock, Thread
try:
    import ujsoqn as json
except ImportError:
    import json
import pickle
import atexit
import time
import Logger
from Message import MessageObj
from User import UserObj
from config import *
logger = Logger.Logging('logging')


class DataMgr(Thread):
    pickle_names = ['msg_queue', 'users']
    data_version = 1000

    def __init__(self):
        self._msg_queue_lock = RLock()
        self._users_lock = RLock()
        self.msg_queue = {}
        self.bootstrap()
        self._dying = False
        Thread.__init__(self)
        self.daemon = True
        self.start()
        self.users = {}
        self.tags2user = {}
        self.tags2msg = {}

    def bootstrap(self):
        '''Restore data from disk'''
        _ = opath.join(DATA_DIR, DM_PKL_NAME)
        if opath.exists(_):
            _ = pickle.load(file(_, 'rb'))
            if '_version' not in _ or _['_version'] != DataMgr.data_version:
                raise Exception(" pkl file mismatch:program(%d) file(%d)" % (DataMgr.data_version, None if '_version' not in _ else _['_version']))
            self.__dict__.update(_)

    def shutdown(self):
        '''Save data to disk'''
        self._dying = True
        logger.debug('saving data to disk...')
        self._save_cache()

    def reset(self):
        '''reset in-memory data and disk data'''
        self._msg_queue_lock.acquire()
        self.msg_queue = {}
        _ = opath.join(DATA_DIR, DM_PKL_NAME)
        if opath.exists(_):
            os.remove(_)
        self._msg_queue_lock.release()

    def _save_cache(self):
        # fixme: save to external database not implemented
        _ = {'_version':DataMgr.data_version}
        for k in DataMgr.pickle_names:
            if k in self.__dict__:
                _[k] = self.__dict__[k]
        pickle.dump(_, file(opath.join(DATA_DIR, DM_PKL_NAME), 'wb'), pickle.HIGHEST_PROTOCOL)

    def msg_queue_put(self, _):
        if not isinstance(_, MessageObj):
            raise ValueError(" argument is not a MessageObj")
        self._msg_queue_lock.acquire()
        msgid = _.msgid
        self.msg_queue[msgid] = _
        for e in _.get_tags():
            self.add_tag2msg(e, msgid)
        self._msg_queue_lock.release()

    def msg_queue_get(self, msgid):
        if msgid not in self.msg_queue:
            raise IndexError(" msgid %d not in queue" % idx)
        return self.msg_queue[msgid]


    def msg_queue_del(self, msgid):
        self._msg_queue_lock.acquire()
        for e in self.msg_queue[msgid].get_tags():
            self.tags2msg[e].remove(msgid)
        del self.msg_queue[msgid]
        self._msg_queue_lock.release()

    def msg_queue_set(self, msgid, msg):
        self._msg_queue_lock.acquire()
        self.msg_queue[msgid] = msg
        self._msg_queue_lock.release()

    def msg_queue_pop_next(self, sort_func=None):
        self._msg_queue_lock.acquire()
        msgid = None
        msg = None
        if len(self.msg_queue) > 0:
            kwargs = {}
            if sort_func:
                kwargs['key'] = lambda x: sort_func(self.msg_queue[x])
            else:
                kwargs['key'] = lambda x: self.msg_queue[x]
            l = sorted(self.msg_queue, **kwargs)
            for msgid in l:
                msg = self.msg_queue[msgid]
                if msg._pr() >= 500:#retry high prioity
                    break
                #get targets every time poped
                _ = [u for t in msg.get_tags() if t in self.tags2user for u in self.tags2user[t] if not msg.is_tried(u)]
                if not _:
                    msgid = None
                    msg = None
                    continue
                msg.set_targets(_)
                break
                #del self.msg_queue[msgid]
            self._msg_queue_lock.release()
            return (msgid, msg)
        

    def msg_queue_size(self):
        return len(self.msg_queue)

    def users_add(self, _):
        if not isinstance(_, UserObj):
            raise ValueError(" argument is not a UserObj")
        self._users_lock.acquire()
        guid = str(_.guid)
        for e in _.get_tags():
            self.add_tag2user(e, guid)
        #TODO add to tags already registered msg
        self.users[_.guid.bytes] = _
        self._users_lock.release()

    def users_get(self, uuid):
        if '-' in uuid:  # convert to bytes
            uuid = binascii.unhexlify(uuid)
        if uuid not in self.users:
            raise IndexError(" uuid %d not in users list" % str(uuid))
        return self.users[uuid]

    def users_del(self, uuid):
        if '-' in uuid:  # convert to bytes
            uuid = binascii.unhexlify(uuid)
        if uuid not in self.users:
            raise IndexError(" uuid %d not in users list" % str(uuid))
        self._users_lock.acquire()
        #TODO: CLEAN self.tags2user when delete
        del self.users[uuid]
        self._users_lock.release()

    def users_size(self):
        return len(self.users)

    def add_tag2user(self, tag_name, guid):
        if tag_name not in self.tags2user:
            self.tags2user[tag_name] = set()
        self.tags2user[tag_name].add(guid)

    def add_tag2msg(self, tag_name, msgid):
        if tag_name not in self.tags2msg:
            self.tags2msg[tag_name] = set()
        self.tags2msg[tag_name].add(msgid)


    def run(self):
        while not self._dying:
            time.sleep(60)
            self._save_cache()
