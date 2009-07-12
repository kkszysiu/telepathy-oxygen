#!/usr/bin/python
#
# telepathy-tlen - Telepathy connection manager for Tlen.pl network.
#
# Copyright (C) 2009 Krzysztof 'kkszysiu' Klinikowski <kkszysiu@gmail.com>
#
# Based on telepathy-pinocchio by:
# Copyright (C) 2008 Nokia Corporation
# Copyright (C) 2008 Collabora Ltd.
#
# This library is free software; you can redistribute it and/or
# modify it under the terms of the GNU Lesser General Public License
# version 2.1 as published by the Free Software Foundation.
#
# This library is distributed in the hope that it will be useful, but
# WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU
# Lesser General Public License for more details.
#
# You should have received a copy of the GNU Lesser General Public
# License along with this library; if not, write to the Free Software
# Foundation, Inc., 51 Franklin St, Fifth Floor, Boston, MA

import gobject
import dbus.mainloop.glib
import dbus

from twisted.internet import glib2reactor
glib2reactor.install()

from twisted.internet import reactor

import telepathy
if telepathy.version < (0, 15, 6):
    print >> sys.stderr, 'Critical: telepathy-python >= 0.15.6 required. Exiting.'
    sys.exit(1)

import tlen

TIMEOUT_MS = 50000

def assert_cm_connections(reactor, manager):
    if len(manager._connections) <= 0:
        reactor.stop()

    # never automatically destroy this timeout
    return True

if __name__ == '__main__':
    dbus.mainloop.glib.DBusGMainLoop(set_as_default=True)

    manager = None

    try:
        manager = tlen.ConnectionManager()
    except dbus.NameExistsException:
        print >> sys.stderr,'telepathy-oxygen is already running; exiting...'
        sys.exit(0)

    try:
        reactor.run()
    except KeyboardInterrupt:
        reactor.stop()