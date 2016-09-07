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

from promise import utils

LOG = utils.getLogger(__name__)
RESERVATION_META_DATA = 'reservation'

class ReserveInstances(show.ShowOne):

    def get_parser(self, prog_name):
        parser = super(ReserveInstances, self).get_parser(prog_name)
        parser.add_argument(
            '--aggregate-name', default=None,
            type=str, help='aggregation name')
        parser.add_argument(
            'name', metavar='<name>',
            help='name for the flavor')
        parser.add_argument(
            'vcpu', default=1, metavar='<vcpu>',
            help='number of vcpu for the flavor')
        parser.add_argument(
            'ram', default=1024, metavar='<ram>',
            help='Memory in MB for the flavor')
        parser.add_argument(
            'disk', default=30, metavar='<disk>',
            help='size of local disk in GB for the flavor')
        parser.add_argument(
            'instance_number', default=1, metavar='<instance-number>',
            help='number of instances for the reservation')
        parser.add_argument(
            'az', metavar='<availability zone>',
            help='availability of the reservation')
        parser = utils.append_openstack_argument(parser)
        return parser

    def choose_unused_host(self, az, flavor, number, aggregate):
        if aggregate:
            # choose unused hosts from a specific aggregation
            if (hasattr(aggregate, 'metadata') and
                RESERVATION_META_DATA in aggregate.metadata):
                msg = ("specified aggregate: %s is used for reservation %s" %
                       (aggregate.name, aggregate.metadata[RESERVATION_META_DATA]))
                LOG.debug(msg)
                raise Exception(msg)

            candidates = aggregate.hosts
        else:
            # choose unused hosts from non-aggregated hosts
            aggregated_host = []
            for h in self.nova_client.aggregates.list():
                aggregated_host.extend(h.hosts)

            all_hosts = [h.host_name for h in self.nova_client.hosts.list(az)
                         if h.service == 'compute']
            candidates = list(set(all_hosts) - set(aggregated_host))

        LOG.debug('candidates: %s' % candidates)

        hypervisors = [h for h in self.nova_client.hypervisors.list(detailed=True)
                       if (h.service['host'] in candidates and
                           not (h.state == 'down' or h.status == 'disabled'))]
        result = []
        reserved = 0
        # choose hypervisor with greedy algorithm
        for h in hypervisors:
            max_vcpu = h.vcpus / flavor.vcpus
            max_mem = h.memory_mb / flavor.ram
            max_disk = h.local_gb / flavor.disk
            instance_capacity = min(max_vcpu, max_mem, max_disk)
            LOG.debug('hypervisor: %s, instance_capacity: %s, reserved: %s, number: %s' %
                      (h.service['host'], instance_capacity, reserved, number))
            if instance_capacity > 0:
                reserved += instance_capacity
                result.append(h.service['host'])
            if reserved >= number:
                return result

        raise Exception("The reservation request is over capacity.")

    def take_action(self, parsed_args):
        auth_args = {
            'auth_url': parsed_args.auth_url,
            'username': parsed_args.username,
            'password': parsed_args.password,
            'tenant_id': parsed_args.project_id,
            }
        self.nova_client = utils.get_nova_openstack_client(auth_args)

        flavor_detail = {
            'name': parsed_args.name,
            'vcpus': parsed_args.vcpu,
            'ram': parsed_args.ram,
            'disk': parsed_args.disk,
            'is_public': False,
            }
        reserved_flavor = self.nova_client.flavors.create(**flavor_detail)
        extra_specs = {
            "aggregate_instance_extra_specs:" + RESERVATION_META_DATA: \
                reserved_flavor.id
            }
        reserved_flavor.set_keys(extra_specs)
        LOG.debug('reserved flavor id: %s, name: %s' %
                  (reserved_flavor.id, reserved_flavor.name))

        aggregate_name = str(reserved_flavor.id) + RESERVATION_META_DATA
        reserved_aggregate = self.nova_client.aggregates.create(aggregate_name,
                                                                parsed_args.az)
        metadata = {
            RESERVATION_META_DATA: str(reserved_flavor.id)
            }

        original_aggre = utils.get_aggregate_from_name(self.nova_client,
                                                       parsed_args.aggregate_name)
        if original_aggre:
            metadata['original-aggregate'] = original_aggre.name

        self.nova_client.aggregates.set_metadata(reserved_aggregate, metadata)

        available_hosts = self.choose_unused_host(parsed_args.az,
                                                  reserved_flavor,
                                                  int(parsed_args.instance_number),
                                                  original_aggre)
        LOG.debug('available hosts: %s' % available_hosts)

        for h in available_hosts:
            self.nova_client.aggregates.add_host(reserved_aggregate, h)
            if original_aggre:
                original_aggre.remove_host(h)

        columns = ('reservation id', 'aggregate id', 'hosts')
        data = (reserved_flavor.id, reserved_aggregate.id, reserved_aggregate.hosts)
        return (columns, data)
