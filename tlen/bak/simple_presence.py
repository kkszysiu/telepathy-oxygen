# telepathy-pinocchio - dummy Telepathy connection manager for instrumentation
#
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
# 02110-1301 USA

import dbus.service

import telepathy as tp

import pinocchio as pin

class SimplePresence(tp.server.ConnectionInterfaceSimplePresence):
    """Presence interface for a Telepathy Connection."""

    def __init__(self):
        tp.server.ConnectionInterfaceSimplePresence.__init__(self)

    def GetPresences(self, contacts):
        """Returns the presence of the given contacts.

        Arguments:
        contacts -- iterable of contacts whose presence is requested
        
        Returns:
        presences -- complex list of structs containing the presences

        Exceptions:
        org.freedesktop.Telepathy.Error.Disconnected
        org.freedesktop.Telepathy.Error.InvalidArgument
        org.freedesktop.Telepathy.Error.InvalidHandle
        org.freedesktop.Telepathy.Error.NetworkError
        org.freedesktop.Telepathy.Error.NotAvailable
        """
        presences = {}
        for handle_id in contacts:
            self.check_handle (tp.constants.HANDLE_TYPE_CONTACT, handle_id)

            handle_obj = self._handles[tp.constants.HANDLE_TYPE_CONTACT,
                                       handle_id]
            presences[handle_id] = handle_obj.get_simple_presence()

        return presences

