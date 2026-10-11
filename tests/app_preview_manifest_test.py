#!/usr/bin/env python3
"""Private bounded revision handoff, before any native data or writes."""
import os
import unittest

import app_test as api
from app_test import copy_request


class ManifestTests(unittest.TestCase):
    setUp=api.AppTests.setUp
    client=api.AppTests.client

    def request(self,entries='1',version='1'):
        request=copy_request(self.source,self.dest)
        request.update(id='native',op='_native_transfer',role='sender',idle_timeout_seconds='1',
                       preview_binding={'version':version,'entries':entries,'root_revision':None})
        return request

    def revision(self):
        c=self.client(); c.send({'id':'stat','op':'lstat','endpoint':api.endpoint(self.source)})
        c.finish()
        return next(e['entry']['revision'] for e in c.events if e['type']=='entry')

    def row(self,path=None):
        return {'path':{'bytes_hex':os.fsencode(path or self.source).hex()},'revision':self.revision()}

    def ready(self,c):
        event=c.read()
        self.assertEqual(event['type'],'preview_binding_ready',c.events)
        return event

    def test_private_chunks_can_exceed_ordinary_request_id_ledger(self):
        revision=self.revision(); c=self.client(); c.send(self.request('38'))
        for sequence in range(1,39):
            self.assertEqual(self.ready(c)['next_sequence'],str(sequence))
            c.send({'sequence':str(sequence),'rows':[{'path':{'bytes_hex':os.fsencode(self.source/str(sequence)).hex()},'revision':revision}]})
        # Native hello has not been supplied, so neither side can start copying.
        while c.read()['type']!='transfer_ready': pass
        c.proc.stdin.close(); self.assertNotEqual(c.proc.wait(timeout=6),0)
        self.assertEqual(list(self.dest.iterdir()),[])
        self.assertFalse((self.dest/'.xsync-app-partials').exists())

    def test_bad_headers_fail_before_native_ready_or_any_output(self):
        for count,version in [('0','1'),('100001','1'),(1,'1'),('1',1),('1','2')]:
            with self.subTest(count=count,version=version):
                c=self.client(); c.send(self.request(count,version)); result=c.finish()
                self.assertEqual(result['status'],'failure',c.events)
                self.assertFalse(any(e['type']=='transfer_ready' for e in c.events))
                self.assertEqual(list(self.dest.iterdir()),[])

    def test_invalid_chunks_and_duplicate_paths_fail_before_native_ready(self):
        row=self.row()
        invalid=[{'sequence':'2','rows':[row]}, {'sequence':1,'rows':[row]},
                 {'sequence':'1','rows':[]}, {'sequence':'1','rows':[row],'unknown':True},
                 {'sequence':'1','rows':[row,row]},
                 {'sequence':'1','rows':[{'path':{'bytes_hex':'00'},'revision':row['revision']}]},
                 {'sequence':'1','rows':[{'path':{'bytes_hex':'66696c65'},'revision':row['revision']}]}]
        for chunk in invalid:
            with self.subTest(chunk=chunk):
                c=self.client(); c.send(self.request('2')); self.ready(c); c.send(chunk); result=c.finish()
                self.assertEqual(result['status'],'failure',c.events)
                self.assertFalse(any(e['type']=='transfer_ready' for e in c.events)); self.assertEqual(list(self.dest.iterdir()),[])

    def test_truncated_manifest_never_starts_data_or_private_store(self):
        c=self.client(); c.send(self.request('2')); self.ready(c)
        c.send({'sequence':'1','rows':[self.row()]}); self.ready(c); c.proc.stdin.close()
        result=c.finish(); self.assertNotEqual(result['status'],'success',c.events)
        self.assertFalse(any(e['type']=='transfer_ready' for e in c.events)); self.assertEqual(list(self.dest.iterdir()),[])


if __name__=='__main__': unittest.main()
