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

# The user module

import uuid


class UserObj(object):

    def __init__(self, uid):
        self.uid = uid
        self.guid = uuid.uuid4()
        self._for_test_era = []
        self.heard_before = 0#the newest message user has been send
        self.leaked_msg = []#msgid of failed message, prior to heard_before

    def get_tags(self):
        return self._for_test_era

    def is_insterested(self, era, func=None):
        pass

    def set_tags(self, era, score=1):
        self._for_test_era.append(era)

