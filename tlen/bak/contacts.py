# telepathy-pinocchio - dummy Telepathy connection manager for instrumentation
#
# Copyright (C) 2008-2009 Nokia Corporation
# Copyright (C) 2008-2009 Collabora Ltd.
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

import mimetypes
import dbus.service

import telepathy as tp

import pinocchio as pin

class Contacts(tp.server.ConnectionInterfaceContacts):
    """Contacts interface for a Telepathy Connection."""

    def __init__(self):
        tp.server.ConnectionInterfaceContacts.__init__(self)

        def get_interfaces():
            return [tp.CONN_INTERFACE,
                    tp.CONNECTION_INTERFACE_ALIASING,
                    tp.CONNECTION_INTERFACE_AVATARS,
                    tp.CONNECTION_INTERFACE_SIMPLE_PRESENCE]

        print self._implement_property_get
        self._implement_property_get(tp.CONNECTION_INTERFACE_CONTACTS,
            {'ContactAttributeInterfaces': get_interfaces})

    def GetContactAttributes(self, handles, interfaces, hold):
        interfaces = list(interfaces)

        all_attrs = {}

        for handle_id in handles:
            self.check_handle (tp.constants.HANDLE_TYPE_CONTACT, handle_id)

            handle_obj = self._handles[tp.constants.HANDLE_TYPE_CONTACT,
                                       handle_id]

            attrs = {}
            attrs[tp.CONN_INTERFACE + '/contact-id'] = handle_obj.get_name()
            if tp.CONNECTION_INTERFACE_ALIASING in interfaces:
                attrs[tp.CONNECTION_INTERFACE_ALIASING + '/alias'] = \
                    handle_obj.get_alias()
            if tp.CONNECTION_INTERFACE_AVATARS in interfaces:
                attrs[tp.CONNECTION_INTERFACE_AVATARS + '/token'] = \
                    handle_obj.get_avatar_token()
            if tp.CONNECTION_INTERFACE_SIMPLE_PRESENCE in interfaces:
                attrs[tp.CONNECTION_INTERFACE_SIMPLE_PRESENCE + '/presence'] = \
                    handle_obj.get_simple_presence()

            all_attrs[handle_id] = attrs

        return all_attrs
