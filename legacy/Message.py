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
# WARRANTIES OR CONDITIONS OF ANY KIND, either e._pr()ess or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

# The Message Defination

import os
import binascii
import time
import random
from config import *

class MessageObj(object):

    def __init__(self, priority, payload, tags = []):
        self.init_pr = priority # higher the value, higher the._priority
        self.payload = payload
        self.msgid = os.urandom(16)
        self.birth = time.time()
        self.last_touched = 0
        self.retries = 0
        self.retry_offset = (1 + random.choice((-1, 1)) * random.random() * 0.3) * MSG_RETRY_INTERV
        #[set(1,2,3,5), set(5,6,7,8)]
        self._targets = []
        #[1,2,3,4]
        self._leaked = []
        #set(1,2,3,4) O(1)
        self._tried = set()
        self._tags = tags

    def get_msgid(self):
        '''Get human readable Msg ID'''
        return binascii.hexlify(self.msgid)

    def _pr(self):
        '''A priority algorithm
        If a message has failed before and is in queue for longer then 10min, lift up its PR,
        to avoid bumping effect, we use random range(+- 30%) instead of fixed time range
        The return value is its calculated priority plus init priority
        '''
        calc_pr = 0
        if len(self._leaked)>0 and self.last_touched > 0 and time.time() - self.last_touched > self.retry_offset:#retry message 
            calc_pr += 500
        return self.init_pr + calc_pr

    def get_payload(self):
        self.retries += 1
        self.last_touched = time.time()
        return self.payload

    def get_targets(self):
        _ = [ i for i in self._targets if i not in self._tried] + self._leaked
        for t in set(_):
            self._tried.add(t)
        return _

    def add_target(self, targ):
        self._targets.append(targ) 

    def set_targets(self, list_new):
        '''notice: list random delete is not fast, 
        build a new one instead'''
        self._targets = list(list_new)

    def is_tried(self, guid):
        return guid in self._tried

    def get_leaked(self):
        return self._leaked

    def add_leaked(self, targ):
        self._leaked.append(targ) 

    def set_leaked(self, list_new):
        self._leaked = list(list_new)

    def set_tags(self, tags):
        return self._tags.append(tags)

    def get_tags(self):
        return self._tags

    # Some magic comparasions
    # Higher pr and older message are "bigger"
    # def __hash__(self):
    #     return self.msgid

    def __eq__(self, other):
        if other == None:
            return False
        return self._pr() == other._pr() and self.birth == other.birth

    def __ne__(self, other):
        if other == None:
            return True
        return not self._pr() == other._pr() and self.birth == other.birth

    def __gt__(self, other):
        return other._pr() < self._pr() and other.birth > self.birth

    def __lt__(self, other):
        return self._pr() < other._pr() and self.birth > other.birth

    def __ge__(self, other):
        return not self._pr() < other._pr() and not self.birth > other.birth

    def __le__(self, other):
        return not other._pr() < self._pr() and not other.birth > self.birth
