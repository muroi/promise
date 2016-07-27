#    Copyright 2016 NTT. All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License");
#    you may not use this file except in compliance with the License.
#    You may obtain a copy of the License at
#
#        http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS,
#    WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#    See the License for the specific language governing permissions and
#    limitations under the License.

import logging
import os

from keystoneauth1 import loading
from keystoneauth1 import session
from keystoneclient import client as keystone_client
from novaclient import client as nova_client
from novaclient import exceptions


def getLogger(name):
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)

    return logger


def append_openstack_argument(parser):
    parser.add_argument(
        '--auth_url', metavar='OS_AUTH_URL',
        default=os.environ.get('OS_AUTH_URL'),
        help='authentification url of admin')
    parser.add_argument(
        '--project_id', metavar='OS_PROJECT_ID',
        default=os.environ.get('OS_PROJECT_ID'),
        help='project id of admin')
    parser.add_argument(
        '--username', metavar='OS_USERNAME',
        default=os.environ.get('OS_USERNAME'),
        help='user name of admin')
    parser.add_argument(
        '--password', metavar='OS_PASSWD',
        default=os.environ.get('OS_PASSWD'),
        help='password of admin')
    return parser


def get_session(auth_args):
    """ Return Keystone API session object."""
    loader = loading.get_plugin_loader('password')
    auth = loader.load_from_options(**auth_args)
    sess = session.Session(auth=auth)

    return sess

NOVA_API_VERSION = '2'
KEYSTONE_API_VERSION = '2.0'

def get_nova_openstack_client(auth_args, logger=None):
    session = get_session(auth_args)
    client = nova_client.Client(NOVA_API_VERSION, session=session, logger=logger)
    return client

def get_keystone_openstack_client(auth_args):
    session = get_session(auth_args)
    ks_client = keystone_client.Client(NOVA_API_VERSION, session=session)
    return ks_client


