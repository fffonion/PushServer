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
# License for the specific language governing permissions and limitations`
# under the License.

# The Connection manager module

import os
import binascii
import time
import gevent
import gevent.ssl
from gevent import Greenlet
from gevent import socket
from gevent.queue import Queue, Empty
from gevent.lock import RLock
import struct
import traceback
try:
    import ujson as json
except ImportError:
    import json
from config import *
from cross_platform import *
import gw_message_pb2

MSG_SERVER = 0x0
MSG_CLIENT = 0x1
MSG_AUTH = 0x2
MSG_HEARTBEAT = 0x4
MSG_RECEIPT = 0x8
MSG_NOT_TRANSIENT = 0x10
MSG_GROUP = 0x20
MSG_EVENT = 0x40
MSG_ERROR = 0x80000000

MAX_PACKET_LENGTH = 1 << 20

class Error(Exception):
    pass

class DataNeededError(Error):
    def __init__(self, value):
        self.value = value

class MaxLengthError(Error):
    def __init__(self, value):
        self.value = value

class Packet(object):

    @staticmethod
    def Pack(message):
        raw = message.SerializeToString()
        length = len(raw)
        data = struct.pack('>I', length)
        data += raw
        return data

    @staticmethod
    def UnPack(data):
        if len(data) < 4:
            raise DataNeededError('At least 4 octets')

        length = struct.unpack('>I', data[:4])[0]

        if length > MAX_PACKET_LENGTH :
            raise MaxLengthError('')

        if len(data) < (4 + length):
            raise DataNeededError('Need more data')

        data = data[4:4 + length]
        msg = gw_message_pb2.Container()
        msg.ParseFromString(data)

        return msg

class GatewayMgr(object):
    PUSH_SERVER_SID = '00000001'

    def __init__(self, logger, online_callback):
        self.logger = logger
        self.online_callback = online_callback
        self._gw_fd_raw = None
        self.gw_fd = None
        self.callback_tbl = {}
        self._send_queue = Queue()
        self.connect()
        self.greenlets = [
            gevent.spawn(self._send),
            gevent.spawn(self._recv),
        ]
        self.auth()

    def auth(self):
        self._queued_send('', MSG_CLIENT | MSG_AUTH, '{"token":"foo"}', callback = lambda *__:None)

    def connect(self):
        self._gw_fd_raw = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._gw_fd_raw.connect((GATEWAY_HOST, GATEWAY_PORT))
        self.gw_fd = gevent.ssl.SSLSocket(self._gw_fd_raw)

    def send_push(self, bundle):
        if not self.gw_fd or not self._gw_fd_raw:
            self.connect()
        self._queued_send(bundle.user.guid, MSG_CLIENT | MSG_RECEIPT, bundle.msg.payload, bundle.callback)

    def _queued_send(self, rid, msgtype, body, callback = None):
        mid = 'PSH' + binascii.hexlify(os.urandom(9))
        msg = gw_message_pb2.Container()
        msg.SID = GatewayMgr.PUSH_SERVER_SID
        msg.RID = rid
        msg.MID = mid
        msg.STIME = 0
        msg.TYPE = msgtype
        msg.BODY = body#'{"token":"foo"}'

        data = Packet.Pack(msg)

        self._send_queue.put(data)
        if callback:
            self.callback_tbl[mid] = callback

    #TODO reconnnect
    def _send(self):
        while True:
            b = self._send_queue.get()
            self.gw_fd.write(b)

    def _recv(self):
        buf = ''
        while True:
            try:
                #print('wait for read')
                socket.wait_read(self.gw_fd.fileno())
            except socket.error:
                break
            #print('read')
            buf += self.gw_fd.read()
            if len(buf) == 0:
                continue
            try:
                msg = Packet.UnPack(buf) # Must catch error
            except DataNeededError:
                continue
            else:
                buf = ''
            self._resp_handler(msg)
            

    def _resp_handler(self, msg):
        self.logger.debug("MID=%s" % msg.MID)
        print(msg)
        if msg.BODY:
            msg_body = json.loads(msg.BODY)
        else:
            msg_body = {}
        if msg.TYPE & MSG_CLIENT:
            self.logger.debug('***INCOMING FROM [%s]:%s***' % (msg.SID, msg.BODY))
        else:#server
            if msg.TYPE & MSG_EVENT:
                if msg_body['type'] == 'online':
                    self.logger.debug('user %s is now online' % msg.SID)
                    self.online_callback(msg.SID)
            else:
                self.logger.debug('***confirmed')
                mid = msg.MID
                if mid in self.callback_tbl:
                    _func = self.callback_tbl.pop(mid)
                    try:
                        _func(msg)
                    except KeyboardInterrupt:
                        return
                    except Exception as ex:
                        self.logger.error('Got "%s" in callback' % ex)
                        traceback.print_exc()


    @staticmethod
    def set_bit(int_type, offset):
        mask = 1 << offset
        return (int_type | mask)

    @staticmethod
    def test_bit(int_type, offset):
        mask = 1 << offset
        return (int_type & mask)

    def shutdown(self):
        gevent.joinall(self.greenlets)


if __name__ == '__main__':
    import Logger
    logger = Logger.Logging('logging')
    logger.level = Logger.Logging.WARNING
    gm = GatewayMgr(logger, online_callback = lambda *_:None)
    def sendme():
        while True:
            print('sent')
            gm.send_push('a', 'PUSH MSG ->%s @%s' % ('a', time.strftime('%X', time.localtime(time.time()))))
            gevent.sleep(2)
            
    print('wait for connection')
    #gevent.spawn(sendme)
    gevent.joinall(gm.greenlets)
