#!/usr/bin/python

import message_pb2
from pack import *
from socket import *
from tlslite import TLSConnection

def setBit(int_type, offset):
    mask = 1 << offset
    return (int_type | mask)

def testBit(int_type, offset):
    mask = 1 << offset
    return (int_type & mask)

sock = socket(AF_INET, SOCK_STREAM)
sock.connect(('server01.dhc.house', 1430))

connection = TLSConnection(sock)
connection.handshakeClientCert()

## Authentication message
msg = message_pb2.Container()
msg.SID = 'b'
msg.RID = ''
msg.STIME = 0

msgType = 0
msgType = setBit(msgType, 0) # Identity
msgType = setBit(msgType, 1) # Authenticate

msg.TYPE = msgType
msg.BODY = '{"token":"foo"}'

data = Packet.Pack(msg)

connection.write(data)

## P2P message
msg.RID = 'a'
msg.TYPE = 0
msg.BODY = 'x'

data = Packet.Pack(msg)

data = connection.read() # You must implement your own tcp receiver

msg = Packet.UnPack(data) # Must catch error

print msg

raw_input('Press enter to exit')

connection.close()
