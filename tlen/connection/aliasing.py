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

import tlen

class Aliasing(tp.server.ConnectionInterfaceAliasing):
    """Aliasing interface for a Telepathy connection."""

    def __init__(self):
        tp.server.ConnectionInterfaceAliasing.__init__(self)

    def GetAliasFlags(self):
        """Returns flag values specifying the behavior of aliases on this
        connection.

        Returns:
        flags -- bitwise OR of Connection_Alias_Flags values specifying the
                 behavior of aliases on this connection

        Exceptions:
        org.freedesktop.Telepathy.Error.Disconnected
        """
        flags = 0
        flags |= tp.constants.CONNECTION_ALIAS_FLAG_USER_SET

        return flags

    def RequestAliases(self, contacts):
        """Request the aliases of any number of contacts.

        Arguments:
        contacts -- iterable of contacts whose aliases are requested

        Returns:
        aliases -- list of requested aliases in the same order
        
        Exceptions:
        org.freedesktop.Telepathy.Error.Disconnected
        org.freedesktop.Telepathy.Error.NetworkError
        org.freedesktop.Telepathy.Error.InvalidHandle
        org.freedesktop.Telepathy.Error.NotAvailable
        """
        aliases = []
        alias_pairs = []
        for handle_id in contacts:
            self.check_handle (tp.constants.HANDLE_TYPE_CONTACT, handle_id)

            handle_obj = self._handles[tp.constants.HANDLE_TYPE_CONTACT,
                                       handle_id]

            aliases.append(handle_obj.get_alias())
            alias_pairs.append((handle_id, aliases[-1]))

        return aliases

    def SetAliases(self, alias_map):
        """Request the aliases of any number of contacts.

        Arguments:
        alias_map -- dictionary mapping contact handles to new aliases

        Exceptions:
        org.freedesktop.Telepathy.Error.Disconnected
        org.freedesktop.Telepathy.Error.NetworkError
        org.freedesktop.Telepathy.Error.NotAvailable
        org.freedesktop.Telepathy.Error.InvalidArgument
        org.freedesktop.Telepathy.Error.PermissionDenied
        """
        alias_pairs = []
        for handle_id in alias_map.keys():
            self.check_handle (tp.constants.HANDLE_TYPE_CONTACT, handle_id)

            for handle_obj in self._handles.values():
                if handle_obj.get_id() == handle_id:
                    handle_obj.set_alias(alias_map[handle_id])

                    alias_pairs.append((handle_obj.get_id(),
                                       alias_map[handle_id]))
        if len(alias_pairs) >= 1:
            self.AliasesChanged(alias_pairs)
            self.save()
