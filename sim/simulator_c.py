#!/usr/bin/python

import message_pb2
from pack import *
from socket import *
from tlslite import TLSConnection
import time
import os
import random
import threading
import httplib2
import json
while True:
    uname = raw_input('uname> ')#hehedayo
    pwd = raw_input('pwd> ')
    ret = json.loads(httplib2.Http().request('http://123.56.142.241/v1/user/login?name='+uname+'&pwd='+pwd)[1])

    if ret['status'] == 0:
        token = ret['user_action']['token']
        uid = str(ret['user_action']['uid'])
    else:
        print ret
        print('ERROR [%d]:%s' % (ret['status'], ret['errmsg']))
        continue
    print('token acquired for [%s]: %s' % (uid, token))
    break

_SID = uid

def setBit(int_type, offset):
    mask = 1 << offset
    return (int_type | mask)

def testBit(int_type, offset):
    mask = 1 << offset
    return (int_type & mask)

sock = socket(AF_INET, SOCK_STREAM)
sock.connect(('messagehive.dhc.house', 1430))

connection = TLSConnection(sock)
connection.handshakeClientCert()

print '***connected***'

## Authentication message
msg = message_pb2.Container()
msg.SID = uid
msg.RID = ''
msg.STIME = 0

os.system('TITLE CLIENT %s' % _SID)

msgType = 0
msgType = setBit(msgType, 0) # Identity
msgType = setBit(msgType, 1) # Authenticate

msg.TYPE = msgType
msg.BODY = '{"token":"%s"}' % token

data = Packet.Pack(msg)

connection.write(data)

## P2P message
def setTimeout(t, func, *args, **kwargs):
    print('called')
    time.sleep(t)
    print('called2')
    func(*args, **kwargs)
last_mid = ''
def loop():
    global last_mid
    buf = ''
    tm = None
    while True:
        _ = connection.read()
        if len(_) == 0:
            time.sleep(random.random())
            continue
        buf += _
        try:
            msg2 = Packet.UnPack(buf) # Must catch error
        except DataNeededError:
            continue
        else:
            buf = ''
        if msg2.SID == "":
            print('***ok')
            continue
        os.system('TITLE CLIENT %s INCOMING FROM [%s]:%s' % (_SID, msg2.SID, (msg2.BODY[:13]+"...") if len(msg2.BODY)>16 else msg2.BODY))
        for k,v in json.loads(msg2.BODY).iteritems():
            print("%s: %s" % (k,v))
        print('=====================================')
        #print('***INCOMING FROM [%s]:%s***' % (msg2.SID, msg2.BODY))
        last_mid = msg2.MID
        
recv_thread = threading.Thread(target = loop)
recv_thread.setDaemon(True)
recv_thread.start()

while True:
    _ = raw_input('CONFIRM?> ') or 'y'
    print(last_mid)
    if _ == 'n':
        break
    msg.SID = _SID
    msg.MID = ''
    msg.RID = "00000001"
    msg.TYPE = 1
    msg.BODY = '{"type":"receipt", "status":"ok", "mid":"'+last_mid+'"}'
    data = Packet.Pack(msg)
    data = connection.write(data) # You must implement your own tcp receiver


connection.close()
