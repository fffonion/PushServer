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
 
import atexit
import gevent
from gevent.queue import Queue, Empty

import Logger
from config import *
from User import UserObj
from DataMgr import DataMgr
from Message import MessageObj
from GatewayMgr import GatewayMgr
from QueueHandler import QueueHandler

logger = Logger.Logging('logging')

class PushServer(object):
    def __init__(self, logger):
        self.has_shutdown = False
        self.logger = logger
        self.dm = DataMgr()
        self.gm = GatewayMgr(logger, self.dm.user_online)
        self.qh = QueueHandler(self.dm.msg_queue, self.gm.send_push)
        atexit.register(self.shutdown)
        logger.info('Server started.')

    def main_loop(self):
        import random
        import string
        import time
        u = UserObj('ua', 'a')
        self.dm.users_add(u)
        while True:
            m = MessageObj(''.join([random.choice(string.letters) for i in range(10)]))
            self.dm.msg_add(m)
            gevent.sleep(MSG_CHECK_INTERV)
            self.dm.make_bundle()
            self.logger.debug('pending:%d' % self.qh.qsize)
            while self.qh.qsize > 0:
                gevent.sleep(1)
            self.logger.debug('remaining msg queue size:%d' % self.qh.qsize)
            gevent.sleep(10)

    def online_loop(self):
        while True:
            u = self.dm.pending_online_queue.get()
            self.dm.make_bundle(u)
    
    def run(self):
        print('run')
        self.greenlets = [
            gevent.spawn(self.main_loop),
            gevent.spawn(self.online_loop),
        ]

    def shutdown(self):
        if not self.has_shutdown:
            gevent.killall(self.greenlets)
            try:
                self.gm.shutdown()
            except KeyboardInterrupt:
                pass
            self.dm.shutdown()
            self.has_shutdown = True
            logger.info('Server exit nicely.')


def main():
    try:
        logger.info('Initializing...')
        ps = PushServer(logger)
        ps.run()
    except KeyboardInterrupt:
        return


if __name__ == '__main__':
    main()