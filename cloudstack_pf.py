#!/usr/bin/python
# -*- coding: utf-8 -*-
#
# (c) 2015, René Moser <mail@renemoser.net>
#
# This file is part of Ansible
#
# Ansible is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
# Ansible is distributed in the hope that it will be useful,
# but WITHOUT ANY WARRANTY; without even the implied warranty of
# MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the
# GNU General Public License for more details.
#
# You should have received a copy of the GNU General Public License
# along with Ansible. If not, see <http://www.gnu.org/licenses/>.

DOCUMENTATION = '''
module: cloudstack_pf
short_description: Create and remove port forwarding rules on Apache CloudStack based clouds.
description:
    - Manage port forwarding rules on Apache CloudStack, Citrix CloudPlatform
    - Credentials can be stored locally in C($HOME/.cloudstack.ini) instead of using C(api_url), C(api_key), C(api_secret), C(api_http_method), see https://github.com/exoscale/cs on which this module depends on.
    - This module supports check mode.
version_added: '1.9'
options:
  ip_address:
    description:
      - Public IP address the rule is assigned to.
    required: true
    default: null
    aliases: []
  state:
    description:
      - State of the port forwarding rule.
    required: false
    default: 'present'
    choices: [ 'present', 'absent' ]
    aliases: []
  protocol:
    description:
      - Protocol of the port forwarding rule.
    required: false
    default: 'tcp'
    choices: [ 'tcp', 'udp' ]
    aliases: []
  public_start_port
    description:
      - Start public port for this rule.
    required: true
    default: null
    aliases: []
  public_end_port
    description:
      - End public port for this rule.
    required: true
    default: null
    aliases: []
  private_start_port
    description:
      - Start private port for this rule.
    required: true
    default: null
    aliases: []
  private_end_port
    description:
      - End private port for this rule.
    required: true
    default: null
    aliases: []
  open_firewall:
    description:
      - Whether the firewall rule for public port should be created.
    required: false
    default: false
    aliases: []
  vm_guest_ip:
    description:
      - VM guest NIC secondary IP address for the port forwarding rule.
    required: false
    default: false
    aliases: []
  project:
    description:
      - Name of the project the VM is located in.
    required: false
    default: null
    aliases: []
  api_key:
    description:
      - API key of the CloudStack API.
    required: false
    default: null
    aliases: []
  api_secret:
    description:
      - Secret key of the CloudStack API.
    required: false
    default: null
    aliases: []
  api_url:
    description:
      - URL of the CloudStack API e.g. https://cloud.example.com/client/api.
    required: false
    default: null
    aliases: []
  api_http_method:
    description:
      - HTTP method used.
    required: false
    default: 'get'
    aliases: []
author: René Moser
requirements: [ 'python library C(cs)' ]
'''

EXAMPLES = '''
---

'''
import sys

try:
    from cs import CloudStack, CloudStackException, read_config
except ImportError:
    print("failed=True " + \
        "msg='python library cs required: pip install cs'")
    sys.exit(1)


class AnsibleCloudStack:

    def __init__(self, module):
        self.module = module
        self._connect()

        self.project_id = None
        self.ip_address_id = None
        self.zone_id = None
        self.vm_id = None
        self.os_type_id = None


    def _connect(self):
        api_key = self.module.params.get('api_key')
        api_secret = self.module.params.get('secret_key')
        api_url = self.module.params.get('api_url')
        api_http_method = self.module.params.get('api_http_method')

        if api_key and api_secret and api_url:
            self.cs = CloudStack(
                endpoint=api_url,
                key=api_key,
                secret=api_secret,
                method=api_http_method
                )
        else:
            self.cs = CloudStack(**read_config())


    def get_project_id(self):
        if self.project_id:
            return self.project_id

        project = self.module.params.get('project')
        if not project:
            return None

        projects = self.cs.listProjects()
        if projects:
            for p in projects['project']:
                if project in [ p['name'], p['displaytext'], p['id'] ]:
                    self.project_id = p[id]
                    return self.project_id
        self.module.fail_json(msg="project '%s' not found" % project)


    def get_ip_address_id(self):
        if self.ip_address_id:
            return self.ip_address_id

        args = {}
        args['ipaddress'] = self.module.params.get('ip_address')
        args['projectid'] = self.get_project_id()
        ip_addresses = self.cs.listPublicIpAddresses(**args)

        if not ip_addresses:
            self.module.fail_json(msg="ip address '%s' not found" % args['ipaddress'])

        self.ip_address_id = ip_addresses['publicipaddress'][0]['id']
        return self.ip_address_id


    def get_vm_id(self):
        if self.vm_id:
            return self.vm_id

        args = {}
        vm = self.module.params.get('vm')
        args['projectid'] = self.get_project_id()
        vms = self.cs.listVirtualMachines(**args)
        if vms:
            for v in vms['virtualmachine']:
                if vm in [ v['name'], v['id'] ]:
                    self.vm_id = v['id']
                    return self.vm_id
        self.module.fail_json(msg="Virtual machine '%s' not found" % vm)


    def get_zone_id(self):
        if self.zone_id:
            return self.zone_id

        zone = self.module.params.get('zone')
        zones = self.cs.listZones()

        # use the first zone if no zone param
        if not zone:
            self.zone_id = zones['zone'][0]['id']
            return self.zone_id

        if zones:
            for z in zones['zone']:
                if zone in [ z['name'], z['id'] ]:
                    self.zone_id = z['id']
                    return self.zone_id
        self.module.fail_json(msg="zone '%s' not found" % zone)


    def get_os_type_id(self):
        if self.os_type_id:
            return self.os_type_id

        os_type = self.module.params.get('os_type')
        if not os_type:
            return None

        os_types = self.cs.listOsTypes()
        if os_types:
            for o in os_types['ostype']:
                if os_type in [ o['description'], o['id'] ]:
                    self.os_type_id = o['id']
                    return self.os_type_id
        self.module.fail_json(msg="OS type '%s' not found" % os_type)


    def _poll_job(self, job, key):
        if 'jobid' in job:
            while True:
                res = self.cs.queryAsyncJobResult(jobid=job['jobid'])
                if res['jobstatus'] != 0:
                    if 'jobresult' in res and key in res['jobresult']:
                        job = res['jobresult'][key]
                    break
                time.sleep(2)
        return job


class AnsibleCloudStackPortforwarding(AnsibleCloudStack):

    def __init__(self, module):
        AnsibleCloudStack.__init__(self, module)
        self.result = {
            'changed': False,
        }


    def get_portforwarding_rule(self):
        protocol = self.module.params.get('protocol')
        public_start_port = self.module.params.get('public_start_port')
        public_end_port = self.module.params.get('public_end_port')
        private_start_port = self.module.params.get('private_start_port')
        private_end_port = self.module.params.get('private_end_port')

        args = {}
        args['ipaddressid'] = self.get_ip_address_id()
        args['projectid'] = self.get_project_id()
        portforwarding_rules = self.cs.listPortForwardingRules(**args)

        if portforwarding_rules and 'portforwardingrule' in portforwarding_rules:
            for rule in portforwarding_rules['portforwardingrule']:
                if protocol == rule['protocol'] \
                    and public_start_port == int(rule['publicport']) \
                    and public_end_port == int(rule['publicendport']) \
                    and private_start_port == int(rule['privateport']) \
                    and private_end_port == int(rule['privateendport']):
                    return rule
        return None


    def _tcp_udp_match(self, rule, protocol, public_start_port, public_end_port, private_start_port, private_end_port):
        return protocol in ['tcp', 'udp'] \
            and protocol == rule['protocol'] \
            and public_start_port == int(rule['publicport']) \
            and public_end_port == int(rule['publicendport']) \
            and private_start_port == int(rule['privateport']) \
            and private_end_port == int(rule['privateendport'])


    def create_portforwarding_rule(self, portforwarding_rule):
        if not portforwarding_rule:
            self.result['changed'] = True
            args = {}
            args['protocol'] = self.module.params.get('protocol')
            args['publicport'] = self.module.params.get('public_start_port')
            args['publicendport'] = self.module.params.get('public_end_port')
            args['privateport'] = self.module.params.get('private_start_port')
            args['privateendport'] = self.module.params.get('private_end_port')

            args['ipaddressid'] = self.get_ip_address_id()
            args['openfirewall'] = self.module.params.get('open_firewall')
            args['vmguestip'] = self.module.params.get('vm_guest_ip')
            args['virtualmachineid'] = self.get_vm_id()
            if not self.module.check_mode:
                portforwarding_rule = self.cs.createPortForwardingRule(**args)

        return portforwarding_rule


    def remove_portforwarding_rule(self, portforwarding_rule):
        if portforwarding_rule:
            self.result['changed'] = True
            args = {}
            args['id'] = portforwarding_rule['id']

            if not self.module.check_mode:
                res = self.cs.deletePortForwardingRule(**args)

        return portforwarding_rule


    def get_result(self, portforwarding_rule):
        return self.result


def main():
    module = AnsibleModule(
        argument_spec = dict(
            ip_address = dict(required=True, default=None),
            protocol = dict(choices=['tcp', 'udp'], default='tcp'),
            public_start_port = dict(type='int', required=True, default=None),
            public_end_port = dict(type='int', required=True, default=None),
            private_start_port = dict(type='int', required=True, default=None),
            private_end_port = dict(type='int', required=True, default=None),
            state = dict(choices=['present', 'absent'], default='present'),
            open_firewall = dict(choices=BOOLEANS, default=False),
            vm_guest_ip = dict(default=None),
            vm = dict(required=True, default=None),
            project = dict(default=None),
            api_key = dict(default=None),
            api_secret = dict(default=None),
            api_url = dict(default=None),
            api_http_method = dict(default='get'),
        ),
        supports_check_mode=True
    )

    try:
        acs_pf = AnsibleCloudStackPortforwarding(module)
        pf_rule = acs_pf.get_portforwarding_rule()

        state = module.params.get('state')
        if state in ['absent']:
            pf_rule = acs_pf.remove_portforwarding_rule(pf_rule)
        else:
            pf_rule = acs_pf.create_portforwarding_rule(pf_rule)

        result = acs_pf.get_result(pf_rule)

    except CloudStackException, e:
        module.fail_json(msg='CloudStackException: %s' % str(e))

    module.exit_json(**result)

# import module snippets
from ansible.module_utils.basic import *
main()
