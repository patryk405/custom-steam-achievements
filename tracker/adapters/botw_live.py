"""Read-only live adapter for Savage Wind / BOTW 1.9.0.
Only version, state and mem read commands are used. Layouts are checked against
getter instruction signatures and CRC32 hashes before accepting any values.
"""

import socket, json, struct, zlib, time, math


class Memory:
    def __init__(self):
        self.s = socket.create_connection(("127.0.0.1", 27777), 2)
        self.f = self.s.makefile("rb")
        self.cache = {}

    def request(self, c):
        self.s.sendall((c + "\n").encode())
        v = json.loads(self.f.readline())
        if not v["ok"]:
            raise ValueError(v)
        return v["data"]

    def read(self, a, n):
        if not 0x7000000000 <= a < 0x8000000000 or not 0 < n <= 4096:
            raise ValueError("Invalid live address")
        raw = bytes.fromhex(self.request(f"mem read {a:#x} {n} hex")["hex"])
        if len(raw) != n:
            raise ValueError("Short live read")
        return raw

    def block(self, a, n):
        page = a & ~4095
        if a + n > page + 4096:
            return self.read(a, n)
        if page not in self.cache:
            self.cache[page] = self.read(page, 4096)
        return self.cache[page][a - page : a - page + n]

    def close(self):
        self.f.close()
        self.s.close()

    def ptr(self, a):
        return struct.unpack("<Q", self.read(a, 8))[0]

    def u32(self, a):
        return struct.unpack("<I", self.read(a, 4))[0]

    def locate(self):
        wm = self.ptr(0x7001E57580)
        tm = self.ptr(self.ptr(wm + 0x5C8))
        calc = self.ptr(self.ptr(tm) + 0x30)
        code = struct.unpack("<32I", self.read(calc, 128))
        for i in range(29):
            if (
                code[i] & 0x9F00001F == 0x90000008
                and code[i + 1] & 0xFFC003FF == 0x91000108
                and code[i + 2] == 0xF9400114
                and code[i + 3] & 0xFF00001F == 0xB5000014
            ):
                imm = ((code[i] >> 5) & 0x7FFFF) << 2 | ((code[i] >> 29) & 3)
                pages = (imm ^ 0x100000) - 0x100000
                site = (
                    ((calc + 4 * i) & ~0xFFF)
                    + pages * 4096
                    + ((code[i + 1] >> 10) & 0xFFF)
                )
                return self.ptr(site)
        raise ValueError("no manager")


class LiveReader:
    def __init__(self):
        self.identity = None
        self.addresses = {}
        self.last_position = None
        self.distance = 0.0
        self.camera_turn = 0.0
        self.camera_up_armed = False
        self.last_camera = None

    def read_metrics(self, manifest):
        m = Memory()
        try:
            version = m.request("version")
            if version.get("version") != "0.6.0-alpha.6":
                raise ValueError("Unsupported Savage Wind live version")
            if "hour" not in m.request("state"):
                raise ValueError("Waiting for a loaded world")
            mgr = m.locate()
            buf = m.ptr(m.ptr(mgr + 0xBE0))
            arrays = []
            for off, hashoff, kind, signature in [
                (0x10, 12, "bool", bytes.fromhex("082c403900010012c0035fd6")),
                (0x20, 28, "int", bytes.fromhex("001840b9c0035fd6")),
            ]:
                count = m.u32(buf + off - 8)
                array = m.ptr(buf + off)
                if not 0 < count < 100000:
                    raise ValueError("Invalid flag count")
                first = m.ptr(array)
                getter = m.ptr(m.ptr(first) + 0x88)
                if m.read(getter, len(signature)) != signature:
                    raise ValueError("Unsupported live flag layout")
                arrays.append((count, array, hashoff, kind, m.ptr(first)))
            identity = (mgr, buf, tuple(arrays))
            if self.identity != identity:
                self.identity = identity
                self.addresses = {}
                self.last_position = None
                self.last_camera = None
                self.camera_up_armed = False
            flags = {f for r in manifest["rules"].values() for f in r["flags"]}
            integer_flags = {
                f
                for r in manifest["rules"].values()
                if r["op"] in ("number", "sum")
                for f in r["flags"]
            }
            for name in sorted(flags):
                if name.startswith("live:") or name in self.addresses:
                    continue
                h = zlib.crc32(name.removeprefix("caption:").encode())
                count, array, hashoff, kind, vtable = arrays[int(name in integer_flags)]
                lo, hi = 0, count
                while lo < hi:
                    mid = (lo + hi) // 2
                    p = struct.unpack("<Q", m.block(array + mid * 8, 8))[0]
                    raw = m.block(p, 32)
                    got = struct.unpack_from("<I", raw, hashoff)[0]
                    if got < h:
                        lo = mid + 1
                    elif got > h:
                        hi = mid
                    else:
                        if struct.unpack_from("<Q", raw)[0] != vtable:
                            raise ValueError("Flag type mismatch")
                        self.addresses[name] = (p, h, hashoff, kind, vtable)
                        break
            # Fresh pages: lookup may take several frames. Never evaluate cached discovery values.
            m.cache.clear()
            metrics = {}
            for name, (p, h, hashoff, kind, vtable) in self.addresses.items():
                raw = m.block(p, 32)
                if (
                    struct.unpack_from("<Q", raw)[0] != vtable
                    or struct.unpack_from("<I", raw, hashoff)[0] != h
                ):
                    self.identity = None
                    raise ValueError("World changed during live reading")
                metrics[name] = (
                    (raw[11] & 1)
                    if kind == "bool"
                    else struct.unpack_from("<i", raw, 24)[0]
                )
            if m.locate() != mgr or m.ptr(m.ptr(mgr + 0xBE0)) != buf:
                raise ValueError("World changed during live reading")
            if "live:distance_m" in flags:
                pos = m.request("pos")
                metrics["live:distance_m"] = self.observe_position(
                    pos, time.monotonic()
                )
            if any(f.startswith("live:camera_") for f in flags):
                metrics.update(
                    self.observe_camera(m.request("camera"), time.monotonic())
                )
            return metrics
        finally:
            m.close()

    def observe_position(self, pos, now):
        coords = tuple(pos.get(k) for k in ("x", "y", "z"))
        if not all(
            type(v) in (int, float) and math.isfinite(v) for v in coords
        ) or not pos.get("player_info"):
            self.last_position = None
            return self.distance
        previous = self.last_position
        self.last_position = (coords, now, pos["player_info"])
        if previous:
            old, timestamp, player = previous
            elapsed = now - timestamp
            delta = math.dist(old, coords)
            if (
                player == pos["player_info"]
                and 0 < elapsed <= 10
                and 0.1 <= delta <= 30
                and delta / elapsed <= 15
            ):
                self.distance += delta
        return self.distance

    def observe_camera(self, camera, now):
        yaw, pitch = camera.get("yaw"), camera.get("pitch")
        if (
            not all(type(v) in (int, float) and math.isfinite(v) for v in (yaw, pitch))
            or not -90 <= pitch <= 90
        ):
            self.last_camera = None
            return {}
        if self.last_camera:
            previous, timestamp = self.last_camera
            if 0 < now - timestamp <= 10:
                delta = abs((yaw - previous + 180) % 360 - 180)
                if delta >= 1:
                    self.camera_turn += delta
        if pitch < 20:
            self.camera_up_armed = True
        self.last_camera = (yaw, now)
        return {
            "live:camera_turn_degrees": self.camera_turn,
            "live:camera_up_degrees": max(0, pitch) if self.camera_up_armed else 0,
        }
