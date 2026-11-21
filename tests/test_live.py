"""Synthetic live memory; never attach to or modify the running game in tests."""
import struct
import sys
import unittest
import zlib
from pathlib import Path
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1]/'tracker'))
from adapters.botw_live import LiveReader
from engine import apply_rules

BASE=0x7200000000
class FakeMemory:
    def __init__(self):
        self.cache={};self.data={};self.bad=False;self.generation=0
        self.put(BASE+0xbe0,'Q',BASE+0x2000)
        self.put(BASE+0x2000,'Q',BASE+0x3000)
        for i,(name,off,hashoff,signature) in enumerate([
            ('done',0x10,12,'082c403900010012c0035fd6'),
            ('count',0x20,28,'001840b9c0035fd6')]):
            array=BASE+0x4000+i*0x1000;flag=BASE+0x6000+i*0x1000;vt=BASE+0x8000+i*0x1000;fn=BASE+0xa000+i*0x1000
            self.put(BASE+0x3000+off-8,'I',1);self.put(BASE+0x3000+off,'Q',array)
            self.put(array,'Q',flag);self.put(flag,'Q',vt);self.put(flag+hashoff,'I',zlib.crc32(name.encode()))
            self.put(vt+0x88,'Q',fn)
            self.write(fn,bytes.fromhex(signature))
        self.values(0,0)
    def put(self,a,fmt,v):self.write(a,struct.pack('<'+fmt,v))
    def write(self,a,raw):self.data.update({a+i:v for i,v in enumerate(raw)})
    def values(self,done,count):self.put(BASE+0x600b,'B',done);self.put(BASE+0x7018,'i',count)
    def request(self,c):return {'version':'0.6.0-alpha.6'} if c=='version' else {'hour':12}
    def read(self,a,n):return bytes(self.data.get(a+i,0) for i in range(n))
    block=read
    def ptr(self,a):return struct.unpack('<Q',self.read(a,8))[0]
    def u32(self,a):return struct.unpack('<I',self.read(a,4))[0]
    def locate(self):return BASE
    def close(self):pass

MANIFEST={'id':'live-test','rules':{'one':{'op':'any','flags':['done']},'two':{'op':'number','flags':['count'],'threshold':3}}}
class LiveTests(unittest.TestCase):
    def test_live_changes_unlock_without_any_save(self):
        memory=FakeMemory();reader=LiveReader()
        with patch('adapters.botw_live.Memory',return_value=memory):
            self.assertEqual(reader.read_metrics(MANIFEST),{'done':0,'count':0})
            memory.values(1,3)
            metrics=reader.read_metrics(MANIFEST)
            self.assertEqual(metrics,{'done':1,'count':3})
            progress=apply_rules({},MANIFEST,metrics,{'one':{'target':1},'two':{'target':3}},100)
            self.assertEqual(progress['one']['unlockedAt'],100)
            self.assertEqual(progress['two']['current'],3)
    def test_wrong_getter_or_changed_identity_fails_closed(self):
        memory=FakeMemory();reader=LiveReader()
        with patch('adapters.botw_live.Memory',return_value=memory):
            reader.read_metrics(MANIFEST)
            memory.put(BASE+0x600c,'I',123)
            with self.assertRaisesRegex(ValueError,'World changed'):reader.read_metrics(MANIFEST)
            memory.write(BASE+0xa000,b'\0'*12)
            with self.assertRaisesRegex(ValueError,'Unsupported live flag layout'):reader.read_metrics(MANIFEST)

    def test_distance_ignores_loading_teleports_and_player_changes(self):
        reader=LiveReader()
        def pos(x, player='Link'):return {'x':x,'y':100,'z':0,'player_info':player}
        self.assertEqual(reader.observe_position(pos(0),1),0)
        self.assertEqual(reader.observe_position(pos(3),2),3)
        self.assertEqual(reader.observe_position(pos(6),3),6)
        self.assertEqual(reader.observe_position(pos(500),4),6)
        self.assertEqual(reader.observe_position(pos(505),20),6)
        self.assertEqual(reader.observe_position(pos(510,'Reloaded'),21),6)
        self.assertEqual(reader.observe_position({'x':float('nan')},22),6)

    def test_camera_wraparound_invalid_and_loading_gap(self):
        r=LiveReader()
        self.assertEqual(r.observe_camera({'yaw':170,'pitch':-20},1)['live:camera_up_degrees'],0)
        self.assertEqual(r.observe_camera({'yaw':-170,'pitch':40},2),{'live:camera_turn_degrees':20,'live:camera_up_degrees':40})
        self.assertEqual(r.observe_camera({'yaw':-100,'pitch':0},3)['live:camera_turn_degrees'],90)
        self.assertEqual(r.observe_camera({'yaw':100,'pitch':0},20)['live:camera_turn_degrees'],90)
        self.assertEqual(r.observe_camera({'yaw':float('nan'),'pitch':0},21),{})
