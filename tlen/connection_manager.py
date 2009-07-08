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

import os.path
import shutil
import sys
import hashlib

from xml.dom import minidom

import dbus
import dbus.service
import telepathy as tp

import tlen.common
import tlen.connection

class ConnectionManager(tp.server.ConnectionManager):
    """
    Tlen Connection Manager
    
    Implements DBus interface org.freedesktop.Telepathy.ConnectionManager
    """
    def __init__(self):
        # try current symbol locations first
	print "ConnectionManager - init"
        try:
            from dbus.bus import NAME_FLAG_DO_NOT_QUEUE \
                    as NAME_FLAG_DO_NOT_QUEUE
            from dbus.bus import REQUEST_NAME_REPLY_EXISTS \
                    as REQUEST_NAME_REPLY_EXISTS
        # fall back to older locations for older versions of dbus-python
        except ImportError:
            from _dbus_bindings import NAME_FLAG_DO_NOT_QUEUE \
                    as NAME_FLAG_DO_NOT_QUEUE
            from _dbus_bindings import REQUEST_NAME_REPLY_EXISTS \
                    as REQUEST_NAME_REPLY_EXISTS

        tp.server.ConnectionManager.__init__(self, 'oxygen')

        self._protos[tlen.common.PROTO_DEFAULT] = tlen.connection.Connection

        bus = dbus.SessionBus()

        rv = bus.request_name(tlen.common.CM_TLEN, NAME_FLAG_DO_NOT_QUEUE)
        if rv == REQUEST_NAME_REPLY_EXISTS:
            raise dbus.NameExistsException (tlen.common.CM_TLEN)

    def GetParameters(self, proto):
        """Returns list of parameters for this protocol."""

	print "ConnectionManager - GetParameters"

        if proto in self._protos:
            conn = self._protos[proto]
            print conn
            ret = []
            for param_name, param_type in conn._mandatory_parameters.iteritems():
                param = (param_name,
                        tp.CONN_MGR_PARAM_FLAG_REQUIRED,
                        param_type,
                        '')
                ret.append(param)

            for param_name, param_type in conn._optional_parameters.iteritems():
                if param_name in conn._parameter_defaults:
                    default_value = conn._parameter_defaults[param_name]
                    param = (param_name,
                            tp.CONN_MGR_PARAM_FLAG_HAS_DEFAULT,
                            param_type,
                            default_value)
                else:
                    param = (param_name, 0, param_type, '')
                ret.append(param)
            return ret
        else:
            raise telepathy.NotImplemented('unknown protocol %s' % proto)

    def connection_connect(self, connection):
        """Treat this connection as if it connected to a real server.
        
        Arguments:
        connection -- connection to track and support

        Exceptions:
        telepathy.errors.NotAvailable 
        """

	print "ConnectionManager - connection_connect"

        # there's no reason to raise NotAvailable, but this function would
        # hypothetically raise it if it were on a real network

    def connection_disconnect(self, connection):
        """Treat this connection as if it disconnected from a real server.
        
        Arguments:
        connection -- connection to no longer track
        """

	print "ConnectionManager - connection disconnect"

        if connection in self._connections:
            self._connections.remove(connection)

    def channel_new(self, connection, channel_type, handle_type, handle,
                    suppress_handler):
        """Returns a channel for the connection; if it does not already exist,
        create a new one.
        
        Arguments:
        connection -- connection on which to open a new channel
        channel_type -- DBus interface name for the new channel type
        handle_type -- Telepathy handle type for the channel
        handle -- handle for the new or existing channel (as in RequestChannel)
        suppress_handler -- True to prevent any automatic handling of channel
        """

	print "ConnectionManager - channel_new"

        if connection not in self._connections:
            raise tp.errors.Disconnected('connection unknown')

        handle_obj = connection.get_handle_obj(handle_type, handle)

        if channel_type == tp.interfaces.CHANNEL_TYPE_CONTACT_LIST:
            channel_result = self._channel_new_contact_list(connection,
                                                            handle_type, handle,
                                                            suppress_handler)
        else:
            # TODO: should be, but is not yet, implemented
            # tp.interfaces.CHANNEL_TYPE_STREAMED_MEDIA:
            # tp.interfaces.CHANNEL_TYPE_ROOM_LIST:
            # tp.interfaces.CHANNEL_TYPE_TEXT:
            # tp.interfaces.CHANNEL_TYPE_TUBES:
            raise tp.errors.NotImplemented()

        return channel_result

    def _channel_new_contact_list(self, connection, handle_type, handle,
                                  suppress_handler):
        """Returns a contact list channel for the connection; if it does not
        already exist, create a new one.
        
        Arguments:
        connection -- connection on which to open a new channel
        handle_type -- Telepathy handle type for the channel
        handle -- handle for the new or existing channel (as in RequestChannel)
        suppress_handler -- True to prevent any automatic handling of channel
        """

	print "ConnectionManager - _channel_new_contact_list"

        handle_obj = connection.get_handle_obj(handle_type, handle)

        if handle_type == tp.constants.HANDLE_TYPE_LIST:
            account_id = connection.get_account_id()
            channel_result = None

            for channel in connection._channels:
                if channel._type == tp.interfaces.CHANNEL_TYPE_CONTACT_LIST:
                    try:
                        if channel.account_id == account_id:
                            if channel._handle.get_id() == handle:
                                # channel already exists; return it to caller
                                channel_result = channel
                                break
                    except AttributeError:
                        pass

            if not channel_result:
                channel_result = tlen.channel.contact_list.ContactList(
                                                                connection,
                                                                handle_obj,
                                                                account_id)
                connection.add_channel(channel_result, handle_obj,
                                       suppress_handler)
        elif handle_type == tp.constants.HANDLE_TYPE_GROUP:
            account_id = connection.get_account_id()
            channel_result = None

            for channel in connection._channels:
                if channel._type == tp.interfaces.CHANNEL_TYPE_CONTACT_LIST:
                    try:
                        if channel.account_id == account_id:
                            if channel._handle.get_id() == handle:
                                # channel already exists; return it to caller
                                channel_result = channel
                                break
                    except AttributeError:
                        pass

            if not channel_result:
                channel_result = tlen.channel.contact_list.Group(connection,
                                                                handle_obj,
                                                                account_id)
                connection.add_channel(channel_result, handle_obj,
                                       suppress_handler)
        else:
            raise tp.errors.InvalidArgument()

        return channel_result

    def connections_teardown(self):
        """Tear down all managed connections."""

	print "ConnectionManager - connections_tearsdown"

        for connection in self._connections:
            connection.Disconnect()