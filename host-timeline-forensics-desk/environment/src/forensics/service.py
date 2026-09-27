"""Composition root shared by API, worker, CLI, and local tooling."""
from __future__ import annotations
from dataclasses import dataclass
from .authz import AuthorizationService
from .cases import CaseService
from .coverage import CoverageService
from .database import Database, get_database
from .dispatch import CollectionDispatcher
from .evidence import EvidenceStore
from .events import EventInboxService
from .exports import ExportService, RetentionService
from .fixture import seed_records
from .inventory import InventoryService
from .planner import PlanService
from .policy import PolicyService
from .source_catalog import SourceCatalog
from .readiness import ReadinessService
from .reconcile import Reconciler
from .queueing import QueueService
from .config import get_settings
from .offline_intake import OfflineIntake
from .recovery import RecoveryManager
from .reporting import EvidencePublisher
from .timeline import TimelineProjector
from .audit import AuditService


@dataclass
class ServiceContainer:
    database: Database
    authorization: AuthorizationService
    cases: CaseService
    inventory: InventoryService
    policies: PolicyService
    plans: PlanService
    queue: QueueService
    events: EventInboxService
    evidence: EvidenceStore
    reconciler: Reconciler
    coverage: CoverageService
    exports: ExportService
    retention: RetentionService
    readiness: ReadinessService
    dispatcher: CollectionDispatcher
    source_catalog: SourceCatalog
    offline_intake: OfflineIntake
    recovery: RecoveryManager
    timeline: TimelineProjector
    publisher: EvidencePublisher
    audit: AuditService

    @classmethod
    def build(cls, database: Database | None = None) -> "ServiceContainer":
        db = database or get_database()
        authz = AuthorizationService(db)
        inventory = InventoryService(db)
        policies = PolicyService(db, authz)
        evidence = EvidenceStore(db, authz)
        queue = QueueService(db)
        readiness = ReadinessService(db)
        source_catalog = SourceCatalog()
        events = EventInboxService(db)
        timeline = TimelineProjector(db, authz)
        return cls(
            database=db,
            authorization=authz,
            cases=CaseService(db, authz),
            inventory=inventory,
            policies=policies,
            plans=PlanService(db, authz, inventory, policies, source_catalog),
            queue=queue,
            events=events,
            evidence=evidence,
            reconciler=Reconciler(db, evidence, timeline),
            coverage=CoverageService(db, authz),
            exports=ExportService(db, authz),
            retention=RetentionService(db),
            readiness=readiness,
            dispatcher=CollectionDispatcher(),
            source_catalog=source_catalog,
            offline_intake=OfflineIntake(authz, events),
            recovery=RecoveryManager(db, queue, readiness, get_settings().evidence_root),
            timeline=timeline,
            publisher=EvidencePublisher(db, authz, readiness),
            audit=AuditService(db, authz),
        )

    def bootstrap(self) -> dict:
        recovery = self.recovery.recover()
        seed = seed_records(self.database, evidence_root=get_settings().evidence_root)
        return {"recovery": recovery, "seed": seed}
