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
import gevent
from gevent import Greenlet
from gevent.lock import RLock
from gevent.queue import Queue, Empty
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
from db_helper import mongo

from config import *


class DataMgr(Greenlet):
    pickle_names = ['_msgs', '_users', 'send_queue', 'pending_online_users']
    data_version = 1000

    def __init__(self, logger):
        Greenlet.__init__(self)
        self.logger = logger
        self._users_lock = RLock()
        self._msgs = {}
        self._users = {}
        self.send_queue = Queue()
        self.pending_online_users = Queue()
        self.bootstrap()
        self._dying = False
        self.start()

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
        self.logger.debug('[DM] saving data to disk...')
        self._save_cache()

    def reset(self):
        '''reset in-memory data and disk data'''
        self.send_queue = Queue()
        self.pending_online_users = Queue()
        _ = opath.join(DATA_DIR, DM_PKL_NAME)
        if opath.exists(_):
            os.remove(_)

    def _save_cache(self):
        # fixme: save to external database not implemented
        _ = {'_version':DataMgr.data_version}
        for k in DataMgr.pickle_names:
            if k in self.__dict__:
                _[k] = self.__dict__[k]
        #pickle.dump(_, file(opath.join(DATA_DIR, DM_PKL_NAME), 'wb'), pickle.HIGHEST_PROTOCOL)

    def msg_add(self, _):
        if not isinstance(_, MessageObj):
            raise ValueError(" argument is not a MessageObj")
        self._msgs[_.msgid] = _

    def msg_get(self, msgid):
        if msgid not in self._msgs:
            raise IndexError(" msgid %d not in queue" % idx)
        return self._msgs[msgid]

    def msg_del(self, msgid):
        del self._msgs[msgid]

    def msg_set(self, msgid, msg):
        self._msgs[msgid] = msg

    @property
    def msg_count(self):
        return len(self._msgs)


    # def bundle_queue_pop_next(self, sort_func=None):
    #     self._bundle_queue_lock.acquire()
    #     msgid = None
    #     msg = None
    #     if len(self.bundle_queue) > 0:
    #         kwargs = {}
    #         if sort_func:
    #             kwargs['key'] = lambda x: sort_func(self.bundle_queue[x])
    #         else:
    #             kwargs['key'] = lambda x: self.bundle_queue[x]
    #         l = sorted(self.bundle_queue, **kwargs)
    #         for msgid in l:
    #             msg = self.bundle_queue[msgid]
    #             if msg._pr() >= 500:#retry high prioity
    #                 break
    #             #get targets every time poped
    #             _ = [u for t in msg.get_tags() if t in self.tags2user for u in self.tags2user[t] if not msg.is_tried(u)]
    #             if not _:
    #                 msgid = None
    #                 msg = None
    #                 continue
    #             msg.set_targets(_)
    #             break
    #             #del self.bundle_queue[msgid]
    #         self._bundle_queue_lock.release()
    #         return (msgid, msg)
    
    def set_user_online(self, guid):
        #TODO get userid from rid
        uid = "u" + guid
        u = UserObj(uid, guid)
        self.users_add(u)
        self.pending_online_users.put(guid)

    def set_user_offline(self, guid):
        #TODO get userid from rid
        self.users_del(guid)

    def users_add(self, _):
        if not isinstance(_, UserObj):
            raise ValueError(" argument is not a UserObj")
        self._users_lock.acquire()
        self._users[_.guid] = _
        self._users_lock.release()

    def users_get(self, uuid):
        if uuid not in self._users:
            raise IndexError(" uuid %d not in users list" % str(uuid))
        return self._users[uuid]

    def users_del(self, uuid):
        if '-' in uuid:  # convert to bytes
            uuid = binascii.unhexlify(uuid)
        if uuid not in self._users:
            raise IndexError(" uuid %d not in users list" % str(uuid))
        self._users_lock.acquire()
        del self._users[uuid]
        self._users_lock.release()

    @property
    def users_count(self):
        return len(self._users)

    def make_bundle(self, send_func, user_keys = None):
        user_keys = user_keys or self._users.keys()
        self.logger.debug('[DM] begin mapping of %du * %dm' % (len(user_keys), self.msg_count))
        cnt = 0
        user_keys = sorted(user_keys, key = lambda x:self._users[x].pr, reverse = True)
        for k in user_keys:
            u = self._users[k]
            for _k, m in self._msgs.iteritems():
                _ = u.gen_bundle(m)
                if _:
                    cnt += 1
                    send_func(_)
        if cnt:
            self.logger.debug('[DM] queued %d new bundles' % cnt)
        return cnt


    def run(self):
        self.mongo_instance = mongo()
        while not self._dying:
            msgids = self.mongo_instance.event_get_id(0)
            for i in msgids:
                m = MessageObj(
                    payload_callback = lambda:self.mongo_instance.event_get_single_info(i),
                    msgid = i
                )
                self.msg_add(m)
            gevent.sleep(60)
            self._save_cache()
