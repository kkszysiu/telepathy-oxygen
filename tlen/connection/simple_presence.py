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

from xml.dom import minidom
import dbus.service

import telepathy as tp

import tlen

class TlenPresenceMapping(object):
    """
    wartosci dla tlena:
        available - dostepny
        chat - porozmawiajmy
	dnd - jestem zajety
	away - zaraz wracam
	xa - wroce pozniej
    + 2 specjalne:
        invisible - niewidoczny
	unavailable - niedostepny
    """
    ONLINE = 'available'
    CHAT = 'chat'
    AWAY = 'away'
    BUSY = 'dnd'
    IDLE = 'xa'
    INVISIBLE = 'invisible'
    OFFLINE = 'unavailable'

    to_presence_type = {
            ONLINE:     tp.constants.CONNECTION_PRESENCE_TYPE_AVAILABLE,
            CHAT:       tp.constants.CONNECTION_PRESENCE_TYPE_AVAILABLE,
            AWAY:       tp.constants.CONNECTION_PRESENCE_TYPE_AWAY,
            BUSY:       tp.constants.CONNECTION_PRESENCE_TYPE_BUSY,
            #BUSY:       telepathy.constants.CONNECTION_PRESENCE_TYPE_AWAY,
            IDLE:       tp.constants.CONNECTION_PRESENCE_TYPE_EXTENDED_AWAY,
            INVISIBLE:  tp.constants.CONNECTION_PRESENCE_TYPE_HIDDEN,
            OFFLINE:    tp.constants.CONNECTION_PRESENCE_TYPE_OFFLINE
            }

class SimplePresence(tp.server.ConnectionInterfaceSimplePresence):
    """Presence interface for a Telepathy Connection."""

    def __init__(self):
        tp.server.ConnectionInterfaceSimplePresence.__init__(self)

        dbus_interface = 'org.freedesktop.Telepathy.Connection.Interface.SimplePresence'

        self._implement_property_get(dbus_interface, {'Statuses' : self.get_statuses})

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
        print "GetPresences"
        presences = {}
        for handle_id in contacts:
            print handle_id
            self.check_handle (tp.constants.HANDLE_TYPE_CONTACT, handle_id)

            handle_obj = self._handles[tp.constants.HANDLE_TYPE_CONTACT,
                                       handle_id]
            presences[handle_id] = handle_obj.get_simple_presence()

        print "presences: ", str(presences)
        return presences

    def SetPresence(self, status, message):

        presence = status
        message = message.encode("utf-8")

        print ("Setting Presence to '%s'" % presence)
        print ("Setting Personal message to '%s'" % message)

        print 'my status changed'
        handle = self.self_handle
        if len(message) == 0:
            self.factory.sendStanza(self._stanzas['presence'] % presence)
        else:
            self.factory.sendStanza(self._stanzas['presence_with_status'] % (presence, message))

        presence_type = TlenPresenceMapping.to_presence_type[presence]

        self.PresencesChanged({handle: (presence_type, presence, message)})

        if presence == TlenPresenceMapping.OFFLINE:
            self.Disconnect()

    def get_statuses(self):
        # you get one of these for each status
        # {name:(Type, May_Set_On_Self, Can_Have_Message}
        return {
            TlenPresenceMapping.ONLINE:(
                tp.CONNECTION_PRESENCE_TYPE_AVAILABLE,
                True, True),
            TlenPresenceMapping.CHAT:(
                tp.CONNECTION_PRESENCE_TYPE_AVAILABLE,
                True, True),
            TlenPresenceMapping.AWAY:(
                tp.CONNECTION_PRESENCE_TYPE_AWAY,
                True, True),
            TlenPresenceMapping.BUSY:(
                tp.CONNECTION_PRESENCE_TYPE_BUSY,
                True, True),
            #TlenPresenceMapping.BUSY:(
            #    tp.CONNECTION_PRESENCE_TYPE_AWAY,
            #    True, True),
            TlenPresenceMapping.IDLE:(
                tp.CONNECTION_PRESENCE_TYPE_EXTENDED_AWAY,
                True, True),
            TlenPresenceMapping.INVISIBLE:(
                tp.CONNECTION_PRESENCE_TYPE_HIDDEN,
                True, True),
            TlenPresenceMapping.OFFLINE:(
                tp.CONNECTION_PRESENCE_TYPE_OFFLINE,
                True, True)
        }

    def _on_presence_changed(self, el):
        """
        <presence from='segfault@tlen.pl'><show>available</show><avatar><a type='0' md5='c5404037a7f8e6f44e1a4ce9e0aab02a'/></avatar></presence>
        """
        #TODO: use unlink to clean DOM elements (more at: http://docs.python.org/library/xml.dom.minidom.html)
        #print "_on_presence_changed: "+el.toXml()
        xml = minidom.parseString(el.toXml())
        xml = xml.getElementsByTagName('presence')[0]
        #jesli istnieje atrybut from oznacza to ze jest to presence od kogos
        #jesli presence zawiera atrybut type oznacza to ze jest to status specjalany
        try:
            have_type = True
            presence =  xml.attributes["type"].value
        except:
            have_type = False
        #jesli nie jest to status specjalny to pobierz status normalny
        if have_type != True:
            presence = xml.getElementsByTagName('show')[0]
            presence = presence.firstChild.nodeValue

        try:
            is_self = False
            from_who = xml.attributes["from"].value
        except:
            is_self = True
            to_who = xml.attributes["from"].value
        try:
            have_status = True
            status = xml.getElementsByTagName('status')[0]
            status = status.firstChild.nodeValue
        except:
            have_status = False
        #TODO: w presence sa jeszcze dane awatarow ale to zrobie chyba w oddzielnym evencie

        #jesli sa to prosby o subskrypcje...
        #is self - jesli status jest moj lub ode mnie - true
        if presence == 'subscribe' and is_self == False:
            print 'presence - subscribe from: ', from_who
            #no i tu zaczyna sie straszny hack poniewaz jesli dostaniemy prosce o subskrypcje to kliet zawsze ja zaakceptuje...
            #i wysle prosbe o subskrypcje dla siebie
            self.factory.sendStanza(self._stanzas['subscription_allow'] % from_who)
#        elif presence == 'subscribed' and is_self == False:
#            print 'presence - subscribed from: ', from_who
#            #jesli osoba zasubskrybuje nas to powinnismy i my poprosic ja o jej subskrypcje
#            self.factory.sendStanza(self._stanzas['subscription_ask'] % to_who)
        else:
            if is_self == False:
                if have_status == False:
                    status = ''
                print "not my status, its from %s (presence: %s, status: %s)" % (from_who, presence, status)
                #nie jestem pewien ale tego chyba jeszcze nie moge zaimplementowac poniewaz nie mam pobranej listy kontaktow :/
                handle_id = self.get_handle_id_idempotent(tp.constants.HANDLE_TYPE_CONTACT, from_who)
                print str(handle_id)
                if handle_id[1] != True:
                    handle = self.get_handle_obj(tp.constants.HANDLE_TYPE_CONTACT, handle_id[0])

                    presence_type = TlenPresenceMapping.to_presence_type[presence]

                status = self.decodeTlenData(str(status))
                self.PresencesChanged({handle: (presence_type, presence, status)})