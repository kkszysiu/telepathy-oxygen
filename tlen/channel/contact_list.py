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

#import dbus
import telepathy as tp

import tlen

class ContactList(tp.server.ChannelTypeContactList,
                  tp.server.ChannelInterfaceGroup):
    """
    Set of contacts corresponding to a Telepathy ContactList channel.
    
    Implements DBus interface org.freedesktop.Telepathy.Channel.Interface.Group
    """

    def __init__(self, connection, channel_handle_obj, account_id):
        tp.server.ChannelTypeContactList.__init__(self, connection,
                                                  channel_handle_obj)
        tp.server.ChannelInterfaceGroup.__init__(self)

        print 'ContactList - init'

        self.parent_connection = connection
        self.account_id = account_id
        contacts_disk = tlen.server.StoredContactList(connection,
                                                     channel_handle_obj)

        handles_initial = contacts_disk.get_handle_objs()
        for handle_obj in handles_initial:
            connection._handles[tp.constants.HANDLE_TYPE_CONTACT,
                                handle_obj.get_id()] = handle_obj

        # send initial member list as any other list change
        # this stores these HandleContact objects in self._members
        self.MembersChanged('', handles_initial, (), (), (), 0,
                            tp.constants.CHANNEL_GROUP_CHANGE_REASON_NONE)

        handle_ids = [h.get_id() for h in handles_initial]
        # announce the presence of our new contacts
        #connection.RequestPresence(handle_ids)

        # announce avatars for contacts with avatars
        #connection.RequestAvatars(handle_ids)

        # declare our group capabilities
        self.GroupFlagsChanged(tp.constants.CHANNEL_GROUP_FLAG_CAN_ADD |
                               tp.constants.CHANNEL_GROUP_FLAG_CAN_REMOVE, 0)

    def AddMembers(self, contacts, message):
        """Add list of contacts to this group.
        
        Arguments:
        contacts -- list of contact handles to add
        message -- message to send to server along with request (if supported)
        """
        print 'AddMembers'
        handle_type = tp.constants.HANDLE_TYPE_CONTACT

        for handle_id in contacts:
            if (handle_type, handle_id) not in self.parent_connection._handles:
                raise tp.errors.InvalidHandle('unknown contact handle %d' % \
                                              handle_id)
            contact_name = self.parent_connection.get_handle_obj(handle_type, handle_id).get_name()
            print contact_name
            alias = self.parent_connection.get_handle_obj(handle_type, handle_id).get_alias()
            print alias
            group = 'Kontakty'
            print "add contact: name - %s, alias - %s, group - %s" % (contact_name, alias, group)
            self.parent_connection.factory.sendStanza(self.parent_connection._stanzas['add_contact'] % (contact_name, alias, group))
            self.parent_connection.factory.sendStanza(self.parent_connection._stanzas['subscription_ask'] % contact_name)
            

        conn_handles = self.parent_connection._handles
        handle_objs = set([conn_handles[tp.constants.HANDLE_TYPE_CONTACT, x]
                           for x in contacts])

        self.MembersChanged(message, handle_objs, (), (), (),
                            self.parent_connection._self_handle,
                            tp.constants.CHANNEL_GROUP_CHANGE_REASON_NONE)

    def RemoveMembers(self, contacts, message):
        """Remove list of contacts from this group.
        
        Arguments:
        contacts -- list of contact handles to add
        message -- message to send to server along with request (if supported)
        """
        print "RemoveMembers: ", str(contacts)
        self.RemoveMembersWithReason(
                                contacts, message,
                                tp.constants.CHANNEL_GROUP_CHANGE_REASON_NONE)

    def RemoveMembersWithReason(self, contacts, message, reason):
        """Remove list of contacts from this group.
        
        Arguments:
        contacts -- list of contact handles to add
        message -- message to send to server along with request (if supported)
        reason -- Channel_Group_Change_Reason as to why the members are being
                  removed
        """
        print "RemoveMembersWithReason"
        if reason < 0 or reason > tp.constants.LAST_CHANNEL_GROUP_CHANGE_REASON:
            raise tp.errors.InvalidArgument('invalid group change reason')

        handle_type = tp.constants.HANDLE_TYPE_CONTACT

        for handle_id in contacts:
            if (handle_type, handle_id) not in self.parent_connection._handles:
                raise tp.errors.InvalidHandle('unknown contact handle %d' % \
                                              handle_id)
            contact_name = self.parent_connection.get_handle_obj(handle_type, handle_id).get_name()
            print "remove contact: name - %s" % (contact_name)
            self.parent_connection.factory.sendStanza(self.parent_connection._stanzas['remove_contact'] % contact_name)

        conn_handles = self.parent_connection._handles
        handle_objs = set([conn_handles[tp.constants.HANDLE_TYPE_CONTACT, x]
                           for x in contacts])

        self.MembersChanged(message, (), handle_objs, (), (),
                            self.parent_connection._self_handle, reason)

class Group(tp.server.ChannelTypeContactList, tp.server.ChannelInterfaceGroup):
    """
    A user-defined group of contacts.
    
    Implements DBus interface org.freedesktop.Telepathy.Channel.Interface.Group
    """

    def __init__(self, connection, channel_handle_obj, account_id):
        tp.server.ChannelTypeContactList.__init__(self, connection,
                                                  channel_handle_obj)
        tp.server.ChannelInterfaceGroup.__init__(self)

        self.parent_connection = connection
        self.account_id = account_id

        contacts_disk = tlen.server.StoredGroup(connection, channel_handle_obj)

        handles_initial = contacts_disk.get_handle_objs()
        for handle_obj in handles_initial:
            connection._handles[tp.constants.HANDLE_TYPE_CONTACT,
                                handle_obj.get_id()] = handle_obj

        # send initial member list as any other list change
        # this stores these HandleContact objects in self._members
        self.MembersChanged('', handles_initial, (), (), (), 0,
                            tp.constants.CHANNEL_GROUP_CHANGE_REASON_NONE)


        handle_ids = [h.get_id() for h in handles_initial]
        # announce the presence of our new contacts
        connection.RequestPresence(handle_ids)

        # announce avatars for contacts with avatars
        connection.RequestAvatars(handle_ids)

        # declare our group capabilities
        self.GroupFlagsChanged(tp.constants.CHANNEL_GROUP_FLAG_CAN_ADD |
                               tp.constants.CHANNEL_GROUP_FLAG_CAN_REMOVE, 0)

    def AddMembers(self, contacts, message):
        """Add list of contacts to this group.
        
        Arguments:
        contacts -- list of contact handles to add
        message -- message to send to server along with request (if supported)
        """
        handle_type = tp.constants.HANDLE_TYPE_CONTACT

        for handle_id in contacts:
            if (handle_type, handle_id) not in self.parent_connection._handles:
                raise tp.errors.InvalidHandle('unknown contact handle %d' % \
                                              handle_id)

        conn_handles = self.parent_connection._handles
        handle_objs = set([conn_handles[tp.constants.HANDLE_TYPE_CONTACT, x]
                           for x in contacts])

        self.MembersChanged(message, handle_objs, (), (), (),
                            self.parent_connection._self_handle,
                            tp.constants.CHANNEL_GROUP_CHANGE_REASON_NONE)

        self.parent_connection.save()

    def RemoveMembers(self, contacts, message):
        """Remove list of contacts from this group.
        
        Arguments:
        contacts -- list of contact handles to add
        message -- message to send to server along with request (if supported)
        """
        self.RemoveMembersWithReason(
                                contacts, message,
                                tp.constants.CHANNEL_GROUP_CHANGE_REASON_NONE)

    def RemoveMembersWithReason(self, contacts, message, reason):
        """Remove list of contacts from this group.
        
        Arguments:
        contacts -- list of contact handles to add
        message -- message to send to server along with request (if supported)
        reason -- Channel_Group_Change_Reason as to why the members are being
                  removed
        """
        if reason < 0 or reason > tp.constants.LAST_CHANNEL_GROUP_CHANGE_REASON:
            raise tp.errors.InvalidArgument('invalid group change reason')

        handle_type = tp.constants.HANDLE_TYPE_CONTACT

        for handle_id in contacts:
            if (handle_type, handle_id) not in self.parent_connection._handles:
                raise tp.errors.InvalidHandle('unknown contact handle %d' % \
                                              handle_id)

        conn_handles = self.parent_connection._handles
        handle_objs = set([conn_handles[tp.constants.HANDLE_TYPE_CONTACT, x]
                           for x in contacts])

        self.MembersChanged(message, (), handle_objs, (), (),
                            self.parent_connection._self_handle, reason)

        self.parent_connection.save()
