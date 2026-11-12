"""Explicit caller-only synthetic B3 service. Never imported by startup/worker/CLI.

The caller must supply a qualified ReplayStore. No network, DSN, scheduler, or
implicit retries. Reports contain bounded identifiers and internal states only.
"""
import time
from src.repositories.projection_store import CaptureError, FencedOut, BudgetExceeded

class ProjectionReplay:
    def __init__(self,store,*,enabled=False):
        if enabled is not True:
            raise CaptureError('bounded replay service disabled')
        self.store=store

    def run(self,domain,*,before_commit=None,after_commit=None,after_transition=None):
        with self.store.invocation():
            return self._run(domain,before_commit=before_commit,after_commit=after_commit,
                             after_transition=after_transition)

    def _run(self,domain,*,before_commit=None,after_commit=None,after_transition=None):
        policy=self.store.replay_policy
        deadline=time.monotonic()+policy.seconds
        results=[]
        def remaining():
            value=deadline-time.monotonic()
            if value<=0: raise BudgetExceeded('replay invocation time budget; stage retained')
            return value
        for _ in range(policy.work):
            remaining()
            ticket=self.store.claim_due(domain)
            if ticket is None: break
            remaining()
            phase=self.store.phase(ticket)['phase']
            if phase=='CLAIMED':
                result=self.store.capture_claim(ticket)
                remaining()
                if result['state']!='READY':
                    self.store.release(ticket)
                    results.append(dict(result,run_id=ticket.run_id))
                    continue
                phase='CAPTURED'
            if phase in ('CAPTURED','FAILED'):
                if not self.store.reserve_attempt(ticket):
                    self.store.release(ticket)
                    results.append(dict(state='BLOCKED',run_id=ticket.run_id))
                    continue
                phase='WRITING'
            if phase=='WRITING':
                try:
                    self.store.process(ticket,max_items=1,seconds=remaining(),before_commit=before_commit)
                except FencedOut:
                    raise  # Never touch newer owner or treat stale data as ordinary poison.
                except Exception:
                    self.store.write_failed(ticket)  # Failed target transaction only, no automatic retry.
                    self.store.release(ticket)
                    raise CaptureError('uncommitted replay failed; durable backoff retained') from None
                # Deliberately outside the write-failure handler: a lost reply is
                # committed PROJECTED, not a failed target write.
                if after_commit: after_commit()
            remaining()
            result=self.store.resolve_claim(ticket,after_transition=after_transition)
            remaining()
            self.store.release(ticket)
            results.append(result)
        return results
