"""Give an EQ Wave an address when it is wired straight to a computer.

A Wave that asks for DHCP has no address until a server answers, and a computer
has no DHCP server of its own. This module is that server, for one link: it
answers every Wave on the computer's Ethernet adapter, gives the first one
192.168.10.10 (the address equser's config and the Wave's docs assume), and
prints each Wave's hostname and address as it is served.

Standard library only. Set the adapter to a fixed address first (default
192.168.10.2, mask 255.255.255.0), then::

    equser wave-dhcp
    equser wave-dhcp --server-ip 192.168.10.2 --first 192.168.10.10

Runs on Windows and Linux. DHCP's server port is 67: Windows binds it as a
normal user and may ask to allow Python through its firewall; Linux needs
``sudo``.
"""

from __future__ import annotations

import ipaddress
import socket
import struct
import sys
import time
from dataclasses import dataclass

SERVER_PORT = 67
CLIENT_PORT = 68
MAGIC_COOKIE = b'\x63\x82\x53\x63'

BOOTREQUEST = 1
BOOTREPLY = 2

DISCOVER = 1
OFFER = 2
REQUEST = 3
DECLINE = 4
ACK = 5
NAK = 6
RELEASE = 7

OPT_PAD = 0
OPT_SUBNET_MASK = 1
OPT_HOSTNAME = 12
OPT_REQUESTED_IP = 50
OPT_LEASE_TIME = 51
OPT_MESSAGE_TYPE = 53
OPT_SERVER_ID = 54
OPT_END = 255

# BOOTP fixed header: op, htype, hlen, hops, xid, secs, flags, ciaddr, yiaddr,
# siaddr, giaddr, chaddr (16), sname (64), file (128).
_HEADER = struct.Struct('!BBBBIHH4s4s4s4s16s64s128s')

LEASE_SECONDS = 24 * 3600


@dataclass
class Packet:
    """The fields of a DHCP message this server reads or writes."""

    op: int
    xid: int
    flags: int
    ciaddr: bytes
    chaddr: bytes
    options: dict[int, bytes]

    @property
    def message_type(self) -> int | None:
        value = self.options.get(OPT_MESSAGE_TYPE)
        return value[0] if value else None

    @property
    def mac(self) -> str:
        return ':'.join(f'{b:02x}' for b in self.chaddr[:6])

    @property
    def hostname(self) -> str:
        return self.options.get(OPT_HOSTNAME, b'').decode('ascii', 'replace')


def parse(data: bytes) -> Packet | None:
    """Decode a BOOTP/DHCP message, or return None if it is not one."""
    if len(data) < _HEADER.size + len(MAGIC_COOKIE):
        return None
    fields = _HEADER.unpack_from(data)
    op, _htype, _hlen, _hops, xid, _secs, flags, ciaddr = fields[:8]
    chaddr = fields[11]
    if data[_HEADER.size:_HEADER.size + 4] != MAGIC_COOKIE:
        return None
    options: dict[int, bytes] = {}
    i = _HEADER.size + 4
    while i < len(data):
        code = data[i]
        if code == OPT_END:
            break
        if code == OPT_PAD:
            i += 1
            continue
        if i + 1 >= len(data):
            break
        length = data[i + 1]
        options[code] = data[i + 2:i + 2 + length]
        i += 2 + length
    return Packet(op, xid, flags, ciaddr, chaddr, options)


def build_reply(request: Packet, message_type: int, yiaddr: str, server_ip: str,
                netmask: str, lease_seconds: int = LEASE_SECONDS) -> bytes:
    """Encode an OFFER, ACK or NAK answering ``request``."""
    header = _HEADER.pack(
        BOOTREPLY, 1, 6, 0, request.xid, 0, request.flags,
        request.ciaddr if message_type == ACK else b'\0' * 4,
        socket.inet_aton(yiaddr) if message_type != NAK else b'\0' * 4,
        socket.inet_aton(server_ip), b'\0' * 4, request.chaddr, b'', b'')
    opts = bytes([OPT_MESSAGE_TYPE, 1, message_type])
    opts += bytes([OPT_SERVER_ID, 4]) + socket.inet_aton(server_ip)
    if message_type != NAK:
        opts += bytes([OPT_LEASE_TIME, 4]) + struct.pack('!I', lease_seconds)
        opts += bytes([OPT_SUBNET_MASK, 4]) + socket.inet_aton(netmask)
    return header + MAGIC_COOKIE + opts + bytes([OPT_END])


class Leases:
    """Addresses handed out on this link, one per MAC, from ``first`` upward."""

    def __init__(self, first: str, server_ip: str, netmask: str):
        self.network = ipaddress.IPv4Network(f'{server_ip}/{netmask}', strict=False)
        self.next = ipaddress.IPv4Address(first)
        if self.next not in self.network:
            raise ValueError(f'{first} is not on {self.network}')
        self.server = ipaddress.IPv4Address(server_ip)
        self.by_mac: dict[str, str] = {}

    def address_for(self, mac: str) -> str:
        if mac not in self.by_mac:
            while self.next == self.server:
                self.next += 1
            if self.next not in self.network or self.next == self.network.broadcast_address:
                raise RuntimeError(f'no addresses left on {self.network}')
            self.by_mac[mac] = str(self.next)
            self.next += 1
        return self.by_mac[mac]


def answer(packet: Packet, leases: Leases, server_ip: str, netmask: str) -> bytes | None:
    """The reply to one client message, or None when it needs none."""
    if packet.op != BOOTREQUEST:
        return None
    kind = packet.message_type
    if kind == DISCOVER:
        return build_reply(packet, OFFER, leases.address_for(packet.mac), server_ip, netmask)
    if kind == REQUEST:
        server_id = packet.options.get(OPT_SERVER_ID)
        if server_id is not None and server_id != socket.inet_aton(server_ip):
            return None  # the client chose another server
        address = leases.address_for(packet.mac)
        wanted = packet.options.get(OPT_REQUESTED_IP) or packet.ciaddr
        if wanted not in (b'\0' * 4, socket.inet_aton(address)):
            return build_reply(packet, NAK, address, server_ip, netmask)
        return build_reply(packet, ACK, address, server_ip, netmask)
    return None


def serve(server_ip: str = '192.168.10.2', first: str = '192.168.10.10',
          netmask: str = '255.255.255.0') -> int:
    """Answer DHCP on the adapter that holds ``server_ip`` until interrupted."""
    leases = Leases(first, server_ip, netmask)
    sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM, socket.IPPROTO_UDP)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_BROADCAST, 1)
    try:
        # Windows delivers broadcasts to a socket bound to the adapter's
        # address, and sends its broadcasts out that adapter.  Linux delivers
        # them only to a wildcard bind, so there the adapter is chosen by name.
        if sys.platform == 'win32':
            sock.bind((server_ip, SERVER_PORT))
        elif sys.platform.startswith('linux'):
            sock.bind(('', SERVER_PORT))
            device = _linux_device_for(server_ip)
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_BINDTODEVICE, device.encode())
        else:
            print(f'Error: wave-dhcp runs on Windows and Linux, not {sys.platform}.',
                  file=sys.stderr)
            return 1
    except PermissionError:
        print('Error: DHCP needs port 67; run this with sudo.', file=sys.stderr)
        return 1
    except OSError as exc:
        print(f'Error: cannot serve on {server_ip}: {exc}. Is the adapter set to '
              f'{server_ip}/{netmask}?', file=sys.stderr)
        return 1

    print(f'Serving DHCP on {server_ip}; connect the Wave (Ctrl+C to stop).', flush=True)
    served: dict[str, str] = {}
    try:
        while True:
            data, _ = sock.recvfrom(1500)
            packet = parse(data)
            if packet is None:
                continue
            reply = answer(packet, leases, server_ip, netmask)
            if reply is None:
                continue
            sock.sendto(reply, ('255.255.255.255', CLIENT_PORT))
            if packet.message_type == REQUEST and reply[_HEADER.size + 6] == ACK:
                address = leases.by_mac[packet.mac]
                if served.get(packet.mac) != address:
                    served[packet.mac] = address
                    print(f'{time.strftime("%H:%M:%S")}  {packet.hostname or "(no hostname)"}'
                          f'  {packet.mac}  {address}', flush=True)
    except KeyboardInterrupt:
        return 0
    except OSError as exc:
        print(f'Stopped: the adapter no longer has {server_ip} ({exc}).', file=sys.stderr)
        return 1
    finally:
        sock.close()


def _linux_device_for(server_ip: str) -> str:
    """The name of the Linux interface that holds ``server_ip``."""
    import fcntl

    for _, name in socket.if_nameindex():
        probe = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        try:
            raw = fcntl.ioctl(probe.fileno(), 0x8915,  # SIOCGIFADDR
                              struct.pack('256s', name.encode()[:15]))
            if socket.inet_ntoa(raw[20:24]) == server_ip:
                return name
        except OSError:
            pass
        finally:
            probe.close()
    raise OSError(f'no interface holds {server_ip}')
