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

# TestSuite

import traceback

from QueueHandler import QueueHandler
from Message import MessageObj
from DataMgr import DataMgr
from User import UserObj
from config import *
import Logger
import atexit

logger = Logger.Logging('logging')


def test_suite1():
    logger.info('***START OF TEST***')
    try:
        import random
        import time
        dm = DataMgr()
        atexit.register(dm.shutdown)
        qh = QueueHandler(dm)
        dm.reset()
        logger.info('***TESTING DataMgr add, pop ***')
        for i in range(100):
            _pr = random.randrange(1, 100)
            ms = MessageObj(_pr, "a test msg with PR %d, idx %d" % (_pr, i))
            qh.put_msg(ms)
        logger.debug('[test]msg queue size %d' % dm.msg_queue_size())
        assert(dm.msg_queue_size() == 100)
        _tmp = []
        #get 50
        for i in range(50):
            _m = qh.get_next()
            logger.debug('[test]payload is: "%s"' % _m.get_payload())
            #assume failing starts after 30 msg sent
            if i > 30:
                _tmp.append(_m)
            #time.sleep(random.random() / 4) #0 ~ 0.25s
        logger.debug('[test]msg queue size %d' % dm.msg_queue_size())
        assert(dm.msg_queue_size() == 50)

        #assume it's failed
        _msg1 = random.choice(_tmp)
        _msg1.set_leaked([233])
        logger.debug('[test]assume has failure this msgid: %s' % _msg1.get_msgid())
        logger.debug('[test]payload is: "%s"' % _msg1.get_payload())
        #put it back
        #qh.put_msg(_msg1)

        #put another 100
        for i in range(100):
            _pr = random.randrange(1, 100)
            ms = MessageObj(_pr, "a test msg with PR %d, idx %d" % (_pr, i))
            qh.put_msg(ms)
        assert(dm.msg_queue_size() == 151)
        logger.debug('[test]msg queue size %d' % dm.msg_queue_size())
        #sleep interval 1
        logger.info('***TESTING QueueHandler retry feature***')
        logger.debug('take a sleep...')
        time.sleep(MSG_RETRY_INTERV * 1.3)
        #now we should get the same object as before
        _msg2 = qh.get_next()
        
        logger.debug('[test]payload is: "%s"' % _msg2.get_payload())
        logger.debug('[test]msgid is: %s %s= before' % (_msg2.get_msgid(), '=' if _msg1.get_msgid() == _msg2.get_msgid() else '!'))
        assert(hash(_msg1) == hash(_msg2))

        logger.info('***TESTING DataMgr.shutdown() and bootstrap()***')
        dm.shutdown()

        dm2 = DataMgr()
        qh.set_dm(dm2)
        logger.debug('[test]restored msg queue size %d' % dm2.msg_queue_size())
        assert(dm2.msg_queue_size() == 150)

        logger.info('***TESTING DataMgr.reset()***')
        dm2.reset()
        logger.debug('[test]msg queue size %d' % dm2.msg_queue_size())
        assert(dm2.msg_queue_size() == 0)
        _ = qh.get_next()
        assert(_ == None)
    except:
        logger.error('***TEST FAILED***\n%s' % traceback.format_exc())
    logger.info('***END OF TEST1***\n')

def test_suite2():
    logger.info('***START OF TEST2***')
    try:
        import random
        import time
        dm = DataMgr()
        dm.reset()
        atexit.register(dm.shutdown)
        qh = QueueHandler(dm)
        dm.reset()
        logger.info('***TESTING DataMgr add, pop ***')
        TEST_CNT = 10
        for i in range(TEST_CNT):
            __tag = random.choice((0, 1))
            usr = UserObj(i)
            usr.set_tags(__tag)
            dm.users_add(usr)
        logger.debug('[test]users size %d' % dm.users_size())
        #assert(dm.users_size() == 10)
        for i in range(TEST_CNT):
            __tag = random.choice((0, 1))
            _pr = random.randrange(1, 100)
            ms = MessageObj(_pr, "a test msg with PR %d, idx %d, tags [%s]" % (_pr, i, str(__tag)), tags = [__tag])
            qh.put_msg(ms)
        _t = dm.tags2msg
        _u = dm.tags2user
        _msg = qh.get_next()
        logger.info('***TESTING tags2msg remove feature***')
        dm.msg_queue_del(_msg.msgid)
        for t in _msg.get_tags():
            assert(_msg.msgid not in _t[t])
        _msg = qh.get_next()
        logger.debug('[test]msg id is %s' % _msg.get_msgid())
        logger.info('***TESTING selecting feature***') 
        logger.debug('[test]msg tags are [%s]' % (','.join(map(str, _msg.get_tags()))))
        all_targets = _msg.get_targets()
        #logger.debug('[test]targets are %s' % str(_))
        _list = []
        for t in _msg.get_tags():
            _list += _u[t]
        assert(set(_list) == set(all_targets))
        _failed = []
        #touch it 
        last_time = time.time()
        logger.debug('[test]payload %s' % _msg.get_payload())
        for t in all_targets:
            if random.random() > 0.8:
                _failed.append(t)
                logger.warning('PUSH FAILED at %s' % t)
            else:
                logger.info('PUSH TO %s' % t)
        _msg.set_leaked(_failed)
        qh.mod_last(_msg)

        #send out all
        cnt = 0
        while True:
            _m = qh.get_next()
            if not _m:
                break
            _m.get_payload()
            _m.get_targets()
            #_m.set_leaked([])
            cnt += 1
        assert(TEST_CNT-2 == cnt)

        if _failed:
            targ_userid= []
            # for i in range(TEST_CNT):
            #     __tag = 1
            #     usr = UserObj(i)
            #     if __tag in _msg.get_tags():
            #         targ_userid.append(str(usr.guid))
            #     usr.set_tags(__tag)
            #     dm.users_add(usr)
            slp_time = MSG_RETRY_INTERV * 1.3 - (time.time() - last_time)
            if slp_time >0:
                logger.debug('sleep %.2f' % slp_time)
                time.sleep(slp_time)
            logger.info('***TESTING retry***') 
            _m = qh.get_next()
            logger.debug('[test]msg id is %s' % _m.get_msgid())
            _targ = _m.get_targets()
            # print(_m._leaked)
            # print(set(_failed), set(targ_userid), set(_targ))
            # print(set(_failed) | set(targ_userid))
            assert(set(_failed) | set(targ_userid) == set(_targ))
            logger.debug('[test]retry on %s' % str(_targ))
        _m = qh.get_next()
        logger.info('***TESTING new user***')
        new_usrid= []
        for i in range(TEST_CNT):
            __tag = 1
            usr = UserObj(i)
            new_usrid.append(str(usr.guid))
            usr.set_tags(__tag)
            dm.users_add(usr)
        _m = qh.get_next()
        logger.debug('[test]msg id is %s' % _m.get_msgid())
        logger.debug('[test]msg tags are [%s]' % (','.join(map(str, _m.get_tags()))))
        _targ = _m.get_targets()
        assert(set(_targ).issubset(set(new_usrid)))
        
    except:
        logger.error('***TEST FAILED***\n%s' % traceback.format_exc())
    logger.info('***END OF TEST2***\n')


if __name__ == '__main__':
    #TODO: fix tags for test 1
    #test_suite1()
    test_suite2()
