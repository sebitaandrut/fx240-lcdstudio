# SPDX-License-Identifier: GPL-3.0-or-later
import importlib.util
from pathlib import Path
import unittest

spec=importlib.util.spec_from_file_location('privacy_audit',Path(__file__).resolve().parents[1]/'tools/audit_privacy.py')
audit=importlib.util.module_from_spec(spec)
spec.loader.exec_module(audit)


class PrivacyAuditTests(unittest.TestCase):
    def test_detects_credentials_without_returning_their_values(self):
        secret=b'gh'+b'p_'+b'A'*30
        result=audit.candidates(b'example '+secret)
        self.assertEqual(result,['credential_signature'])
        self.assertNotIn(secret.decode(),repr(result))

    def test_local_identity_is_matched_only_in_memory(self):
        private=b'private-'+b'owner-token'
        result=audit.candidates(b'prefix '+private,[private])
        self.assertEqual(result,['local_identity_home_or_machine'])
        self.assertNotIn(private.decode(),repr(result))

    def test_network_identifiers_are_candidates_not_silently_allowed(self):
        address=b'192.'+b'168.'+b'1.2'
        mac=b'aa:bb:'+b'cc:dd:'+b'ee:ff'
        result=audit.candidates(address+b' '+mac)
        self.assertEqual(set(result),{'private_ipv4','mac_address'})
        self.assertEqual(audit.candidates(b'ordinary application content'),[])
        self.assertEqual(audit.candidates(b'anode',[b'node']),[])
        self.assertIn('local_identity_home_or_machine',audit.candidates(b'host=node',[b'node']))
