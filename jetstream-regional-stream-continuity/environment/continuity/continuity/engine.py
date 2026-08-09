from __future__ import annotations

from collections import defaultdict
from collections.abc import Mapping
from datetime import datetime, timedelta
from typing import Any

from .model import (
    ContractError,
    EffectStatus,
    EventEnvelope,
    Finding,
    FindingSeverity,
    FencingError,
    GenerationStatus,
    HealthReport,
    LeaseToken,
    PublishAck,
    PublishState,
    ReconcileStatus,
    ReconciliationSummary,
    ReplayConflict,
    ReplayPlan,
    ReplayRange,
    ReplayStatus,
    RetentionPolicy,
    contiguous_floor,
    sha256_text,
    to_iso,
    utcnow,
)
from .policy import (
    ContinuityEngine as BaseContinuityEngine,
    Delivery,
    OriginObservation,
    ProcessingResult,
    Publisher,
    ReplayDecision,
    RetentionDecision,
)
from .store import RetentionWatermark


class ContinuityEngine(BaseContinuityEngine):
    """Inherited regional continuity controller used by the operator CLI."""

    def message_id_for_event(self, event: EventEnvelope, *, attempt_no: int) -> str:
        return f"{event.identity.event_id}:attempt:{attempt_no}"

    async def publish_event(self, event_id: str, publisher: Publisher) -> PublishAck:
        event = self.store.event_by_id(event_id)
        if event is None:
            raise ContractError(f"event {event_id} is not in the edge journal")
        expected_stream = self.expected_stream_for_event(event)
        attempt_no = self._next_attempt(event.identity.event_id)
        message_id = self.message_id_for_event(event, attempt_no=attempt_no)
        attempt_no = self.store.begin_publish_attempt(
            event.identity.event_id,
            message_id=message_id,
            requested_stream=expected_stream,
        )
        self.store.execute(
            "UPDATE event_journal SET publish_state='PUBLISHED',last_publish_at=? WHERE event_id=?",
            (to_iso(utcnow()), event.identity.event_id),
        )
        try:
            ack = await publisher.publish(
                event, message_id=message_id, expected_stream=expected_stream
            )
        except TimeoutError as exc:
            self.store.finish_publish_attempt(
                event.identity.event_id,
                attempt_no,
                outcome="TIMEOUT",
                error_code="PUBLISH_TIMEOUT",
                error_text=str(exc),
            )
            raise
        except Exception as exc:
            self.store.finish_publish_attempt(
                event.identity.event_id,
                attempt_no,
                outcome="ERROR",
                error_code=type(exc).__name__,
                error_text=str(exc),
            )
            raise
        self.store.finish_publish_attempt(
            event.identity.event_id,
            attempt_no,
            outcome="DUPLICATE_ACK" if ack.duplicate else "ACKED",
            ack=ack,
        )
        self.store.update_generation_high_watermark(
            event.identity.region,
            event.identity.generation,
            event.identity.origin_sequence,
        )
        return ack

    def validate_origin_observation(self, observation: OriginObservation):
        region_cfg = self.region_config(observation.region)
        expected_stream = str(region_cfg["stream_name"])
        expected_domain = str(region_cfg["domain"])
        if observation.stream_name != expected_stream:
            raise ContractError(
                f"observed stream {observation.stream_name} does not match configured {expected_stream}"
            )
        if observation.domain != expected_domain:
            raise ContractError(
                f"observed domain {observation.domain} does not match configured {expected_domain}"
            )
        current = self.store.confirmed_generation(observation.region)
        if current is None:
            pending = self.store.record_pending_generation(
                observation.region,
                generation=1,
                stream_fingerprint=observation.stream_fingerprint,
                first_sequence=observation.first_sequence,
                last_observed_sequence=observation.last_sequence,
                at=observation.observed_at,
            )
            return self.store.approve_generation(
                observation.region,
                pending.generation,
                approved_by="continuity-controller",
                at=observation.observed_at,
            )
        if observation.stream_fingerprint == current.stream_fingerprint:
            self.store.update_generation_high_watermark(
                observation.region,
                current.generation,
                observation.last_sequence,
            )
            refreshed = self.store.generation(observation.region, current.generation)
            if refreshed is None:
                raise ContractError("confirmed generation disappeared")
            return refreshed
        next_generation = current.generation + 1
        pending = self.store.generation(observation.region, next_generation)
        if pending is None:
            pending = self.store.record_pending_generation(
                observation.region,
                generation=next_generation,
                stream_fingerprint=observation.stream_fingerprint,
                first_sequence=observation.first_sequence,
                last_observed_sequence=observation.last_sequence,
                at=observation.observed_at,
            )
        return self.store.approve_generation(
            observation.region,
            pending.generation,
            approved_by="continuity-controller",
            at=observation.observed_at,
        )

    def _emit_dispatch(
        self,
        *,
        consumer_name: str,
        event: EventEnvelope,
        worker_id: str,
        fence_epoch: int,
        detail: Mapping[str, Any],
    ) -> None:
        consumer = next(
            (
                row
                for row in self.store.consumers()
                if str(row["consumer_name"]) == consumer_name
            ),
            None,
        )
        if consumer is None:
            raise ContractError(f"unknown consumer {consumer_name}")
        self.store.execute(
            "INSERT INTO effect_dispatches(consumer_name,event_id,effect_key,effect_type,dispatched_at,worker_id,fence_epoch,state,detail_json) "
            "VALUES(?,?,?,?,?,?,?,'CONFIRMED',?)",
            (
                consumer_name,
                event.identity.event_id,
                f"{consumer_name}:{event.identity.event_id}",
                str(consumer["effect_type"]),
                to_iso(utcnow()),
                worker_id,
                fence_epoch,
                __import__("json").dumps(
                    dict(detail), sort_keys=True, separators=(",", ":")
                ),
            ),
        )

    async def process_delivery(
        self,
        delivery: Delivery,
        *,
        worker_id: str,
        fence_epoch: int,
        poison_predicate: callable | None = None,
    ) -> ProcessingResult:
        event = delivery.event
        self.validate_event_generation(event)
        if poison_predicate is not None and bool(poison_predicate(event)):
            self.store.quarantine_effect(
                consumer_name=delivery.consumer_name,
                event=event,
                reason_code="VALIDATION_REJECTED",
                reason_text="event rejected by consumer validation",
                delivery_count=delivery.delivery_count,
                worker_id=worker_id,
                fence_epoch=fence_epoch,
            )
            await delivery.ack()
            checkpoint = self.store.advance_ack_checkpoint(
                consumer_name=delivery.consumer_name,
                identity=event.identity,
                jetstream_ack_floor=delivery.jetstream_ack_floor,
            )
            return ProcessingResult(
                consumer_name=delivery.consumer_name,
                event_id=event.identity.event_id,
                status="QUARANTINED",
                duplicate_effect=False,
                checkpoint=checkpoint,
                detail={"delivery_count": delivery.delivery_count},
            )

        existing = self.store.effect(delivery.consumer_name, event.identity.event_id)
        duplicate_effect = (
            existing is not None and existing.status is EffectStatus.COMMITTED
        )
        checkpoint = self.store.advance_ack_checkpoint(
            consumer_name=delivery.consumer_name,
            identity=event.identity,
            jetstream_ack_floor=delivery.jetstream_ack_floor,
        )
        payload = self._consumer_effect_payload(delivery.consumer_name, event)
        self._emit_dispatch(
            consumer_name=delivery.consumer_name,
            event=event,
            worker_id=worker_id,
            fence_epoch=fence_epoch,
            detail=payload,
        )
        if not duplicate_effect:
            effect = self.store.prepare_effect(
                consumer_name=delivery.consumer_name,
                event=event,
                effect_type=self._consumer_effect_type(delivery.consumer_name),
                effect_payload=payload,
                worker_id=worker_id,
                fence_epoch=fence_epoch,
            )
            if effect.status is not EffectStatus.COMMITTED:
                self.store.commit_effect(
                    delivery.consumer_name,
                    event.identity.event_id,
                    worker_id=worker_id,
                    fence_epoch=fence_epoch,
                )
            checkpoint = self.store.advance_effect_checkpoint(
                consumer_name=delivery.consumer_name,
                identity=event.identity,
            )
        await delivery.ack()
        return ProcessingResult(
            consumer_name=delivery.consumer_name,
            event_id=event.identity.event_id,
            status="COMMITTED",
            duplicate_effect=duplicate_effect,
            checkpoint=checkpoint,
            detail={"delivery_count": delivery.delivery_count, "worker_id": worker_id},
        )

    def reconcile_region(self, region: str, generation: int) -> ReconciliationSummary:
        run_id = self.store.create_reconciliation_run(mode="DRY_RUN")
        journal = list(self.store.iter_events(region=region, generation=generation))
        archive = list(self.store.iter_archive(region=region, generation=generation))
        findings: list[Finding] = []
        journal_count = len(journal)
        archive_count = len(archive)
        missing_count = max(journal_count - archive_count, 0)
        duplicate_count = sum(record.duplicate_observation_count for record in archive)
        if journal_count != archive_count:
            findings.append(
                Finding(
                    severity=FindingSeverity.ERROR,
                    finding_type="COUNT_MISMATCH",
                    message="journal and archive counts differ",
                    region=region,
                    generation=generation,
                    expected_value=str(journal_count),
                    observed_value=str(archive_count),
                    remediation_hint="replay the trailing archive gap",
                )
            )
        highest_journal = max(
            (event.identity.origin_sequence for event in journal), default=0
        )
        highest_hub = max((record.hub_stream_sequence for record in archive), default=0)
        archive_origin_floor = contiguous_floor(
            record.identity.origin_sequence for record in archive
        )
        required_consumer_progress: dict[str, int] = {}
        for consumer_name in self.store.required_consumers():
            checkpoint = self.store.checkpoint(consumer_name, region, generation)
            required_consumer_progress[consumer_name] = (
                0 if checkpoint is None else checkpoint.application_sequence
            )
        if highest_hub < highest_journal:
            findings.append(
                Finding(
                    severity=FindingSeverity.ERROR,
                    finding_type="SEQUENCE_LAG",
                    message="hub aggregate sequence is behind the edge sequence",
                    region=region,
                    generation=generation,
                    expected_value=str(highest_journal),
                    observed_value=str(highest_hub),
                )
            )
        checksum = sha256_text(
            f"{region}:{generation}:{journal_count}:{archive_count}:{highest_hub}"
        )
        status = ReconcileStatus.CONVERGED if not findings else ReconcileStatus.DIVERGED
        summary = ReconciliationSummary(
            run_id=run_id,
            status=status,
            journal_event_count=journal_count,
            archive_event_count=archive_count,
            missing_count=missing_count,
            unexpected_count=max(archive_count - journal_count, 0),
            duplicate_count=duplicate_count,
            metadata_mismatch_count=0,
            consumer_lag_count=0,
            highest_contiguous_archive_origin_sequence=archive_origin_floor,
            required_consumer_progress=required_consumer_progress,
            checksum=checksum,
            findings=tuple(findings),
        )
        for finding in findings:
            self.store.add_finding(run_id, finding)
        self.store.finish_reconciliation_run(
            run_id,
            status=summary.status.value,
            journal_event_count=summary.journal_event_count,
            archive_event_count=summary.archive_event_count,
            missing_count=summary.missing_count,
            duplicate_count=summary.duplicate_count,
            metadata_mismatch_count=summary.metadata_mismatch_count,
            consumer_lag_count=summary.consumer_lag_count,
            checksum=summary.checksum,
            summary=summary.as_dict(),
        )
        return summary

    def missing_event_ids(self, region: str, generation: int) -> tuple[str, ...]:
        archive_count = self.store.archive_count(region)
        values = [
            event.identity.event_id
            for event in self.store.iter_events(region=region, generation=generation)
            if event.identity.origin_sequence > archive_count
        ]
        return tuple(values)

    def plan_replay(
        self,
        *,
        region: str,
        generation: int,
        created_by: str,
        reason: str,
        approve: bool = False,
        approved_by: str | None = None,
    ) -> ReplayDecision:
        record = self.store.generation(region, generation)
        if record is None:
            return ReplayDecision(None, (), "unknown generation")
        missing = self.missing_event_ids(region, generation)
        if not missing:
            return ReplayDecision(None, (), None)
        all_events = list(self.store.iter_events(region=region, generation=generation))
        replay_range = ReplayRange(
            region,
            generation,
            min(event.identity.origin_sequence for event in all_events),
            max(event.identity.origin_sequence for event in all_events),
        )
        for active in self.store.active_replay_plans(
            region=region, generation=generation
        ):
            if active.replay_range == replay_range:
                raise ReplayConflict(
                    f"an active replay plan already covers {replay_range.as_dict()}"
                )
        plan = self.store.insert_replay_plan(
            plan_id=f"rp-{region}-g{generation}-{__import__('uuid').uuid4().hex[:10]}",
            replay_range=replay_range,
            status=ReplayStatus.APPROVED if approve else ReplayStatus.DRAFT,
            reason=reason,
            created_by=created_by,
            event_ids=[event.identity.event_id for event in all_events],
            approved_by=approved_by if approve else None,
            approved_at=utcnow() if approve else None,
        )
        return ReplayDecision(plan, tuple(plan.event_ids), None)

    def acquire_recovery_lease(
        self,
        *,
        region: str,
        owner_id: str,
        ttl_seconds: int,
        at: datetime | None = None,
    ) -> LeaseToken:
        now = at or utcnow()
        if ttl_seconds <= 0:
            raise ContractError("ttl_seconds must be positive")
        current = self.store.current_lease(region)
        if current is None:
            epoch = 1
            acquired_at = now
        elif current.owner_id == owner_id:
            epoch = current.fence_epoch
            acquired_at = current.acquired_at
        elif current.expired(now):
            epoch = current.fence_epoch
            acquired_at = now
        else:
            raise FencingError(
                f"recovery lease for {region} is owned by {current.owner_id} until {to_iso(current.expires_at)}"
            )
        return self.store.write_lease(
            region=region,
            owner_id=owner_id,
            fence_epoch=epoch,
            acquired_at=acquired_at,
            renewed_at=now,
            expires_at=now + timedelta(seconds=ttl_seconds),
        )

    def assert_recovery_fence(
        self,
        *,
        region: str,
        owner_id: str,
        fence_epoch: int,
        at: datetime | None = None,
    ) -> LeaseToken:
        current = self.store.current_lease(region)
        if current is None:
            raise FencingError(f"region {region} has no recovery lease")
        if current.owner_id != owner_id:
            raise FencingError(f"region {region} is owned by another recovery worker")
        if current.expired(at or utcnow()):
            raise FencingError(f"region {region} recovery lease has expired")
        return current

    def compute_retention_decision(
        self,
        *,
        region: str,
        generation: int,
        at: datetime | None = None,
        limit: int = 1000,
    ) -> RetentionDecision:
        policy = self.retention_policy(region)
        archive_sequence = self.store.highest_archive_sequence(region, generation)
        consumer_sequence = self.store.slowest_required_consumer_sequence(
            region, generation
        )
        replay_pin = self.store.first_active_replay_sequence(region, generation)
        safe_sequence = archive_sequence
        self.store.write_retention_watermark(
            RetentionWatermark(
                region=region,
                generation=generation,
                archive_sequence=archive_sequence,
                slowest_required_consumer_sequence=consumer_sequence,
                replay_pin_sequence=replay_pin,
                cleanup_safe_sequence=safe_sequence,
                calculated_at=at or utcnow(),
            )
        )
        candidates = self.store.cleanup_candidate_ids(
            region=region,
            generation=generation,
            safe_sequence=safe_sequence,
            minimum_age_seconds=policy.journal_min_age_seconds,
            at=at,
            limit=limit,
        )
        return RetentionDecision(
            region=region,
            generation=generation,
            safe_sequence=safe_sequence,
            archive_sequence=archive_sequence,
            required_consumer_sequence=consumer_sequence,
            replay_pin_sequence=replay_pin,
            eligible_event_ids=tuple(candidates),
            horizon_safe=policy.stream_horizon_safe,
        )

    def derived_subject_for(self, event: EventEnvelope, *, consumer_name: str) -> str:
        return (
            f"telemetry.raw.{event.identity.region}.{consumer_name}.{event.event_type}"
        )

    def consumer_health(self) -> tuple[bool, dict[str, Any]]:
        details: dict[str, Any] = {}
        for consumer_name in self.store.required_consumers():
            checkpoints = self.store.checkpoints(consumer_name)
            details[consumer_name] = [
                checkpoint.as_dict() for checkpoint in checkpoints
            ]
        return True, details
