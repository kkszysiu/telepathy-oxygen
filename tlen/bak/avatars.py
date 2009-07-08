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

import mimetypes
import dbus.service

import telepathy as tp

import pinocchio as pin

class Avatars(tp.server.ConnectionInterfaceAvatars):
    """Avatars interface for a Telepathy Connection."""

    def __init__(self):
        tp.server.ConnectionInterfaceAvatars.__init__(self)

    def GetAvatarRequirements(self):
        """Returns the required format of avatars for this connection.

        Returns:
        mime_types -- list of supported MIME types
        img_width_min -- minimum image width (pixels)
        img_height_min -- minimum image height (pixels)
        img_width_max -- maximum image width (pixels); 0 for no limit
        img_height_max -- maximum image height (pixels); 0 for no limit
        img_size_max -- maximum image size (bytes); 0 for no limit

        Exceptions:
        org.freedesktop.Telepathy.Error.Disconnected
        org.freedesktop.Telepathy.Error.NetworkError
        org.freedesktop.Telepathy.Error.PermissionDenied
        org.freedesktop.Telepathy.Error.NotAvailable
        """
        mime_types = ['image/gif', 'image/jpeg', 'image/png']
        img_width_min = 1
        img_height_min = 1
        # 0 == no limit
        img_width_max = 0
        img_height_max = 0
        img_size_max = 0

        return (mime_types, img_width_min, img_height_min, img_width_max,
                img_height_max, img_size_max)

    def GetKnownAvatarTokens(self, contact_handles):
        """Returns the tokens for the avatars on this connection.

        Returns:
        token_map -- dictionary mapping contact handles to avatar tokens
                     (strings)

        Exceptions:
        org.freedesktop.Telepathy.Error.Disconnected
        org.freedesktop.Telepathy.Error.NetworkError
        org.freedesktop.Telepathy.Error.InvalidArgument
        org.freedesktop.Telepathy.Error.PermissionDenied
        org.freedesktop.Telepathy.Error.NotAvailable
        """
        token_map = {}
        for handle_id in contact_handles:
            if (tp.constants.HANDLE_TYPE_CONTACT, handle_id) in self._handles:
                handle_obj = self._handles[tp.constants.HANDLE_TYPE_CONTACT,
                                           handle_id]

                token_map[handle_obj.get_id()] = handle_obj.get_avatar_token()

        return token_map

    def RequestAvatars(self, contacts):
        """Request avatars for the given contacts (by handle ID).

        Exceptions:
        org.freedesktop.Telepathy.Error.Disconnected
        org.freedesktop.Telepathy.Error.InvalidHandle
        """
        # make sure all these IDs are valid before we proceed
        for handle_id in contacts:
            self.check_handle (tp.constants.HANDLE_TYPE_CONTACT,
                               handle_id)
            
        for handle_id in contacts:
            handle_obj = self._handles[tp.constants.HANDLE_TYPE_CONTACT,
                                       handle_id]

            # only send the Updated and Retrieved signals if the contact has an
            # avatar, in accordance to the spec
            avatar_token = handle_obj.get_avatar_token()
            if avatar_token:
                avatar_bin = handle_obj.get_avatar_bin()
                avatar_mime = handle_obj.get_avatar_mime()

                if handle_obj._last_avatar_token_published != avatar_token:
                    self.AvatarUpdated(handle_id, avatar_token)
                    handle_obj._last_avatar_token_published = avatar_token

                self.AvatarRetrieved(handle_id, avatar_token,
                                     handle_obj.get_avatar_bin(),
                                     handle_obj.get_avatar_mime())

    @dbus.service.method(tp.interfaces.CONNECTION_INTERFACE_AVATARS,
                         in_signature='us', out_signature='')
    def set_avatar(self, handle_id, avatar_path):
        """Set the avatar for the given contact (something a regular protocol
        would not allow). The image's MIME type will be determined from the file
        name, not its content.

        Arguments:
        handle_id -- a contact handle
        avatar_path -- the local path to an image file for the contact

        Exceptions:
        org.freedesktop.Telepathy.Error.Disconnected
        org.freedesktop.Telepathy.Error.InvalidArgument
        org.freedesktop.Telepathy.Error.InvalidHandle
        """
        self.check_connected()
        self.check_handle(tp.constants.HANDLE_TYPE_CONTACT, handle_id)

        # FIXME: check that the avatar meets the requirements

        handle_obj = self._handles[tp.constants.HANDLE_TYPE_CONTACT, handle_id]

        # will raise tp.errors.InvalidArgument if it's not an image filename
        pin.common.image_filename_to_mime_type(avatar_path)

        handle_obj.set_avatar(avatar_path)
        self.save()
