"""Tests for the one-link DHCP server a Wave wired to a computer uses."""

import socket
import struct

from equser import wave_dhcp as d

SERVER = '192.168.10.2'
MASK = '255.255.255.0'


def client_message(kind, mac=b'\x00\x1a\xb6\x01\x02\x03', hostname=b'eqw-1a2b3c4d',
                   requested=None, server_id=None, xid=0x1234ABCD):
    """A client message laid out the way a DHCP client sends it."""
    header = struct.pack('!BBBBIHH4s4s4s4s16s64s128s', d.BOOTREQUEST, 1, 6, 0, xid, 0,
                         0x8000, b'\0' * 4, b'\0' * 4, b'\0' * 4, b'\0' * 4,
                         mac + b'\0' * 10, b'', b'')
    opts = bytes([d.OPT_MESSAGE_TYPE, 1, kind, d.OPT_HOSTNAME, len(hostname)]) + hostname
    if requested:
        opts += bytes([d.OPT_REQUESTED_IP, 4]) + socket.inet_aton(requested)
    if server_id:
        opts += bytes([d.OPT_SERVER_ID, 4]) + socket.inet_aton(server_id)
    return header + d.MAGIC_COOKIE + opts + bytes([d.OPT_END])


def reply_to(message, leases):
    raw = d.answer(d.parse(message), leases, SERVER, MASK)
    return None if raw is None else d.parse(raw), raw


def test_discover_is_offered_the_first_address():
    leases = d.Leases('192.168.10.10', SERVER, MASK)
    offer, raw = reply_to(client_message(d.DISCOVER), leases)
    assert offer.message_type == d.OFFER
    assert offer.xid == 0x1234ABCD
    assert raw[16:20] == socket.inet_aton('192.168.10.10')  # yiaddr
    assert offer.options[d.OPT_SERVER_ID] == socket.inet_aton(SERVER)
    assert offer.options[d.OPT_SUBNET_MASK] == socket.inet_aton(MASK)
    assert struct.unpack('!I', offer.options[d.OPT_LEASE_TIME])[0] == d.LEASE_SECONDS


def test_request_for_the_offer_is_acked():
    leases = d.Leases('192.168.10.10', SERVER, MASK)
    reply_to(client_message(d.DISCOVER), leases)
    ack, _ = reply_to(client_message(d.REQUEST, requested='192.168.10.10',
                                     server_id=SERVER), leases)
    assert ack.message_type == d.ACK


def test_request_for_another_address_is_refused():
    leases = d.Leases('192.168.10.10', SERVER, MASK)
    nak, _ = reply_to(client_message(d.REQUEST, requested='192.168.10.50'), leases)
    assert nak.message_type == d.NAK


def test_request_to_another_server_gets_no_reply():
    leases = d.Leases('192.168.10.10', SERVER, MASK)
    reply, _ = reply_to(client_message(d.REQUEST, requested='192.168.10.10',
                                       server_id='192.168.10.3'), leases)
    assert reply is None


def test_each_wave_keeps_its_own_address():
    leases = d.Leases('192.168.10.10', SERVER, MASK)
    assert leases.address_for('aa') == '192.168.10.10'
    assert leases.address_for('bb') == '192.168.10.11'
    assert leases.address_for('aa') == '192.168.10.10'


def test_the_server_address_is_never_handed_out():
    leases = d.Leases('192.168.10.2', SERVER, MASK)
    assert leases.address_for('aa') == '192.168.10.3'


def test_hostname_and_mac_are_read():
    packet = d.parse(client_message(d.DISCOVER))
    assert packet.hostname == 'eqw-1a2b3c4d'
    assert packet.mac == '00:1a:b6:01:02:03'


def test_non_dhcp_traffic_is_ignored():
    assert d.parse(b'\0' * 100) is None
