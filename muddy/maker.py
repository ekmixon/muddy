from pprint import pprint
from datetime import datetime
import re

from muddy.constants import DOMAIN_NAME_REGEX, HTTP_URL_REGEX, URN_URL_REGEX
from muddy.exceptions import InputException
from muddy.models import MatchType, IPVersion, Protocol, Direction



def make_support_info(mud_version, mud_url, last_update, cache_validity,
                      is_supported, masa_server, system_info, mfg_name, documentation, model_name):
    support_info = {}

    if mfg_name is not None:
        support_info['mfg-name'] = mfg_name
    if model_name is not None:
        support_info['model-name'] = model_name
    if masa_server is not None:
        support_info["masa-server"] = masa_server

    support_info['mud-version'] = int(mud_version)
    support_info['mud-url'] = mud_url
    support_info['last-update'] = last_update if last_update is not None else datetime.now().strftime(
        '%Y-%m-%dT%H:%M:%S%z')
    support_info['cache-validity'] = int(cache_validity)
    support_info['is-supported'] = is_supported
    support_info['systeminfo'] = system_info
    support_info['documentation'] = documentation

    return support_info


def make_port_range(dir_init, source_port, destination_port):
    port_range = {}

    if dir_init is not None and dir_init in ['to-device', 'from-device']:
        port_range['ietf-mud:direction-initiated'] = dir_init

    if source_port is not None:
        port_range['source-port'] = {
            'operator': 'eq',
            'port': int(source_port)
        }
    if destination_port is not None:
        port_range['destination-port'] = {
            'operator': 'eq',
            'port': int(destination_port)
        }

    return port_range

def make_acldns_match(domain, direction):
    acldns_match = {}

    if not re.match(DOMAIN_NAME_REGEX, domain):
        raise InputException(f"Not a domain name: {domain}")
    key = "ietf-acldns:src-dnsname" if direction is Direction.TO_DEVICE else \
             "ietf-acldns:dst-dnsname" if direction is Direction.FROM_DEVICE
    if key:
        acldns_match[key] = domain
    else:
        raise InputException(f"direction is not valid: {direction}")


def make_sub_ace(sub_ace_name, protocol_direction, target_url, protocol, local_port, remote_port, match_type,
                 direction_initiated, ip_version):
    if ip_version is IPVersion.IPV4:
        ip_version = 'ipv4'
    elif ip_version is IPVersion.IPV6:
        ip_version = 'ipv6'
    else:
        raise InputException('initiation_direction is not valid: {}' % protocol_direction)
    match = {}
    if len(target_url) > 140:
        raise InputException('target url is to long: {}' % target_url)
    cloud_ipv4_entry = None
    source_port = None
    destination_port = None

    make_acldns_match(target_url, protocol_direction) if match_type is MatchType.IS_CLOUD

    elif match_type is MatchType.IS_CONTROLLER:
        if not (re.match(HTTP_URL_REGEX, target_url) or re.match(URN_URL_REGEX, target_url)):
            raise InputException('Not a valid URL: {}' % target_url)
        match['ietf-mud:mud'] = {'controller': target_url}
    elif match_type is MatchType.IS_MY_CONTROLLER:
        match['ietf-mud:mud'] = {'my-controller': [None]}
    elif match_type is MatchType.IS_MFG:
        if not re.match(DOMAIN_NAME_REGEX, target_url):
            raise InputException('Not a domain name: {}' % target_url)
        match['ietf-mud:mud'] = {'manufacturer': target_url}
    elif match_type is MatchType.IS_MYMFG:
        match['ietf-mud:mud'] = {'same-manufacturer': [None]}
    else:
        raise InputError('match_type is not valid: ' % match_type)
    if protocol is Protocols.ANY and cloud_ipv4_entry:
        match['ipv4'] = cloud_ipv4_entry
    else:
        if protocol_direction is Direction.TO_DEVICE:
            source_port = remote_port
            destination_port = local_port
        elif protocol_direction is Direction.FROM_DEVICE:
            source_port = local_port
            destination_port = remote_port
        if protocol is Protocols.TCP:
            match['ipv4'] = {'protocol': 6}
            match['tcp'] = make_port_range(direction_initiated, source_port, destination_port)
        elif protocol is Protocols.UDP:
            match['ipv4'] = {'protocol': 17}
        else:
            raise InputException('protocol is not valid: {}' % protocol)
        if cloud_ipv4_entry:
            match[ip_version].update(cloud_ipv4_entry)
    return {'name': sub_ace_name, 'matches': match}


def make_ace(ace_name, protocol_directions, target_url, protocol, local_ports, remote_ports, match_type,
             direction_initiateds, ip_version):
    if protocol_directions is Directions.TO_DEVICE:
        sub_ace_name = ace_name + '{}-todev'
    else:
        sub_ace_name = ace_name + '{}-frdev'
    ace = []
    for i in range(len(protocol)):
        ace.append(
            make_sub_ace(sub_ace_name.format(i), protocol_directions[i], target_url, protocol, local_ports[i],
                         remote_ports[i],
                         match_type, direction_initiateds, ip_version))


if __name__ == '__main__':
    pprint(make_support_info(1, 'https://test/123', None, 48, True, None, 'aa', 'CIRA', 'https://doc.ca', '123'))
    pprint(make_support_info(1, 'https://test/123', None, 48, True, None, 'aa', None, 'https://doc.ca', '123'))
    pprint(make_port_range('to-device', 888, 80))
    pprint(
        make_sub_ace('ace', Directions.TO_DEVICE, 'www.google.com', Protocols.UDP, 888, 80, MatchType.IS_CLOUD,
                     'to-device'))
