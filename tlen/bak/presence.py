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

class Presence(tp.server.ConnectionInterfacePresence):
    """Presence interface for a Telepathy Connection."""

    def __init__(self):
        tp.server.ConnectionInterfacePresence.__init__(self)

    def GetPresence(self, contacts):
        """Returns the presence of the given contacts.

        Arguments:
        contacts -- iterable of contacts whose presence is requested
        
        Returns:
        presences -- complex list of structs containing the presences

        Exceptions:
        org.freedesktop.Telepathy.Error.Disconnected
        org.freedesktop.Telepathy.Error.InvalidArgument
        org.freedesktop.Telepathy.Error.InvalidHandle
        org.freedesktop.Telepathy.Error.NotAvailable
        """
        presences = {}
        for handle_id in contacts:
            self.check_handle (tp.constants.HANDLE_TYPE_CONTACT, handle_id)

            handle_obj = self._handles[tp.constants.HANDLE_TYPE_CONTACT,
                                       handle_id]

            parameters = {'message': handle_obj.get_status_message()}
            statuses = {handle_obj.get_status(): parameters}
            # timestamp is deprecated, so we won't bother setting it
            activity_statuses = (0, statuses)

            presences[handle_id] = activity_statuses

        return presences

    def GetStatuses(self):
        """Returns a mapping of the valid presence statuses for this connection.

        Returns:
        valid_statuses -- dictionary of presence statuses to status specs

        Exceptions:
        org.freedesktop.Telepathy.Error.Disconnected
        org.freedesktop.Telepathy.Error.NetworkError
        """
        parameter_types = {'message' : 's'}

        valid_statuses = \
        {
            # the following statuses may set a status message
            'available' :
                (tp.CONNECTION_PRESENCE_TYPE_AVAILABLE, True, True,
                 parameter_types),
            'away' :
                (tp.CONNECTION_PRESENCE_TYPE_AWAY, True, True,
                 parameter_types),
            'brb' :
                (tp.CONNECTION_PRESENCE_TYPE_AWAY, True, True,
                 parameter_types),
            'busy' :
                (tp.CONNECTION_PRESENCE_TYPE_AWAY, True, True,
                 parameter_types),
            'dnd' :
                (tp.CONNECTION_PRESENCE_TYPE_AWAY, True, True,
                 parameter_types),
            'xa' :
                (tp.CONNECTION_PRESENCE_TYPE_EXTENDED_AWAY, True, True,
                 parameter_types),

            # 'offline' and 'hidden' statuses may not set a status message
            'offline' :
                (tp.CONNECTION_PRESENCE_TYPE_OFFLINE, True, True, {}),
            'hidden' :
                (tp.CONNECTION_PRESENCE_TYPE_HIDDEN, True, True, {}),
        }

        return valid_statuses

    def RequestPresence(self, contacts):
        """Triggers a PresenceUpdate signal (which contains the presences of the
        contacts for this connection).

        Arguments:
        contacts -- iterable of contacts whose presence is requested
        
        Exceptions:
        org.freedesktop.Telepathy.Error.Disconnected
        org.freedesktop.Telepathy.Error.NetworkError
        org.freedesktop.Telepathy.Error.InvalidArgument
        org.freedesktop.Telepathy.Error.InvalidHandle
        org.freedesktop.Telepathy.Error.PermissionDenied
        org.freedesktop.Telepathy.Error.NotAvailable
        """
        presences = self.GetPresence(contacts)
        self.PresenceUpdate(presences)

    @dbus.service.method(tp.interfaces.CONNECTION_INTERFACE_PRESENCE,
                         in_signature='a{s(ss)}', out_signature='')
    def set_presences(self, contact_presences):
        """Set the presence and presence messages of contacts in the roster
        (something a normal client would not be able to do).

        Arguments:
        contact_presences -- dictionary mapping contact handle IDs to
                             (status, message) tuples
        """
        ids_matched = []
        for username in contact_presences.keys():
            for handle_obj in self._handles.values():
                if handle_obj.get_name() == username:
                    status = contact_presences[username][0]
                    status_message = contact_presences[username][1]

                    if status != None:
                        handle_obj.set_status(status)
                    if status_message != None:
                        handle_obj.set_status_message(status_message)

                    ids_matched.append(handle_obj.get_id())
        if len(ids_matched) >= 1:
            self.RequestPresence(ids_matched)
            self.save()
