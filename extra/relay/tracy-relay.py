#!/usr/bin/env python3
"""Bridge a reverse-connecting Tracy client to a normal Tracy server.

Tracy's transport assumes the client listens and the server dials in. That does not work
when the client runs somewhere nothing can reach it -- a UWP app container on an Xbox, for
instance. Building the client with TRACY_CONNECT_ADDRESS inverts the client half; this
relay inverts the other half, so the unmodified Tracy server still sees something it can
connect to.

    Xbox (client)  --connects-->  :8087  [relay]  :8086  <--connects--  Tracy server

Run it on the same machine as the Tracy server, then point the server at 127.0.0.1.

    python3 tracy-relay.py

Both ports stay open for the life of the process, so either side may connect first and in
any order. Whatever one side says before the other arrives is buffered and delivered on
connection. When either side drops, both are closed and the relay returns to waiting, which
is what the client does anyway in on-demand mode.
"""

import argparse
import socket
import sys
import threading


class Side:
    """One end of the relay: a persistent listener plus the current connection."""

    def __init__(self, name, port):
        self.name = name
        self.conn = None
        self.pending = bytearray()

        self.listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self.listener.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self.listener.bind(("0.0.0.0", port))
        # Room for a few queued redials: the client reconnects every couple of seconds while
        # it waits for a server, and the relay is briefly out of accept() between attempts.
        self.listener.listen(4)
        self.listener.settimeout(0.2)

    def reset(self):
        self.conn = None
        self.pending = bytearray()

    def accept_then_buffer(self, both_ready):
        """Hold a live connection open until the peer shows up.

        A Tracy client that connects before the server exists gives up on the handshake
        after two seconds and redials, so a connection parked here goes stale quickly.
        Drop those and take the next one rather than pairing the server with a corpse.
        """
        while not both_ready.is_set():
            try:
                conn, addr = self.listener.accept()
            except socket.timeout:
                continue
            except OSError:
                return

            conn.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
            print(f"  {self.name} connected from {addr[0]}:{addr[1]}", flush=True)
            self.conn = conn
            self.pending = bytearray()

            if self._buffer_until(conn, both_ready):
                return

            print(f"  {self.name} dropped before the peer arrived; still waiting", flush=True)
            self.conn = None
            conn.close()

    def _buffer_until(self, conn, both_ready):
        """Buffer whatever `conn` says. False if it died before the peer arrived."""
        # NOTE: catch socket.timeout, not TimeoutError -- the two are only the same class
        # on Python 3.10 and newer, and on older versions a read timeout would otherwise
        # look like a dropped connection.
        conn.settimeout(0.2)
        while not both_ready.is_set():
            try:
                data = conn.recv(65536)
            except socket.timeout:
                continue
            except OSError:
                return False
            if not data:
                return False
            self.pending.extend(data)
        try:
            conn.settimeout(None)
        except OSError:
            return False
        return True


def _pump(src, dst, on_close):
    try:
        while True:
            data = src.recv(65536)
            if not data:
                break
            dst.sendall(data)
    except OSError:
        pass
    finally:
        on_close()


def _session(client, server):
    for side in (client, server):
        side.reset()

    both_ready = threading.Event()
    waiting = [
        threading.Thread(target=side.accept_then_buffer, args=(both_ready,), daemon=True)
        for side in (client, server)
    ]
    for t in waiting:
        t.start()

    while client.conn is None or server.conn is None:
        for t in waiting:
            t.join(0.1)
    both_ready.set()
    for t in waiting:
        t.join()

    # A side can go stale in the window between being observed and both_ready being set.
    if client.conn is None or server.conn is None:
        for side in (client, server):
            if side.conn is not None:
                side.conn.close()
                side.conn = None
        print("  lost a side while pairing; retrying", flush=True)
        return

    for src, dst in ((client, server), (server, client)):
        if src.pending:
            print(f"  flushing {len(src.pending)} buffered bytes "
                  f"{src.name} -> {dst.name}", flush=True)
            dst.conn.sendall(bytes(src.pending))

    closing = threading.Event()

    def shutdown():
        if not closing.is_set():
            closing.set()
            for side in (client, server):
                try:
                    side.conn.shutdown(socket.SHUT_RDWR)
                except OSError:
                    pass

    print("  relaying", flush=True)

    pumps = [
        threading.Thread(target=_pump, args=(client.conn, server.conn, shutdown), daemon=True),
        threading.Thread(target=_pump, args=(server.conn, client.conn, shutdown), daemon=True),
    ]
    for t in pumps:
        t.start()
    for t in pumps:
        t.join()

    for side in (client, server):
        side.conn.close()
    print("  session ended", flush=True)


def main():
    parser = argparse.ArgumentParser(description=__doc__,
                                     formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("--client-port", type=int, default=8087,
                        help="port the Tracy client dials out to (default: 8087, "
                             "matching TRACY_CONNECT_PORT)")
    parser.add_argument("--server-port", type=int, default=8086,
                        help="port the Tracy server connects to (default: 8086)")
    args = parser.parse_args()

    client = Side("client", args.client_port)
    server = Side("server", args.server_port)
    print(f"tracy-relay: client :{args.client_port} <-> server :{args.server_port}",
          flush=True)

    try:
        while True:
            print("waiting for both ends...", flush=True)
            _session(client, server)
    except KeyboardInterrupt:
        print("\nstopped", flush=True)
        return 0


if __name__ == "__main__":
    sys.exit(main())
