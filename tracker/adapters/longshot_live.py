"""Longshot 3.0 control protocol 1. Read-only status and explicit flag subscriptions."""
import json
import math
import socket
import struct
import os
from contextlib import contextmanager


def number(value):
    return type(value) in (float, int) and math.isfinite(value)


class LongshotReader:
    def __init__(self):
        self.identity = None
        self.previous = None
        self.distance = 0.0

    @contextmanager
    def connect(self, path, expected_exe=None):
        if os.name == 'nt':
            from windows_native import NamedPipe
            with NamedPipe(path, expected_exe) as pipe:
                yield pipe, pipe, pipe.identity
        else:
            with socket.socket(socket.AF_UNIX, socket.SOCK_STREAM) as sock:
                sock.settimeout(2)
                sock.connect(str(path))
                pid, uid, _ = struct.unpack('3i', sock.getsockopt(socket.SOL_SOCKET, socket.SO_PEERCRED, 12))
                if uid != os.getuid(): raise ValueError('Longshot socket belongs to another user')
                with sock.makefile('rb') as stream:
                    yield sock, stream, (pid, path.stat().st_ino)

    def read_metrics(self, path, watch=None, expected_exe=None):
        try:
            with self.connect(path, expected_exe) as (sock, stream, identity):
                watch = watch or {}
                if len(watch) > 64: raise ValueError('Too many Longshot watched signals')
                def request(command):
                    sock.sendall((json.dumps(command)+'\n').encode())
                def receive():
                    raw = stream.readline(65537)
                    if len(raw) > 65536 or not raw.endswith(b'\n'): raise ValueError('Invalid Longshot response size')
                    result = json.loads(raw)
                    if not isinstance(result, dict): raise ValueError('Invalid Longshot response')
                    return result
                request({'id':1, 'cmd':'status'})
                reply = receive()
                self.validate(reply)
                metrics = {}
                try:
                    metrics = self.consume(reply, identity)
                except ValueError:
                    self.previous = None
                    if not watch: raise
                if watch:
                    request({'id':2, 'cmd':'subscribe', 'events':['oot'], 'every':60,
                             'flags':list(watch.values()), 'changes':False})
                    ack = receive()
                    if ack.get('id') != 2 or ack.get('ok') is not True: raise ValueError('Longshot flag subscription refused')
                    metrics.update(self.flag_metrics(receive(), watch))
                if not metrics: raise ValueError('Waiting for readable Longshot progress')
                return metrics
        except (FileNotFoundError, ConnectionRefusedError) as error:
            self.previous = None
            raise ValueError('Waiting for Longshot — launch the game through Steam') from error
        except (OSError, ValueError, TypeError, KeyError):
            self.previous = None
            raise

    @staticmethod
    def validate(reply):
        if not isinstance(reply, dict) or reply.get('ok') is not True or reply.get('id') != 1 or reply.get('protocol') != 1:
            raise ValueError('Unsupported Longshot control response')
        version = reply.get('version', '')
        if not isinstance(version, str) or version != 'v3.0.0 (source bd6a0cdd)':
            raise ValueError('Unsupported Longshot version (expected 3.0.0)')
    @staticmethod
    def flag_metrics(event, watch):
        game = event.get('game')
        if event.get('event') != 'oot' or event.get('sub') != 2 or not isinstance(game, dict):
            raise ValueError('Invalid Longshot flag sample')
        frame, sample = event.get('frame'), game.get('frame')
        if not all(number(v) for v in (frame, sample)) or not 0 <= frame-sample <= 30 or game.get('loading') is not False:
            raise ValueError('Waiting for fresh Longshot flags')
        values = game.get('flags')
        if not isinstance(values, dict):
            raise ValueError('Missing Longshot flag values')
        # No coercion of strings, null, negative or nonfinite values. Missing
        # signals are omitted so the rule engine cannot falsely unlock a goal.
        return {name: values[key] for name, key in watch.items()
                if type(values.get(key)) in (int, bool) and 0 <= values[key] <= 1000000}

    def consume(self, reply, identity):
        self.validate(reply)
        if identity != self.identity:
            self.identity = identity
            self.previous = None
            self.distance = 0.0
        game = reply.get('game')
        if not isinstance(game, dict):
            self.previous = None
            raise ValueError('Waiting for Longshot gameplay')
        frame, sample, stamp = reply.get('frame'), game.get('frame'), game.get('t')
        # t is the host monotonic clock, not process uptime. Frame freshness is
        # checked directly; elapsed sample time is checked between observations.
        valid = (reply.get('state') == 'play' and reply.get('stalled') is False
                 and game.get('event') is False and game.get('loading') is False
                 and all(number(v) for v in (frame, sample, stamp))
                 and 0 <= frame - sample <= 30 and stamp >= 0
                 and isinstance(game.get('map'), str) and bool(game['map']))
        if not valid:
            self.previous = None
            raise ValueError('Waiting for fresh gameplay (menu, cutscene or loading)')
        pos = game.get('pos')
        if not isinstance(pos, list) or len(pos) != 3 or not all(number(v) and abs(v) < 1e7 for v in pos):
            self.previous = None
            raise ValueError('Waiting for a valid player position')
        current = (sample, stamp, game['map'], game.get('age'), pos)
        if self.previous:
            old_frame, old_t, old_map, old_age, old_pos = self.previous
            dt = stamp - old_t
            if sample <= old_frame or dt <= 0:
                self.previous = None
                raise ValueError('Waiting for a new gameplay sample')
            distance = math.hypot(pos[0]-old_pos[0], pos[2]-old_pos[2])
            if old_map == game['map'] and old_age == game.get('age') and dt <= 5 and distance <= min(25, 12*dt) and abs(pos[1]-old_pos[1]) <= 4:
                self.distance = min(5.0, self.distance + distance)
        self.previous = current
        metrics = {'live:distance': self.distance}
        maximum = game.get('max_life')
        if type(maximum) is int and 0 < maximum <= 80:
            metrics['max_life'] = maximum
        rupees = game.get('rupees')
        if type(rupees) is int and 0 <= rupees <= 9999:
            metrics['rupees'] = rupees
        return metrics
