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
from xml.dom import minidom
import string
import hashlib

import telepathy as tp

import tlen

def contacts_file_get_groups(connection):
    """Returns a set of the groups mentioned in the contacts file.

    Arguments:
    connection -- the initialized (though not necessarily opened) connection
    """
    try:
        contacts_file = open(connection._contacts_file, 'rU')
    except:
        print 'Could not open contact list file ', connection._contacts_file
        raise

    group_names = set()

    contacts_xml = minidom.parse(contacts_file)
    contacts_file.close()

    roster = contacts_xml.getElementsByTagName('roster')[0]
    groups_lists = roster.getElementsByTagName('groups')
    for groups_list in groups_lists:
        groups = groups_list.getElementsByTagName('group')
        for group in groups:
            group_names.add(group.firstChild.data)
        
    return group_names

class HandleContact(tp.server.Handle):
    """
    Full-fledged Contact wrapper of Telepathy Handle object.
    """

    def __init__(self, id, username, connection, extended_attrs={}):
        tp.server.Handle.__init__(self, id, tp.constants.HANDLE_TYPE_CONTACT,
                                  username)

        self._connection = connection

        _extended_attr_defaults = {'alias': u'',
                                   'group': '',
                                   'subscription': '',
                                   'avatar_bin': '',
                                   'avatar_mime': '',
                                   'avatar_path': '',
                                   'avatar_token': '',
                                   'status': 'unavailable',
                                   'status_message': u'',}
        self._extended_attrs = {}
        for attr in _extended_attr_defaults:
            if attr in extended_attrs:
                self._extended_attrs[attr] = extended_attrs[attr]
            else:
                self._extended_attrs[attr] = _extended_attr_defaults[attr]

        if self._extended_attrs['avatar_path']:
            # if the avatar path in the contact list file is relative, prepend
            # the avatars data dir to it
            if not os.path.isabs(self._extended_attrs['avatar_path']):
                self._extended_attrs['avatar_path'] = os.path.join(
                                            tlen.common.AVATAR_DIR_DEFAULT,
                                            self._extended_attrs['avatar_path'])

            if self._extended_attrs['avatar_path']:
                # set up the avatar metadata, but don't publish (we don't have a
                # handle within our connection by this point)
                self.set_avatar(self._extended_attrs['avatar_path'],
                                publish=False)

        self._last_avatar_token_published = ''

    # these each get their own function to match the style in tp.server.Handle
    def get_alias(self):
        return self._extended_attrs['alias']

    def get_group(self):
        return self._extended_attrs['group']

    def get_subscription(self):
        return self._extended_attrs['subscription']

    def get_avatar_bin(self):
        """Returns the raw image binary of the contact's avatar."""

        return self._extended_attrs['avatar_bin']

    def get_avatar_mime(self):
        return self._extended_attrs['avatar_mime']

    def get_avatar_path(self):
        return self._extended_attrs['avatar_path']

    def get_avatar_token(self):
        return self._extended_attrs['avatar_token']

    def get_connection(self):
        return self._connection

    def get_status_type(self):
        # TODO do this in a proper way, for instance Presence.set_presences
        # should also get the status type in the contact_presences argument
        types = \
        {
            'available': tp.CONNECTION_PRESENCE_TYPE_AVAILABLE,
            'chat': tp.CONNECTION_PRESENCE_TYPE_AVAILABLE,
            'away': tp.CONNECTION_PRESENCE_TYPE_AWAY,
            'dnd': tp.CONNECTION_PRESENCE_TYPE_BUSY,
            'xa': tp.CONNECTION_PRESENCE_TYPE_EXTENDED_AWAY,
            'unavailable': tp.CONNECTION_PRESENCE_TYPE_OFFLINE,
            'invisible': tp.CONNECTION_PRESENCE_TYPE_HIDDEN
        }
        try:
            return types[self.get_status()]
        except KeyError:
            return tp.CONNECTION_PRESENCE_TYPE_OFFLINE

    def get_status(self):
        return self._extended_attrs['status']

    def get_status_message(self):
        return self._extended_attrs['status_message']

    def get_simple_presence(self):
        return (self.get_status_type(),
                self.get_status(),
                self.get_status_message())

    def set_alias(self, alias):
        self._extended_attrs['alias'] = alias

    def set_group(self, group):
        self._extended_attrs['group'] = group

    def set_subscription(self, subscription):
        self._extended_attrs['subscription'] = subscription

    def set_avatar(self, avatar_path, publish=True):
        """Set the contact's avatar image path and generate derived
        attributes based on the image itself.
        
        Arguments:
        avatar_path -- path of the image file (absolute or relative)
        publish -- publish the new avatar immediately (default: True)

        Exceptions:
        org.freedesktop.Telepathy.Error.InvalidArgument
        """
        avatar_bin = ''

        # will raise tp.errors.InvalidArgument in case of error
        avatar_mime = tlen.common.image_filename_to_mime_type(avatar_path)

        try:
            avatar_file = open(avatar_path, 'r')
            avatar_bin = avatar_file.read()
            avatar_file.close()
        except IOError:
            raise tp.errors.InvalidArgument('failed to open avatar file: %s'
                                            % avatar_path)

        if avatar_bin:
            md5gen = hashlib.md5()
            md5gen.update(avatar_bin)
            self._extended_attrs['avatar_bin'] = avatar_bin
            self._extended_attrs['avatar_mime'] = avatar_mime
            # FIXME: if the token for this new avatar is the same as the old
            # one, exit early (and avoid emitting signals)
            self._extended_attrs['avatar_token'] = md5gen.hexdigest()
            self._extended_attrs['avatar_path'] = avatar_path
        else:
            self._extended_attrs['avatar_token'] = \
                                    self._extended_attr_defaults['avatar_token']
            self._extended_attrs['avatar_path'] = \
                                    self._extended_attr_defaults['avatar_path']

        if publish:
            if self._last_avatar_token_published != \
                                        self._extended_attrs['avatar_token']:

                self._connection.AvatarUpdated(
                                        self.get_id(),
                                        self._extended_attrs['avatar_token'])
                self._last_avatar_token_published = \
                                        self._extended_attrs['avatar_token']

    def set_status(self, status):
        self._extended_attrs['status'] = status

    def set_status_message(self, status_message):
        self._extended_attrs['status_message'] = status_message

    def get_xml(self, contact_lists, groups):
        dom_impl = minidom.getDOMImplementation()
        xml_doc = dom_impl.createDocument(None, 'contact', None)
        contact_xml = xml_doc.documentElement

        # add newline for human-readability
        newline_value = xml_doc.createTextNode('\n')
        contact_xml.appendChild(newline_value)

        tlen.common.xml_insert_element(xml_doc, contact_xml, 'username',
                                      self.get_name())

        skip_attrs = ('avatar_bin', 'avatar_mime', 'avatar_token')
        for attr, value in self._extended_attrs.items():
            if attr not in skip_attrs:
                tlen.common.xml_insert_element(xml_doc, contact_xml, attr, value)

        contact_lists_xml = tlen.common.xml_insert_element(xml_doc, contact_xml,
                                                          'contact_lists', '\n')
        for contact_list in contact_lists:
            tlen.common.xml_insert_element(xml_doc, contact_lists_xml, 'list',
                                          contact_list)

        groups_xml = tlen.common.xml_insert_element(xml_doc, contact_xml,
                                                   'groups', '\n')
        for group in groups:
            tlen.common.xml_insert_element(xml_doc, groups_xml, 'group', group)

        return contact_xml

class StoredList:
    def __init__(self, connection, channel_handle_obj, list_tag_name,
                 list_item_tag_name):
        # FIXME: update this
        """
        Arguments:
        connection -- connection this StoredContactList corresponds to
        channel_handle_obj -- handle object of the channel this list maps to
        list_tag_name -- name of the list-enclosing tag (eg, "contact_lists")
        list_item_tag_name -- name of the list item tag (eg, "list")

        Exceptions:
        IOError -- failed to read contact list file
        IndexError -- contact list file parsing failed
        """
        self.connection = connection
        self.channel_handle_obj = channel_handle_obj
        self.list_tag_name = list_tag_name
        self.list_item_tag_name = list_item_tag_name

        contacts_xml = minidom.parseString(connection._xmlized_contact_list)
        contacts_xml = contacts_xml.getElementsByTagName('query')[0]
        contacts = contacts_xml.getElementsByTagName('item')

        channel_name = self.channel_handle_obj.get_name()
        print "channel_name: ", channel_name
        self.contacts = []
        for contact in contacts:
#            <iq type='result' id='GetRoster'>
#                <query xmlns='jabber:iq:roster'>
#                    <item jid='segfault@tlen.pl' name='segfault@tlen.pl' subscription='both'>
#                        <group>Znajomi</group>
#                    </item>
#                    <item ask='subscribe' jid='portsentry@tlen.pl' name='portsentry@tlen.pl' subscription='none'>
#                        <group>Znajomi</group>
#                    </item>
#                </query>
#            </iq>
            print "contact: ", contact.toxml()
            subscription = contact.attributes["subscription"].value
            if subscription == 'both':
                #jesli subskrybcja kontaktu == both to znaczy ze mozemy odbierac i wysylac status do osoby itd.
                if channel_name == 'allow' or channel_name == 'stored' or channel_name == 'subscribe' or channel_name == 'publish':
                    handle_contact = self.contact_xml_to_handle(contact,
                                                                connection)

                    self.contacts.append(handle_contact)
            if subscription == 'to':
                if channel_name == 'allow' or channel_name == 'stored' or channel_name == 'subscribe':
                    handle_contact = self.contact_xml_to_handle(contact,
                                                                connection)

                    self.contacts.append(handle_contact)
            if subscription == 'from':
                if channel_name == 'allow' or channel_name == 'stored' or channel_name == 'publish':
                    handle_contact = self.contact_xml_to_handle(contact,
                                                                connection)

                    self.contacts.append(handle_contact)
            if subscription == 'none':
                if channel_name == 'allow' or channel_name == 'stored':
                    handle_contact = self.contact_xml_to_handle(contact,
                                                                connection)

                    self.contacts.append(handle_contact)

    def get_handle_objs(self):
        return self.contacts

    def contact_xml_to_handle(self, contact_xml, connection):
        handle_contact = None
        extended_attrs = {}

        subscription = contact_xml.attributes["subscription"].value

        try:
            username = contact_xml.attributes["jid"].value
            print "contact_xml_to_handle: jid - ", username
        except:
            raise ValueError, 'contact has no username'

        try:
            group = contact_xml.getElementsByTagName('group')[0].firstChild.nodeValue
            print "contact_xml_to_handle: group - ", group
        except:
            group = ''

        CONTACT_HANDLE = tp.constants.HANDLE_TYPE_CONTACT
        id, id_is_new = connection.get_handle_id_idempotent(CONTACT_HANDLE,
                                                            username)
        # only create HandleContact objects as necessary (to avoid unwanted
        # side-effects in the form of duplicate signals)
        if id_is_new:
            extended_attrs = {}
            for attr in ('alias', 'group', 'subscription'):
                try:
                    if attr == 'alias':
                        extended_attrs[attr] = connection.decodeTlenData(contact_xml.attributes["name"].value)
                    if attr == 'group':
                        extended_attrs[attr] = connection.decodeTlenData(group)
                    if attr == 'subscription':
                        extended_attrs[attr] = subscription
                except:
                    pass
            
            handle_contact = HandleContact(id, username, connection,
                                           extended_attrs)
        else:
            handle_contact = connection._handles[CONTACT_HANDLE, id]

        return handle_contact

class StoredContactList(StoredList):
    def __init__(self, connection, channel_handle_obj):
        """
        Arguments:
        connection -- connection this StoredContactList corresponds to
        channel_handle_obj -- handle object of the channel this list maps to

        Exceptions:
        IOError -- failed to read contact list file
        IndexError -- contact list file parsing failed
        """
        StoredList.__init__(self, connection, channel_handle_obj,
                            'contact_lists', 'list')

class StoredGroup(StoredList):
    def __init__(self, connection, channel_handle_obj):
        """
        Arguments:
        connection -- connection this StoredGroup corresponds to
        channel_handle_obj -- handle object of the channel this list maps to

        Exceptions:
        IOError -- failed to read contact list file
        IndexError -- contact list file parsing failed
        """
        StoredList.__init__(self, connection, channel_handle_obj,
                            'groups', 'group')
