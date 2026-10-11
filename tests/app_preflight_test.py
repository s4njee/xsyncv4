#!/usr/bin/env python3
"""Read-only destination observations and exact advisory space budgets."""
import copy
import errno
import json
import os
import pathlib
import subprocess
import sys
import tempfile
import unittest
import time

import app_test as api
from app_test import BINARY, ROOT, Client, endpoint

class AppPreflightTests(unittest.TestCase):
    setUpClass = classmethod(api.AppTests.setUpClass.__func__)
    fault_env = api.AppTests.fault_env

    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='xs preflight '); self.addCleanup(self.tmp.cleanup)
        self.root = pathlib.Path(self.tmp.name); self.dest = self.root/'destination'; self.dest.mkdir()
        (self.dest/'existing').write_bytes(b'unchanged data')
        self.request = {'id':'preflight','op':'preflight','endpoint':endpoint(self.dest)}

    def job(self, request=None, env=None):
        c = Client(env); self.addCleanup(c.close); c.send(request or self.request)
        result = c.finish(); return c,result

    def row(self, c): return next(e for e in c.events if e['type'] == 'destination_preflight')

    def test_filesystem_observation_is_read_only_and_exact(self):
        before = self.dest.stat(); data = (self.dest/'existing').stat()
        c,result = self.job(); self.assertEqual(result['status'],'success',c.events); row = self.row(c)
        self.assertEqual(c.capabilities['destination_preflight'],'1')
        self.assertIn('preflight',c.capabilities['operations']); self.assertIn('preflight',c.capabilities['ssh_operations'])
        self.assertTrue(row['advisory']); self.assertFalse(row['copy_authorized']); self.assertFalse(row['write_probe_performed'])
        self.assertEqual(row['endpoint'],'local'); self.assertEqual(row['path']['bytes_hex'],os.fsencode(self.dest).hex())
        volume = os.statvfs(self.dest); unit = volume.f_frsize or volume.f_bsize
        self.assertEqual(row['capacity']['total_bytes'],str(volume.f_blocks*unit))
        self.assertEqual(row['capacity']['allocation_unit_bytes'],str(unit))
        self.assertEqual(row['read_only'],bool(volume.f_flag & os.ST_RDONLY))
        self.assertEqual(row['names']['max_component_bytes'],str(os.pathconf(self.dest,'PC_NAME_MAX')))
        self.assertEqual(row['names']['forbidden_bytes_hex'],'002f'); self.assertFalse(row['names']['dot_components_allowed'])
        self.assertIsNone(row['names']['invalid_utf8_supported']); self.assertIsNone(row['space'])
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()),['existing'])
        after = self.dest.stat(); updated = (self.dest/'existing').stat()
        self.assertEqual((before.st_mtime_ns,before.st_ctime_ns),(after.st_mtime_ns,after.st_ctime_ns))
        self.assertEqual((data.st_mtime_ns,data.st_ctime_ns),(updated.st_mtime_ns,updated.st_ctime_ns))
        self.assertEqual((self.dest/'existing').read_bytes(),b'unchanged data')

    def test_budget_accounts_for_atomic_staging_retained_data_and_allocation_uncertainty(self):
        request = copy.deepcopy(self.request); request['space'] = {'regular_file_sizes':['1','9000','2000','0'],'jobs':'2','retained_logical_bytes':'700'}
        c,result = self.job(request); self.assertEqual(result['status'],'success',c.events); row = self.row(c); budget = row['space']
        self.assertEqual(budget['copy_logical_bytes'],'11001'); self.assertEqual(budget['atomic_staging_peak_logical_bytes'],'11000')
        self.assertEqual(budget['coexisting_data_logical_bytes'],'11701'); self.assertEqual(budget['retained_logical_bytes'],'700')
        unit = int(row['capacity']['allocation_unit_bytes'])
        self.assertEqual(budget['new_regular_data_allocation_estimate_bytes'],str(sum((n+unit-1)//unit*unit for n in (1,9000,2000,0))))
        self.assertFalse(budget['inputs_verified']); self.assertTrue(budget['retained_already_consumes_available'])
        self.assertFalse(budget['reclaim_before_publication']); self.assertFalse(budget['copy_uses_clone']); self.assertFalse(budget['copy_uses_sparse'])
        self.assertTrue(budget['filesystem_allocation_uncertainty'])
        for field in ('physical_requirement_bytes','metadata_overhead_bytes','quota_remaining_bytes'): self.assertIsNone(budget[field])

    def test_large_decimal_budgets_remain_exact_and_overflow_is_unknown(self):
        request = copy.deepcopy(self.request); request['space'] = {'regular_file_sizes':[str(2**53+1)],'jobs':'1'}
        c,result = self.job(request); self.assertEqual(result['status'],'success',c.events)
        self.assertEqual(self.row(c)['space']['copy_logical_bytes'],str(2**53+1))
        self.assertFalse(self.row(c)['space']['data_budget_fits_available'])
        request['space']['regular_file_sizes'] = [str(2**63-1)]*2
        c,result = self.job(request); self.assertEqual(result['status'],'success',c.events); budget = self.row(c)['space']
        self.assertEqual(budget['copy_logical_bytes'],str(2**64-2))
        self.assertIsNone(budget['new_regular_data_allocation_estimate_bytes']); self.assertIsNone(budget['data_budget_fits_available'])

    def test_bad_inputs_fail_before_any_preflight_observation(self):
        bad = [None,False,[],{}, {'regular_file_sizes':'1'}, {'regular_file_sizes':[False]},
               {'regular_file_sizes':['-1']},{'regular_file_sizes':[str(2**63)]}, {'regular_file_sizes':['1'],'jobs':'0'},
               {'regular_file_sizes':['1'],'jobs':'65'}, {'regular_file_sizes':['1'],'jobs':1},
               {'regular_file_sizes':[str(2**63-1)]*3}, {'regular_file_sizes':['1'],'retained_logical_bytes':str(2**64-1)},
               {'regular_file_sizes':[],'password':'secret'}, {'regular_file_sizes':['1e9']}]
        for space in bad:
            with self.subTest(space=space):
                request = copy.deepcopy(self.request); request['space'] = space
                c,result = self.job(request); self.assertEqual(result['status'],'failure',c.events)
                self.assertFalse(any(e['type'] == 'destination_preflight' for e in c.events))
        request = copy.deepcopy(self.request); request['options'] = {'dry_run':False}
        c,result = self.job(request); self.assertEqual(result['status'],'failure',c.events)
        self.assertEqual(sorted(p.name for p in self.dest.iterdir()),['existing'])

    def test_missing_non_directory_and_symlink_destinations_are_typed_failures(self):
        (self.root/'link').symlink_to(self.dest)
        for path in (self.root/'missing',self.dest/'existing',self.root/'link'):
            with self.subTest(path=path):
                request = copy.deepcopy(self.request); request['endpoint'] = endpoint(path)
                c,result = self.job(request); self.assertEqual(result['status'],'failure',c.events)
                self.assertTrue(any(e['type'] == 'error' and e['operation'] == 'destination_preflight' and e['native_code'] is not None for e in c.events))
                self.assertFalse(any(e['type'] == 'destination_preflight' for e in c.events))

    def test_reference_cli_preflight_without_tty(self):
        done = subprocess.run([sys.executable,str(ROOT/'tools/app_client.py'),'--binary',str(BINARY),
            'preflight',str(self.dest),'--regular-file-size','9007199254740993','--jobs','1','--retained-logical-bytes','32'],
            stdin=subprocess.DEVNULL,capture_output=True,text=True,timeout=10)
        self.assertEqual(done.returncode,0,done.stdout+done.stderr)
        events = [json.loads(line) for line in done.stdout.splitlines()]; row = next(e for e in events if e['type'] == 'destination_preflight')
        self.assertEqual(row['space']['coexisting_data_logical_bytes'],'9007199254741025')
        self.assertEqual(events[-1]['status'],'success')

    def test_read_only_mount_is_detected_when_available(self):
        if sys.platform != 'linux' or not pathlib.Path('/host').is_dir() or not os.statvfs('/host').f_flag & os.ST_RDONLY:
            self.skipTest('requires the read-only source mount in the Linux rig')
        request = copy.deepcopy(self.request); request['endpoint'] = endpoint('/host')
        c,result = self.job(request); self.assertEqual(result['status'],'success',c.events)
        self.assertTrue(self.row(c)['read_only']); self.assertFalse(self.row(c)['directory_access_allowed'])

    def test_unavailable_capacity_and_name_limits_are_unknown_not_zero(self):
        env = self.fault_env(self.dest); env.update(XSYNC_FAULT_STATVFS_ERROR=str(errno.EIO),XSYNC_FAULT_NAME_MAX_ERROR=str(errno.EIO))
        request = copy.deepcopy(self.request); request['space'] = {'regular_file_sizes':['1']}
        c,result = self.job(request,env); self.assertEqual(result['status'],'success',c.events); row = self.row(c)
        for key in ('total_bytes','free_bytes','available_bytes','allocation_unit_bytes'): self.assertIsNone(row['capacity'][key])
        self.assertEqual(row['capacity']['native_error'],str(errno.EIO)); self.assertIsNone(row['read_only'])
        self.assertIsNone(row['names']['max_component_bytes']); self.assertEqual(row['names']['limit_kind'],'unknown')
        self.assertIsNone(row['space']['new_regular_data_allocation_estimate_bytes']); self.assertIsNone(row['space']['data_budget_fits_available'])
        env.pop('XSYNC_FAULT_NAME_MAX_ERROR'); env['XSYNC_FAULT_NAME_MAX_UNBOUNDED'] = '1'
        c,result = self.job(request,env); self.assertEqual(result['status'],'success',c.events)
        self.assertIsNone(self.row(c)['names']['max_component_bytes']); self.assertEqual(self.row(c)['names']['limit_kind'],'unbounded')

    def test_capacity_overflow_and_read_only_state_do_not_invent_available_space(self):
        env = self.fault_env(self.dest); env.update(XSYNC_FAULT_STATVFS_OVERFLOW='1',XSYNC_FAULT_STATVFS_READ_ONLY='1')
        request = copy.deepcopy(self.request); request['space'] = {'regular_file_sizes':['1']}
        c,result = self.job(request,env); self.assertEqual(result['status'],'success',c.events); row = self.row(c)
        self.assertTrue(row['read_only']); self.assertFalse(row['directory_access_allowed'])
        for field in ('total_bytes','free_bytes','available_bytes'): self.assertIsNone(row['capacity'][field])
        self.assertEqual(row['capacity']['allocation_unit_bytes'],str(2**63))
        self.assertEqual(row['space']['new_regular_data_allocation_estimate_bytes'],str(2**63))
        self.assertIsNone(row['space']['data_budget_fits_available'])

    def test_replaced_logical_root_cannot_return_a_stale_observation(self):
        marker = self.root/'volume-observed'; env = self.fault_env(self.dest); env['XSYNC_FAULT_STATVFS_NOTIFY'] = str(marker)
        c = Client(env); self.addCleanup(c.close); c.send(self.request)
        deadline = time.monotonic()+5
        while not marker.exists():
            self.assertLess(time.monotonic(),deadline); time.sleep(.01)
        self.dest.rename(self.root/'original'); self.dest.mkdir()
        pathlib.Path(str(marker)+'.release').touch()
        result = c.finish(); self.assertEqual(result['status'],'failure',c.events)
        self.assertFalse(any(e['type'] == 'destination_preflight' for e in c.events))
        self.assertTrue(any(e['type'] == 'error' and e['native_code'] == str(errno.ESTALE) for e in c.events))
        self.assertEqual(list(self.dest.iterdir()),[]); self.assertEqual((self.root/'original'/'existing').read_bytes(),b'unchanged data')

if __name__ == '__main__': unittest.main()
