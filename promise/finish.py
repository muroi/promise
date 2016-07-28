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

from cliff import command

from promise import reservation
from promise import utils

LOG = utils.getLogger(__name__)


class FinishReservation(command.Command):

    def get_parser(self, prog_name):
        parser = super(FinishReservation, self).get_parser(prog_name)
        parser.add_argument(
            'reservation_id', metavar='<reservation-id>',
            help='ID of the reservation')
        parser.add_argument(
            '--keep-reserved-instances', default=False,
            help="The flag which promise doesn't delete reserved instances")
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

        flavor_id = parsed_args.reservation_id
        aggregate_name = flavor_id + reservation.RESERVATION_META_DATA
        aggregate = [aggre for aggre in self.nova_client.aggregates.list()
                     if aggre.name == aggregate_name]

        if not aggregate:
            msg = "reservation id %s isn't defined" % flavor_id
            LOG.debug(msg)
            raise Exception(msg)

        aggregate = aggregate[0]
        reserved_hosts = aggregate.hosts

        # get rid of flavor access from the project
        accesses= self.nova_client.flavor_access.list(flavor=flavor_id)
        self.nova_client.flavor_access.remove_tenant_access(flavor_id,
                                                            accesses[0].tenant_id)

        if not parsed_args.keep_reserved_instances:
            reserved_servers = []
            for h in reserved_hosts:
                opts = {
                    'host': h,
                    'all_tenants': True
                    }
                servers = self.nova_client.servers.list(detailed=False,
                                                        search_opts=opts)
                reserved_servers.extend(servers)
                
            LOG.debug('delete servers because of reservation end: %s' %
                      reserved_servers)
            for s in reserved_servers:
                self.nova_client.servers.delete(s)

        LOG.debug('delete flavor %s and host aggregate %s' %
                  (flavor_id, aggregate))
        self.nova_client.flavors.delete(flavor_id)
        for h in reserved_hosts:
            aggregate.remove_host(h)
        aggregate.delete()

        LOG.debug('hosts %s is de-associated' % reserved_hosts)
