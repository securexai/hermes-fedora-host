"""Bounded operator session for the supplemental B4/B7 cases; never promotion."""
import argparse
import os
from pathlib import Path
import signal
import sys
import time

from common import Failure, atomic, canonical, decode, protected_file, report, require, run
from lifecycle import execute, load
from lifecycle_fixture import Fixture
from maintenance import publish

CASES = {'b4-linux', 'b4-initrd', 'b4-cmdline', 'b4-pcr11', 'b4-external', 'b4-credential',
         'b7-before-copy', 'b7-during-copy', 'b7-before-publish', 'b7-during-replay',
         'b7-before-select', 'b7-after-select', 'b7-notifications'}


def validate_case(case):
    require(set(case) == {'schema', 'case', 'run_id', 'policy_binding'}
            and case['schema'] == 'hermes-remaining-case-v1' and case['case'] in CASES,
            'invalid-remaining-lab-case')
    from release import sha
    require(sha(case['run_id']) and sha(case['policy_binding']), 'invalid-remaining-case-binding')
    return case


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--config', required=True); parser.add_argument('--case', required=True)
    parser.add_argument('--lab-window-grant'); parser.add_argument('--cleanup-only', action='store_true')
    args = parser.parse_args()
    policy = load(args.config)
    case = validate_case(decode(protected_file(args.case, 0).read_bytes()))
    from lifecycle import identity
    require(case['policy_binding'] == identity(policy), 'case-policy-mismatch')
    require(args.cleanup_only or args.lab_window_grant, 'explicit-lab-window-required')

    class OperatorFixture(Fixture):
        def certify(self):
            require(self.state['run_id'] == case['run_id'], 'case-run-mismatch')
            if case['case'].startswith('b4-') or case['case'] == 'b7-notifications':
                super().certify()
            else:
                from schedule import child_environment
                run(['runuser', '-u', self.account.pw_name, '--', 'env', '-i',
                     'PATH=' + child_environment()['PATH'], sys.executable, '-B', '-E', '-s',
                     str(self.code / 'lab_stage.py'), '--config', str(self.directory / 'certifier.json')], timeout=1200)
            atomic(self.directory / 'operator-ready.json', canonical({**case, 'stage': 'operator-ready',
                   'candidate_sha256': self.state['candidate_sha256'], 'release_id': self.state['release_id'],
                   'deadline': self.state['lab_window']['expires_at']}))
            result_path = self.directory / 'operator-result.json'
            while time.time() < self.state['lab_window']['expires_at']:
                if result_path.exists():
                    result = decode(protected_file(result_path, 0).read_bytes())
                    require(set(result) == {'case', 'run_id', 'candidate_sha256', 'result', 'evidence_sha256'}
                            and result['case'] == case['case'] and result['run_id'] == case['run_id']
                            and result['candidate_sha256'] == self.state['candidate_sha256']
                            and result['result'] in {'PASS', 'FAIL', 'BLOCKED'}, 'invalid-operator-case-result')
                    from release import sha
                    require(sha(result['evidence_sha256']), 'missing-operator-evidence-binding')
                    self.save(supplemental_result=result['result'])
                    # Intentional: a supplemental case never fabricates full certification.
                    raise Failure(69, 'supplemental-case-finished-cleanup-required')
                time.sleep(3)
            raise Failure(69, 'operator-case-window-expired')

    def interrupted(signum, frame): raise Failure(69, 'operator-case-interrupted')
    signal.signal(signal.SIGTERM, interrupted); signal.signal(signal.SIGINT, interrupted)
    try:
        return execute(policy, OperatorFixture, cleanup_only=args.cleanup_only, grant_path=args.lab_window_grant)
    except Exception:
        publish(policy['events_dir'], 'action-required', 69)
        raise Failure(69, 'operator-session-closed-see-case-and-cleanup-records') from None


if __name__ == '__main__': report(main)
