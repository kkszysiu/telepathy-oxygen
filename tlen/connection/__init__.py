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

import time
from xml.dom import minidom
import sys
import hashlib
import urllib

import dbus

import telepathy as tp

from twisted.words.protocols.jabber import xmlstream
from twisted.internet import protocol
from twisted.words.xish import domish, utility
from twisted.internet import reactor
from twisted.python import log

import tlen
from aliasing import *
#from avatars import *
from capabilities import *
#from presence import *
from simple_presence import *
from contacts import *

log.startLogging(sys.stdout)

TLEN_STANZAS = {
    "message":"<message to='%s' type='normal'><body>%s</body></message>",
    "presence":"<presence><show>%s</show></presence>",
    "presence_with_status":"<presence><show>%s</show><status>%s</status></presence>",
    "get_roster":"<iq type='get' id='GetRoster'><query xmlns='jabber:iq:roster'></query></iq>",
    #subskrypcje
    "subscription_ask":"<presence to='%s' type='subscribe'/>",
    "subscription_allow":"<presence to='%s' type='subscribed'/>",
    "subscription_deny":"<presence to='%s' type='unsubscribed'/>",
    "subscription_remove":"<presence to='%s' type='unsubscribed'/>",
    #dodawanie, aktualizacja, usuwanie kontaktow na serwerze
    #"add_contact":"<iq type='set'><query xmlns='jabber:iq:roster'><item jid='%s' name='%s'><group>%s</group></item></query></iq>",
    "add_contact":"<iq type='set'><query xmlns='jabber:iq:roster'><item jid='%s' subscription='' ask='' name='%s'><group>%s</group></item></query></iq>",
    "update_contact":"<iq type='set'><query xmlns='jabber:iq:roster'><item jid='%s' name='%s' subscription='to'><group>Kontakty</group></item></query></iq>",
    "remove_contact":"<iq type='set'><query xmlns='jabber:iq:roster'><item jid='%s' subscription='remove' /></query></iq>",
    #messages
    "message_send":"<message to='%s' type='chat'><body>%s</body></message>",
    "end_session":"</s>"
                }

""" TWISTED TLEN CORE """

def magicHash(password, sid):
        magic1 = 0x50305735
        magic2 = 0x12345671
        sum = 7
        for s in range(len(password)):
            z = ord(password[s]);
            if (z == ' '):
                continue
            if (z == '\t'):
                continue
            magic1 = magic1 ^ ((((magic1 & 0x3f) + sum) * z) + (magic1 << 8))
            magic2 = magic2 + ((magic2 << 8) ^ magic1)
            sum += z
            magic1 = magic1 & 0x7fffffff
            magic2 = magic2 & 0x7fffffff

        hash = ('%08x%08x'%(magic1, magic2))
	return sid+hash

def ping(xmlstream):
	xmlstream.send('  \t  ')
	reactor.callLater(40, ping, xmlstream)

class TlenAuthInitializer(object):
	def __init__(self, xs):
		self.xmlstream = xs

	def initialize(self):
		iq = xmlstream.IQ(self.xmlstream, "set")
		iq['id'] = xmlstream.XmlStream.sid
		q = iq.addElement('query', 'jabber:iq:auth')
		q.addElement('username', content = self.xmlstream.authenticator.jid)
		q.addElement('digest', content = hashlib.sha1(magicHash(self.xmlstream.authenticator.password, xmlstream.XmlStream.sid)).hexdigest())
		q.addElement('resource', content  = 't')
		q.addElement('host', content = 'tlen.pl')
		d = iq.send()
		d.addCallback(self._authreply)
		d.addErrback(self._authfail)

	def _authreply(self, el):
		reactor.callLater(40, ping, self.xmlstream)
                self.xmlstream.factory.clientReady(self.xmlstream)

	def _authfail(self, el):
		print "_authfail: ", el

class TlenAuthenticator(xmlstream.ConnectAuthenticator):
	def __init__(self, jid, password, host):
		xmlstream.ConnectAuthenticator.__init__(self, host)
		self.jid = jid
		self.password = password

	def associateWithStream(self, xs):
		xs.version = (0, 0)
		xmlstream.ConnectAuthenticator.associateWithStream(self, xs)

		inits = [(TlenAuthInitializer, True)]
		for initClass, required in inits:
			init = initClass(xs)
			init.required = required
			xs.initializers.append(init)

class TlenStream(xmlstream.XmlStream):
        def connectionMade(self):
            xmlstream.XmlStream.connectionMade(self)

	def sendHeader(self):
		rootElem = domish.Element((None, 's'))
		rootElem['v'] = '9'
		rootElem['t'] = '06000224'
		self.rootElem = rootElem
		self.send(rootElem.toXml(prefixes=self.prefixes, closeElement=0))
		self._headerSent = True

	def sendFooter(self):
		self.send('</s>')

	def onDocumentStart(self, rootelem):
		xmlstream.XmlStream.onDocumentStart(self, rootelem)
		if rootelem.hasAttribute("i"):
			xmlstream.XmlStream.sid = rootelem["i"]
		self.authenticator.streamStarted(rootelem)

        def connectionLost(self, reason):
            print 'connectionLost: ', reason.getErrorMessage()
#            reactor.stop()

class TlenStreamFactory(xmlstream.XmlStreamFactory):
    def __init__(self, authenticator):
        xmlstream.XmlStreamFactory.__init__(self, authenticator)
        self.authenticator = authenticator
        self.messageQueue = []
        self.clientInstance = None

    def clientReady(self, instance):
        self.clientInstance = instance
        for xml in self.messageQueue:
            self.sendStanza(xml)

    def sendStanza(self, xml):
        if self.clientInstance is not None:
            print 'sendStanza xml: ', xml
            self.clientInstance.send(xml)
        else:
            self.messageQueue.append(xml)

    def clientConnectionFailed(self, connector, reason):
        print 'connection failed:', reason.getErrorMessage()
        reactor.stop()

    def clientConnectionLost(self, connector, reason):
        print 'connection lost:', reason.getErrorMessage()
        reactor.stop()

    def buildProtocol(self, _):
        self.resetDelay()
        # Create the stream and register all the bootstrap observers
        xs = TlenStream(self.authenticator)
        xs.factory = self
        for event, fn in self.bootstraps: xs.addObserver(event, fn)
        return xs

""" END OF TWISTED TLEN CORE """











class Connection(tp.server.Connection,
                 aliasing.Aliasing,
#                 avatars.Avatars,
                 capabilities.Capabilities,
#                 presence.Presence,
                 simple_presence.SimplePresence,
                 contacts.Contacts
                ):
    """Representation of a virtual connection."""

    print "Connection"

    _CONTACT_LIST_NAMES = ('subscribe', 'publish', 'hide', 'allow', 'deny', 'stored')

    _mandatory_parameters = {'account': 's', 'password': 's'}
    _parameter_defaults = {'account': 'tlentestacc', 'password': 'xxxxxx'}

    def __init__(self, manager, parameters):
        self.check_parameters(parameters)

        tp.server.Connection.__init__(self, tlen.common.PROTO_DEFAULT,
                                      unicode(self.unTID(parameters['account'])),
                                      'oxygen')
        aliasing.Aliasing.__init__(self)
#        avatars.Avatars.__init__(self)
        capabilities.Capabilities.__init__(self)
#        presence.Presence.__init__(self)
        contacts.Contacts.__init__(self)
        simple_presence.SimplePresence.__init__(self)
        print self.unTID(parameters['account']), parameters['password']
        self.factory = TlenStreamFactory(TlenAuthenticator(self.unTID(parameters['account']), parameters['password'], 's1.tlen.pl'))

        #litle hack
        self._stanzas = TLEN_STANZAS
        self.stanzas = TLEN_STANZAS
        # accept the default alias, etc. (including the required, though empty,
        # avatar)
        account_id = self.get_account_id()
        extended_attrs = {}
        self_handle = tlen.server.HandleContact(self.get_handle_id(),
                                               account_id, self, extended_attrs)
        self.self_handle = self_handle
        self.set_self_handle(self_handle)

        self._manager = manager
        self._recv_id = 0
#        self._contacts_file = tlen.common.get_contacts_file(
#                                            account_id,
#                                            pin.common.PREFIX_SAVED_PREFERRED)

    def Connect(self):
        """Request connection establishment."""

	print "Connection - Connect"
        reactor.connectTCP('s1.tlen.pl', 443, self.factory)
        self.StatusChanged(tp.CONNECTION_STATUS_CONNECTING,
                        tp.CONNECTION_STATUS_REASON_REQUESTED)
        self._manager.connection_connect(self)

        self.factory.addBootstrap('/*', self.lg)
        self.factory.addBootstrap('/presence', self._on_presence_changed)
        self.factory.addBootstrap('/iq[@type="result" and @id="GetRoster"]/*', self._on_roster_received)
        self.factory.addBootstrap('/message/*', self._on_msg_received)
        self.factory.addBootstrap(xmlstream.INIT_FAILED_EVENT, self.err)
        #drobny hack. Ustawia tatus na niewidoczny
        self.factory.sendStanza(self._stanzas['get_roster'])

    def Disconnect(self):
        """Request connection tear-down."""

	print "Connection - Disconnect"

        self._manager.connection_disconnect(self)
        self.StatusChanged(tp.constants.CONNECTION_STATUS_DISCONNECTED,
                           tp.constants.CONNECTION_STATUS_REASON_REQUESTED)
        reactor.stop()

    def RequestChannel(self, channel_type, handle_type, handle,
                       suppress_handler):
        """
        Returns a new channel to the given handle.
        
        Arguments:
        channel_type -- DBus interface name for the type of channel requested
        handle_type -- the Handle_Type of handle, or Handle_Type_None if no
                       handle is specified
        handle -- nonzero handle to open a channel to, or zero for an
                  anonymous channel (handle_type must be Handle_Type_None)
        suppress_handler -- true if requesting client will display the channel
                            itself (and no handler should take responsibility
                            for it)

        Returns:
        object_path -- DBus object path for the channel (new or retrieved)

        Exceptions:
        telepathy.errors.NotImplemented
        telepathy.errors.Disconnected
        """

	print "Connection - RequestChannel IN channel_type - %s, handle_type - %s" % (channel_type, handle_type)

        self.check_connected()

        channel = self._channel_get_or_create (channel_type, handle_type,
                                               handle, suppress_handler)

        return channel._object_path

    @dbus.service.method(tp.interfaces.CONNECTION, in_signature='uas',
                         out_signature='au', sender_keyword='sender')
    def RequestHandles(self, handle_type, names, sender):
        """Returns a list of handles for the given type and names. Creates new
        handle IDs only as necessary (as required in the specification and as
        violated in telepathy-python 0.14.0's default implementation).
        
        Arguments:
        handle_type -- the Handle_Type of handle handles
        names -- iterable of names for the handles
        sender -- magic DBus name for the caller (not passed explicitly)

        Returns:
        ids -- list of corresponding handle IDs
        """

	print "Connection - RequestHandles, handle_type: %s, namrs: %s, sender: %s" % (str(handle_type), str(names), str(sender))

        self.check_connected()
        self.check_handle_type(handle_type)

        ids = []
        for name in names:
            id, id_is_new = self.get_handle_id_idempotent(handle_type, name)
            if id_is_new:
                if handle_type == tp.constants.HANDLE_TYPE_CONTACT:
                    print "RequestHandles - yeap were there"
                    name = self.checkTID(name)
                    handle = tlen.server.HandleContact(id, name, self,
                                                      extended_attrs={})
                    #self.factory.sendStanza(self._stanzas['subscription_ask'] % name)
                else:
                    print "RequestHandles - nope were there"
                    handle = tp.server.Handle(id, handle_type, name)

                self._handles[handle_type, id] = handle
            else:
                handle = self._handles[handle_type, id]

            # self._client_handles is a set, so this won't make dupes
            self.add_client_handle(handle, sender)
            ids.append(id)

        return ids

    @dbus.service.method(tp.interfaces.CONNECTION, in_signature='',
                         out_signature='')
    def reset_to_default_contacts_file(self):
        """Reverts to the default contact list for this account and disconnects
        this Connection. The next instantiation of a Connection for this account
        will use the default contact list.

        Note that disconnecting the Connection will affect any other clients
        using this Connection.
        """

	print "Connection - reset_to_default_contacts_file"

        self.Disconnect()

        # clear out any modified version of the contact list (upon next
        # Connect(), the default contact list will be read in)
        account_id = self.get_account_id()
        filename = pin.common.get_contacts_file(account_id,
                                                pin.common.PREFIX_SAVED)
        if os.path.isfile(filename):
            os.remove(filename)

    def _channel_get_or_create (self, channel_type, handle_type, handle,
                                suppress_handler):
        """
        Returns a new channel to the given handle.
        
        Arguments:
        channel_type -- DBus interface name for the type of channel requested
        handle_type -- the Handle_Type of handle, or Handle_Type_None if no
                       handle is specified
        handle -- nonzero handle to open a channel to, or zero for an
                  anonymous channel (handle_type must be Handle_Type_None)
        suppress_handler -- true if requesting client will display the channel
                            itself (and no handler should take responsibility
                            for it)

        Returns:
        channel -- telepathy.server.Channel object (new or retrieved)

        Exceptions:
        telepathy.errors.NotImplemented
        telepathy.errors.Disconnected
        """

	print "Connection - _channel_get_or_create"

        self.check_connected()

        channel = None

        # TODO: support handle_type == 0 && handle == 0

        for channel_existing in self._channels:
            if channel_type == channel_existing.GetChannelType():
                handle_obj = None
                channel_handle_obj = None

                channel_handle_type, channel_handle_obj = \
                                                    channel_existing.GetHandle()

                # this would be a bit simpler, but we have to factor in the
                # given handle and handle_type
                if (handle_type, handle) in self._handles.keys():
                    handle_obj = self._handles[handle_type, handle]

                if handle_obj and channel_handle_obj:
                    handle_name =  handle_obj.get_name()
                    channel_name = channel_handle_obj.get_name()

                    if     handle_name == channel_name \
                       and handle_type == channel_handle_type:
                        channel = channel_existing

        if not channel:
            channel = self._manager.channel_new(self, channel_type, handle_type,
                                                handle, suppress_handler)

        return channel

    def get_handle_obj(self, type, id):
        """Returns the Handle object for a given handle (type, ID) pair.

        Arguments:
        type -- the Telepathy Handle_Type
        id -- the integer handle value
        """
        print "Connection - get_handle_obj - init"
        self.check_handle(type, id)

	print "Connection - get_handle_obj IN type - %s id - %s" % (type, id)

        return self._handles[type, id]

    def get_handle_id_idempotent(self, handle_type, name):
        """Returns a handle ID for the given type and name, creating a new
        handle ID only as necessary (similar to RequestHandles' definition in
        the specification).

        Arguments:
        handle_type -- Telepathy Handle_Type for all the handles
        name -- username for the contact

        Returns:
        handle_id -- ID for the given username
        is_new -- True if the ID was created (did not exist)
        """

        is_new = False
        handle_id = 0
        for handle in self._handles.values():
            if handle.get_name() == name:
                handle_id = handle.get_id()
                break

        # if the handle doesn't already exist, create a new one
        if handle_id <= 0:
            handle_id = self.get_handle_id()
            is_new = True
        
	print "Connection - get_handle_id_idempotent in handle_type - %s, name - %s... out handle_id - %s, is_new - %s" % (handle_type, name, handle_id, is_new)

        return handle_id, is_new

    def get_account_id(self):
        """Returns the sanitized account name for the given connection."""

        print "Connection - get_account_id ", self._name.get_name().split('.')[-1]

        return self._name.get_name().split('.')[-1]

    def get_contact_channel_membership_info(self):
        """Returns a map of contacts to their contact lists and groups.

        Returns:
        mapping -- dict of handle IDs to [contact list names, group names]
        """

	print "Connection - get_contact_channel_membership_info"

        MAPPING_CONTACT_LISTS = 0
        MAPPING_GROUPS = 1
        mapping = {}

        for channel in self._channels:
            if channel.GetChannelType() == \
                                        tp.interfaces.CHANNEL_TYPE_CONTACT_LIST:
                channel_handle_type, ignore = channel.GetHandle()

                if   channel_handle_type == tp.constants.HANDLE_TYPE_LIST:
                    mapping_pos = MAPPING_CONTACT_LISTS
                elif channel_handle_type == tp.constants.HANDLE_TYPE_GROUP:
                    mapping_pos = MAPPING_GROUPS

                # TODO: also factor in local_pending and remote_pending
                members = channel.GetMembers()

                for member_id in members:
                    # make space for the lists if we don't already have it
                    if member_id not in mapping:
                        mapping[member_id] = [[], []]

                    channel_name = channel._handle.get_name()
                    mapping[member_id][mapping_pos].append(channel_name)

        print "get_contact_channel_membership_info: ", str(mapping)
        return mapping

    def save(self):
        """Writes the current contact list, group, and contact state out to a
        new contacts file.
        """

	print "Connection - save"

        dom_impl = minidom.getDOMImplementation()
        xml_doc = dom_impl.createDocument(None, 'roster', None)
        roster_xml = xml_doc.documentElement

        # add newline for human-readability
        newline_value = xml_doc.createTextNode('\n')
        roster_xml.appendChild(newline_value)

        contact_channels_map = self.get_contact_channel_membership_info()
        for handle_obj, lists_groups in contact_channels_map.items():
            contact_lists, groups = lists_groups

            contact_xml = handle_obj.get_xml(contact_lists, groups)
            roster_xml.appendChild(contact_xml)

            # add newline for human-readability
            newline_value = xml_doc.createTextNode('\n\n')
            roster_xml.appendChild(newline_value)

        
        account_id = self.get_account_id()
        pin.common.save_roster(xml_doc, account_id)

    def checkTID(self, tid):
        if tid[-8:] != '@tlen.pl':
            tid = tid+'@tlen.pl'
        print 'tid: '+tid
        return tid

    def unTID(self, tid):
        if tid[-8:] == '@tlen.pl':
            tid = tid[:-8]
        print 'tid: '+tid
        return tid

    def encodeTlenData(self, data):
        tmp = urllib.urlencode({'x':unicode(data).encode('iso-8859-2')})
        encoded = tmp[2:]
        encoded.replace(' ', '+')
        return encoded

    def decodeTlenData(self, data):
        decoded = urllib.unquote(data.replace('+', ' '))
        return decoded.decode('iso-8859-2').encode('utf8')

    """ EVENTS """
    def lg(self, el):
        print 'ALL > ', el.toXml()
    def err(self, el):
        print 'ERR > ', el

    def _on_roster_received(self, el):
        """ Hooray! That event notifies about contact list downloaded sucesfuly so we can change TP status to CONNECTED :) """
        print 'hurej! mamy liste kontaktow!'
        
        self._xmlized_contact_list = el.toXml()

        self.StatusChanged(tp.constants.CONNECTION_STATUS_CONNECTED,
                        tp.constants.CONNECTION_STATUS_REASON_REQUESTED)

        # create the standard ContactList channels (emitting the NewChannel
        # signal in the process), as described in the Channel specification
        for list_name in self._CONTACT_LIST_NAMES:
            handle = tp.server.Handle(self.get_handle_id(),
                                      tp.constants.HANDLE_TYPE_LIST, list_name)
            print 'list type: ', handle.get_name()
            self._handles[handle.get_type(), handle.get_id()] = handle

            self._channel_get_or_create(tp.interfaces.CHANNEL_TYPE_CONTACT_LIST,
                                        tp.constants.HANDLE_TYPE_LIST,
                                        handle.get_id(), True)

        #FIXME: hack, hack! Remove it when Empathy will support SimplePresence.
        self.factory.sendStanza(self._stanzas['presence'] % ('available'))

        # XXX: this is kinda hacky, since we have to re-parse the file later
        # create all Groups listed in the contacts file
#        group_names = tlen.server.contacts_file_get_groups(self)
#        for group_name in group_names:
#            handle = tp.server.Handle(self.get_handle_id(),
#                                      tp.constants.HANDLE_TYPE_GROUP,
#                                      group_name)
#            self._handles[handle.get_type(), handle.get_id()] = handle
#
#            self._channel_get_or_create(tp.interfaces.CHANNEL_TYPE_CONTACT_LIST,
#                                        tp.constants.HANDLE_TYPE_GROUP,
#                                        handle.get_id(), True)

    def _on_msg_received(self, el):
        print "_on_msg_received"
        #<message from="malcom@tlen.pl">
        #    <body>tresc</body>
        #</message>
        xml = minidom.parseString(el.toXml())
        from_who = xml.getElementsByTagName('message')[0].attributes["from"].value
        print from_who
        message = xml.getElementsByTagName('body')[0].firstChild.nodeValue
        print message
        handle = self.get_handle_id_idempotent(tp.constants.HANDLE_TYPE_CONTACT,
                                  from_who)

        text_channel = self._channel_get_or_create(tp.interfaces.CHANNEL_TYPE_TEXT,
                                    tp.constants.HANDLE_TYPE_CONTACT,
                                    handle[0], True)
        id = self._recv_id
        timestamp = int(time.time())
        type = tp.CHANNEL_TEXT_MESSAGE_TYPE_NORMAL
        print "User %s sent a message to you" % from_who
        print 'handle[0]: ', handle[0]
        text_channel.Received(id, timestamp, handle[0], type, 0, message)
        self._recv_id += 1