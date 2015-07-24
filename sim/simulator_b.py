#!/usr/bin/python

import message_pb2
from pack import *
from socket import *
from tlslite import TLSConnection
import time
import os
import random
import threading
from config import *

def setBit(int_type, offset):
    mask = 1 << offset
    return (int_type | mask)

def testBit(int_type, offset):
    mask = 1 << offset
    return (int_type & mask)

sock = socket(AF_INET, SOCK_STREAM)
sock.connect((GATEWAY_HOST, GATEWAY_PORT))

connection = TLSConnection(sock)
connection.handshakeClientCert()

print '***connected***'

## Authentication message
msg = message_pb2.Container()
_SID = raw_input('YOUR SID> ')
msg.SID = _SID#'a'
msg.RID = ''
msg.STIME = 0

os.system('TITLE CLIENT %s' % _SID)

msgType = 0
msgType = setBit(msgType, 0) # Identity
msgType = setBit(msgType, 1) # Authenticate

msg.TYPE = msgType
msg.BODY = '{"token":"foo"}'

data = Packet.Pack(msg)

connection.write(data)

## P2P message
def setTimeout(t, func, *args, **kwargs):
    print('called')
    time.sleep(t)
    print('called2')
    func(*args, **kwargs)

def loop():
    buf = ''
    tm = None
    while True:
        buf += connection.read()
        try:
            msg2 = Packet.UnPack(buf) # Must catch error
        except DataNeededError:
            time.sleep(random.random())
            continue
        else:
            buf = ''
        if msg2.SID == "":
            print('***confirmed')
            continue
        os.system('TITLE CLIENT %s INCOMING FROM [%s]:%s' % (_SID, msg2.SID, msg2.BODY))
        print('***INCOMING FROM [%s]:%s***' % (msg2.SID, msg2.BODY))
        
recv_thread = threading.Thread(target = loop)
recv_thread.setDaemon(True)
recv_thread.start()

while True:
    _ = raw_input('RID> ')
    if not _:
        break
    msg.RID = _
    msg.TYPE = 0
    _ = raw_input('MSG> ')
    if not _:
        break
    if _.startswith('group'):
        _1, action, data = _.split()
        msg.TYPE = setBit(msgType, 5)
        msg.BODY = '{"action":"%s", "data":"%s"}' % (action, data)
        print(msg.BODY)
    else:
        msg.BODY = _

    data = Packet.Pack(msg)

    data = connection.write(data) # You must implement your own tcp receiver


connection.close()
