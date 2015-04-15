#!/usr/bin/pythn

import message_pb2
from struct import *

MAX_PACKET_LENGTH = 1 << 20

class Error(Exception):
    pass

class DataNeededError(Error):
    def __init__(self, value):
        self.value = value

class MaxLengthError(Error):
    def __init__(self, value):
        self.value = value

class Packet:

    @staticmethod
    def Pack(message):
        raw = message.SerializeToString()
        length = len(raw)
        data = pack('>I', length)
        data += raw
        return data

    @staticmethod
    def UnPack(data):
        if len(data) < 4:
            raise DataNeededError('At least 4 octets')

        length = unpack('>I', data[:4])[0]

        if length > MAX_PACKET_LENGTH :
            raise MaxLengthError('')

        if len(data) < (4 + length):
            raise DataNeededError('Need more data')

        data = data[4:4 + length]
        msg = message_pb2.Container()
        msg.ParseFromString(data)
        
        return msg
        
if __name__ == "__main__":
    
    try:
        msg = message_pb2.Container()
        msg.MID = ""
        msg.SID = "a"
        msg.RID = "b"
        msg.STIME = 11111111
        msg.TYPE = 0
        msg.BODY = "foo"

        data = Packet.Pack(msg)

        msg = Packet.UnPack(data)

        print "All test passed"
    except:
        raise
