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
import mimetypes

import telepathy as tp

PROTO_DEFAULT = 'tlen'
ACCOUNT_DEFAULT = 'default@default'

CONTACTS_FILENAME='contacts.xml'
# this is a pseudo-enum
PREFIX_DEFAULT, PREFIX_SAVED, PREFIX_SAVED_PREFERRED = range(3)
DATA_DIR_DEFAULT = '/var/lib/telepathy-pinocchio'
DATA_DIR_SAVED = os.path.join(os.path.expanduser('~'), '.telepathy-pinocchio')
AVATAR_DIR_DEFAULT = os.path.join(DATA_DIR_DEFAULT, 'avatars')
AVATAR_DIR_SAVED = os.path.join(DATA_DIR_SAVED, 'avatars')

CM_TLEN = '.'.join((tp.interfaces.CONNECTION_MANAGER, 'tptlen'))
CM_PINOCCHIO_OBJ = '/' + CM_TLEN.replace('.', '/')

def get_account_dir(prefix, account_id):
    """Get the base account directory for default or saved contacts file, etc.

    Arguments:
    prefix -- PREFIX_DEFAULT to get the unmodified contacts file
              PREFIX_SAVED to get the saved contacts file
    account_id -- escaped account name

    Exceptions:
    ValueError -- invalid account_id or prefix
    """

    print "common.py - get_account_dir"

    dir_result = None

    if   prefix == PREFIX_DEFAULT:
        dir_result = os.path.join(DATA_DIR_DEFAULT, 'accounts', account_id)
    elif prefix == PREFIX_SAVED:
        dir_result = os.path.join(DATA_DIR_SAVED, 'accounts', account_id)
    else:
        raise ValueError, 'invalid contacts file argument'

    return dir_result

def get_contacts_file(account_id, prefix=PREFIX_SAVED_PREFERRED):
    """Returns the absolute path for the contacts file (prepending the account's
    base data dir as necessary). Modified rosters are saved to disk as a
    different name, so this function prefers them over the default file name.
    Note that this method does not check that the final result or its parent
    directories exist, so the caller is still responsible to confirm they exist
    and create them as necessary.

    Arguments:
    account_id -- escaped account name
    prefix -- PREFIX_DEFAULT to get the unmodified contacts file
              PREFIX_SAVED to get the saved contacts file
              PREFIX_SAVED_PREFERRED to get the saved file if it exists, else
                  default

    Returns:
    contacts_file -- absolute path for the contacts file

    Exceptions:
    ValueError -- invalid account_id or prefix
    """

    print "common.py - get_contacts_file"

    # get the sanitized name of the default account if one was not given
    if not account_id:
        raise ValueError, 'an account ID must be provided'

    account_dir_default = get_account_dir(PREFIX_DEFAULT, account_id)
    account_dir_saved = get_account_dir(PREFIX_SAVED, account_id)
    contacts_file_default = os.path.join(account_dir_default, CONTACTS_FILENAME)
    contacts_file_saved = os.path.join(account_dir_saved, CONTACTS_FILENAME)

    contacts_file_final = None

    if   prefix == PREFIX_DEFAULT:
        contacts_file_final = contacts_file_default
    elif prefix == PREFIX_SAVED:
        contacts_file_final = contacts_file_saved
    elif prefix == PREFIX_SAVED_PREFERRED:
        if os.path.isfile(contacts_file_saved):
            contacts_file_final = contacts_file_saved
        else:
            contacts_file_final = contacts_file_default
    else:
        raise ValueError, 'invalid contacts file argument'

    return contacts_file_final

def image_filename_to_mime_type(file_path):
    """Get the MIME type for a given image file. The image's MIME type will be
    determined from the file name, not its content. If the file is not an image,
    it will be treated as an error. This function doesn't check that a file
    exists.

    Arguments:
    file_path -- the local path to an image file for the contact

    Exceptions:
    org.freedesktop.Telepathy.Error.InvalidArgument
    """
    mime_type = mimetypes.guess_type(file_path)[0]
    if mime_type is None:
        tp.errors.InvalidArgument('could not determine image type by filename')
    else:
        type = mime_type.split('/')[0]
        if type != 'image':
            tp.errors.InvalidArgument('file does not seem to be an image '
                                      '(based on its name)')

    return mime_type

def xml_insert_element(xml_doc, parent_node, element_name, element_content,
                       trailer='\n'):
    """Create and fill a new element, and insert it at the end of a parent node.
    This method also inserts a newline after the new element for human
    readability.

    Arguments:
    xml_doc -- minidom Document object of the encompassing document
    parent_node -- minidom Node object
    element_name -- new element's name
    element_contact -- new element's content
    trailer -- text to insert after the new element's end tag (default: '\n')

    Returns:
    element -- the newly-created element Node object
    """

    print "common.py - xml_insert_element"

    element = xml_doc.createElement(element_name)

    element_node = xml_doc.createTextNode(element_content)
    element.appendChild(element_node)

    parent_node.appendChild(element)
    
    # add newline for human-readability
    if trailer:
        trailer_node = xml_doc.createTextNode(trailer)
        parent_node.appendChild(trailer_node)

    return element

def save_roster(xml_doc, account_id):
    """Write the roster XML content to the contacts file for the account.

    Arguments:
    xml_doc -- minidom Document object of the encompassing document
    account_id -- sanitized account ID
    """

    print "common.py - save_roster"

    filename = get_contacts_file(account_id, PREFIX_SAVED)

    # make sure the parent directories exist
    parent_dir = os.path.dirname(filename)
    if not os.path.isdir(parent_dir):
        os.makedirs(parent_dir)

    file = open(filename, 'w')
    file.write(xml_doc.toxml(encoding='utf-8'))
    file.close()
