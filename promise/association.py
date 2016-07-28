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

from cliff import show
from novaclient import exceptions as nova_exception

from promise import utils

LOG = utils.getLogger(__name__)

class AssociateProjects(show.ShowOne):

    def get_parser(self, prog_name):
        parser = super(AssociateProjects, self).get_parser(prog_name)
        parser.add_argument(
            'reservation_id', metavar='<reservation id>',
            help='ID of the reservation')
        parser.add_argument(
            'project_id', metavar='<project id>',
            help='ID of project using the reservation')
        parser = utils.append_openstack_argument(parser)
        return parser

    def take_action(self, parsed_args):
        auth_args = {
            'auth_url': parsed_args.auth_url,
            'username': parsed_args.username,
            'password': parsed_args.password,
            'tenant_id': parsed_args.project_id,
            }
        self.nova_client = utils.get_nova_openstack_client(auth_args)

        # promise uses flavor id as a reservation id
        flavor_id = parsed_args.reservation_id

        try:
            self.nova_client.flavors.get(flavor_id)
        except nova_exception.NotFound:
            msg = "reservation id %s doesn't exist." % flavor_id
            LOG.info(msg)
            raise Exception(msg)

        association = self.nova_client.flavor_access.add_tenant_access(flavor_id,
                                                                       parsed_args.project_id)
        columns = ('reservation id', 'associated project')
        data = (flavor_id, parsed_args.project_id)

        return (columns, data)
