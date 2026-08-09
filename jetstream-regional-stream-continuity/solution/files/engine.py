from __future__ import annotations

import json
import uuid
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
    LeaseToken,
    PublishAck,
    ReconcileStatus,
    ReconciliationSummary,
    ReplayConflict,
    ReplayRange,
    ReplayStatus,
    collapse_ranges,
    contiguous_floor,
    report_checksum,
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
    """Continuity controller with durable cross-domain invariants."""

    def message_id_for_event(self, event: EventEnvelope, *, attempt_no: int) -> str:
        return event.identity.event_id

    async def publish_event(self, event_id: str, publisher: Publisher) -> PublishAck:
        event = self.store.event_by_id(event_id)
        if event is None:
            raise ContractError(f"event {event_id} is not in the edge journal")
        generation = self.validate_event_generation(event)
        if generation.status is not GenerationStatus.CONFIRMED:
            self.store.mark_held(
                event.identity.event_id, reason="origin generation is not confirmed"
            )
            raise ContractError(
                f"event {event.identity.event_id} belongs to an unconfirmed generation"
            )
        expected_stream = self.expected_stream_for_event(event)
        attempt_no = self._next_attempt(event.identity.event_id)
        message_id = self.message_id_for_event(event, attempt_no=attempt_no)
        attempt_no = self.store.begin_publish_attempt(
            event.identity.event_id,
            message_id=message_id,
            requested_stream=expected_stream,
        )
        try:
            ack = await publisher.publish(
                event,
                message_id=message_id,
                expected_stream=expected_stream,
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
        if ack.stream != expected_stream:
            message = (
                f"publish acknowledgement stream {ack.stream} does not match "
                f"expected {expected_stream}"
            )
            self.store.finish_publish_attempt(
                event.identity.event_id,
                attempt_no,
                outcome="ERROR",
                error_code="ACK_STREAM_MISMATCH",
                error_text=message,
            )
            raise ContractError(message)
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
            self.store.execute(
                "INSERT INTO origin_observations(region,stream_name,domain,stream_fingerprint,first_sequence,last_sequence,observed_at,disposition,detail_json) "
                "VALUES(?,?,?,?,?,?,?,'PENDING_GENERATION',?)",
                (
                    observation.region,
                    observation.stream_name,
                    observation.domain,
                    observation.stream_fingerprint,
                    observation.first_sequence,
                    observation.last_sequence,
                    to_iso(observation.observed_at),
                    json.dumps({"generation": pending.generation}, sort_keys=True),
                ),
            )
            return pending
        if observation.stream_fingerprint == current.stream_fingerprint:
            if observation.first_sequence > current.last_observed_sequence + 1:
                raise ContractError(
                    f"origin {observation.region} skipped from {current.last_observed_sequence} "
                    f"to {observation.first_sequence} without a generation transition"
                )
            self.store.update_generation_high_watermark(
                observation.region,
                current.generation,
                observation.last_sequence,
            )
            self.store.execute(
                "INSERT INTO origin_observations(region,stream_name,domain,stream_fingerprint,first_sequence,last_sequence,observed_at,disposition,detail_json) "
                "VALUES(?,?,?,?,?,?,?,'MATCH',?)",
                (
                    observation.region,
                    observation.stream_name,
                    observation.domain,
                    observation.stream_fingerprint,
                    observation.first_sequence,
                    observation.last_sequence,
                    to_iso(observation.observed_at),
                    json.dumps({"generation": current.generation}, sort_keys=True),
                ),
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
        elif pending.stream_fingerprint != observation.stream_fingerprint:
            raise ContractError(
                f"region {observation.region} has a different pending generation fingerprint"
            )
        else:
            self.store.update_generation_high_watermark(
                observation.region,
                pending.generation,
                observation.last_sequence,
            )
        self.store.execute(
            "INSERT INTO origin_observations(region,stream_name,domain,stream_fingerprint,first_sequence,last_sequence,observed_at,disposition,detail_json) "
            "VALUES(?,?,?,?,?,?,?,'PENDING_GENERATION',?)",
            (
                observation.region,
                observation.stream_name,
                observation.domain,
                observation.stream_fingerprint,
                observation.first_sequence,
                observation.last_sequence,
                to_iso(observation.observed_at),
                json.dumps(
                    {
                        "generation": pending.generation,
                        "previous_generation": current.generation,
                        "operator_approval_required": True,
                    },
                    sort_keys=True,
                ),
            ),
        )
        return pending

    def _dispatch_count(self, consumer_name: str, event_id: str) -> int:
        value = self.store.scalar(
            "SELECT COUNT(*) FROM effect_dispatches WHERE consumer_name=? AND event_id=? AND state='CONFIRMED'",
            (consumer_name, event_id),
        )
        return int(value or 0)

    def _emit_dispatch_once(
        self,
        *,
        consumer_name: str,
        event: EventEnvelope,
        worker_id: str,
        fence_epoch: int,
        detail: Mapping[str, Any],
    ) -> bool:
        if self._dispatch_count(consumer_name, event.identity.event_id) > 0:
            return False
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
                json.dumps(dict(detail), sort_keys=True, separators=(",", ":")),
            ),
        )
        return True

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
            self.store.set_jetstream_ack_floor(
                consumer_name=delivery.consumer_name,
                region=event.identity.region,
                generation=event.identity.generation,
                ack_floor=delivery.jetstream_ack_floor,
            )
            return ProcessingResult(
                consumer_name=delivery.consumer_name,
                event_id=event.identity.event_id,
                status="QUARANTINED",
                duplicate_effect=False,
                checkpoint=self.store.checkpoint(
                    delivery.consumer_name,
                    event.identity.region,
                    event.identity.generation,
                ),
                detail={
                    "delivery_count": delivery.delivery_count,
                    "effect_complete": False,
                },
            )

        existing = self.store.effect(delivery.consumer_name, event.identity.event_id)
        duplicate_effect = (
            existing is not None and existing.status is EffectStatus.COMMITTED
        )
        payload = self._consumer_effect_payload(delivery.consumer_name, event)
        if not duplicate_effect:
            effect = self.store.prepare_effect(
                consumer_name=delivery.consumer_name,
                event=event,
                effect_type=self._consumer_effect_type(delivery.consumer_name),
                effect_payload=payload,
                worker_id=worker_id,
                fence_epoch=fence_epoch,
            )
            self._emit_dispatch_once(
                consumer_name=delivery.consumer_name,
                event=event,
                worker_id=worker_id,
                fence_epoch=fence_epoch,
                detail=payload,
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
        checkpoint = self.store.advance_ack_checkpoint(
            consumer_name=delivery.consumer_name,
            identity=event.identity,
            jetstream_ack_floor=delivery.jetstream_ack_floor,
        )
        return ProcessingResult(
            consumer_name=delivery.consumer_name,
            event_id=event.identity.event_id,
            status="COMMITTED",
            duplicate_effect=duplicate_effect,
            checkpoint=checkpoint,
            detail={
                "delivery_count": delivery.delivery_count,
                "worker_id": worker_id,
                "dispatch_count": self._dispatch_count(
                    delivery.consumer_name,
                    event.identity.event_id,
                ),
            },
        )

    def reconcile_region(self, region: str, generation: int) -> ReconciliationSummary:
        run_id = self.store.create_reconciliation_run(mode="DRY_RUN")
        journal_by_id = {
            event.identity.event_id: event
            for event in self.store.iter_events(region=region, generation=generation)
        }
        archive_by_id = {
            record.identity.event_id: record
            for record in self.store.iter_archive(region=region, generation=generation)
        }
        journal_ids = set(journal_by_id)
        archive_ids = set(archive_by_id)
        missing_ids = sorted(journal_ids - archive_ids)
        unexpected_ids = sorted(archive_ids - journal_ids)
        findings: list[Finding] = []
        metadata_mismatch_count = 0

        for event_id in missing_ids:
            event = journal_by_id[event_id]
            findings.append(
                Finding(
                    severity=FindingSeverity.ERROR,
                    finding_type="MISSING_ARCHIVE_EVENT",
                    message="accepted edge event is absent from the hub archive",
                    region=region,
                    generation=generation,
                    origin_sequence=event.identity.origin_sequence,
                    event_id=event_id,
                    expected_value="present",
                    observed_value="missing",
                    remediation_hint="replay this stable event identity after validating its origin generation",
                )
            )
        for event_id in unexpected_ids:
            record = archive_by_id[event_id]
            findings.append(
                Finding(
                    severity=FindingSeverity.BLOCKER,
                    finding_type="UNEXPECTED_ARCHIVE_EVENT",
                    message="hub raw archive contains an event outside the edge journal authority",
                    region=region,
                    generation=generation,
                    origin_sequence=record.identity.origin_sequence,
                    event_id=event_id,
                    expected_value="absent",
                    observed_value="present",
                    remediation_hint="identify the local/raw write path before continuing replay",
                )
            )
        for event_id in sorted(journal_ids & archive_ids):
            event = journal_by_id[event_id]
            record = archive_by_id[event_id]
            mismatches: list[str] = []
            if event.identity.region != record.identity.region:
                mismatches.append("region")
            if event.identity.generation != record.identity.generation:
                mismatches.append("generation")
            if event.identity.origin_sequence != record.identity.origin_sequence:
                mismatches.append("origin_sequence")
            if event.payload_sha256.lower() != record.payload_sha256.lower():
                mismatches.append("payload_sha256")
            if mismatches:
                metadata_mismatch_count += 1
                findings.append(
                    Finding(
                        severity=FindingSeverity.BLOCKER,
                        finding_type="ARCHIVE_METADATA_MISMATCH",
                        message="archive event identity metadata disagrees with its edge journal authority",
                        region=region,
                        generation=generation,
                        origin_sequence=event.identity.origin_sequence,
                        event_id=event_id,
                        expected_value=",".join(mismatches),
                        observed_value="mismatch",
                        remediation_hint="hold the affected generation and repair source identity propagation",
                    )
                )

        duplicate_count = sum(
            record.duplicate_observation_count for record in archive_by_id.values()
        )
        if duplicate_count:
            findings.append(
                Finding(
                    severity=FindingSeverity.WARNING,
                    finding_type="DUPLICATE_OBSERVATIONS",
                    message="the archive observed duplicate deliveries for stable event identities",
                    region=region,
                    generation=generation,
                    expected_value="0",
                    observed_value=str(duplicate_count),
                    remediation_hint="retain stable message ids and application idempotency; server duplicate windows are not replay authority",
                )
            )

        archive_sequences = [
            record.identity.origin_sequence for record in archive_by_id.values()
        ]
        archive_floor = contiguous_floor(archive_sequences)
        journal_sequences = [
            event.identity.origin_sequence for event in journal_by_id.values()
        ]
        journal_floor = contiguous_floor(journal_sequences)
        target = min(journal_floor, archive_floor)
        consumer_findings = self._required_consumer_lag(region, generation, target)
        findings.extend(consumer_findings)

        checksum = report_checksum(archive_by_id.values())
        blocking = [
            finding
            for finding in findings
            if finding.severity in {FindingSeverity.ERROR, FindingSeverity.BLOCKER}
        ]
        summary = ReconciliationSummary(
            run_id=run_id,
            status=ReconcileStatus.CONVERGED
            if not blocking
            else ReconcileStatus.DIVERGED,
            journal_event_count=len(journal_by_id),
            archive_event_count=len(archive_by_id),
            missing_count=len(missing_ids),
            unexpected_count=len(unexpected_ids),
            duplicate_count=duplicate_count,
            metadata_mismatch_count=metadata_mismatch_count,
            consumer_lag_count=len(consumer_findings),
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
        journal_ids = {
            event.identity.event_id
            for event in self.store.iter_events(region=region, generation=generation)
        }
        archive_ids = self.store.archive_identity_set(region, generation)
        return tuple(sorted(journal_ids - archive_ids))

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
        generation_record = self.store.generation(region, generation)
        if generation_record is None:
            return ReplayDecision(None, (), "unknown generation")
        if generation_record.status is not GenerationStatus.CONFIRMED:
            return ReplayDecision(
                None, (), "origin generation requires operator approval"
            )
        missing = self.missing_event_ids(region, generation)
        if not missing:
            return ReplayDecision(None, (), None)
        missing_events = [self.store.event_by_id(event_id) for event_id in missing]
        missing_events = [event for event in missing_events if event is not None]
        sequences = [event.identity.origin_sequence for event in missing_events]
        ranges = collapse_ranges(sequences, region=region, generation=generation)
        replay_range = ReplayRange(region, generation, min(sequences), max(sequences))
        for active in self.store.active_replay_plans(
            region=region, generation=generation
        ):
            if active.replay_range.overlaps(replay_range):
                raise ReplayConflict(
                    f"active replay plan {active.plan_id} overlaps requested range {replay_range.as_dict()}"
                )
        plan_id = f"rp-{region}-g{generation}-{uuid.uuid4().hex[:10]}"
        status = ReplayStatus.APPROVED if approve else ReplayStatus.DRAFT
        plan = self.store.insert_replay_plan(
            plan_id=plan_id,
            replay_range=replay_range,
            status=status,
            reason=reason,
            created_by=created_by,
            event_ids=missing,
            approved_by=approved_by if approve else None,
            approved_at=utcnow() if approve else None,
        )
        return ReplayDecision(plan, missing, None)

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
        elif current.owner_id == owner_id and not current.expired(now):
            epoch = current.fence_epoch
            acquired_at = current.acquired_at
        elif current.expired(now):
            epoch = current.fence_epoch + 1
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
        current.assert_current(
            owner_id=owner_id,
            fence_epoch=fence_epoch,
            at=at or utcnow(),
        )
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
        archive_sequences = [
            record.identity.origin_sequence
            for record in self.store.iter_archive(region=region, generation=generation)
        ]
        archive_sequence = contiguous_floor(archive_sequences)
        consumer_sequence = self.store.slowest_required_consumer_sequence(
            region, generation
        )
        replay_pin = self.store.first_active_replay_sequence(region, generation)
        candidates_for_min = [archive_sequence, consumer_sequence]
        if replay_pin is not None:
            candidates_for_min.append(max(replay_pin - 1, 0))
        safe_sequence = min(candidates_for_min) if candidates_for_min else 0
        watermark = RetentionWatermark(
            region=region,
            generation=generation,
            archive_sequence=archive_sequence,
            slowest_required_consumer_sequence=consumer_sequence,
            replay_pin_sequence=replay_pin,
            cleanup_safe_sequence=safe_sequence,
            calculated_at=at or utcnow(),
        )
        self.store.write_retention_watermark(watermark)
        event_ids = self.store.cleanup_candidate_ids(
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
            eligible_event_ids=tuple(event_ids),
            horizon_safe=policy.stream_horizon_safe,
        )

    def derived_subject_for(self, event: EventEnvelope, *, consumer_name: str) -> str:
        safe_consumer = consumer_name.replace("_", "-")
        return f"telemetry.derived.{event.identity.region}.{safe_consumer}.{event.event_type}"

    def consumer_health(self) -> tuple[bool, dict[str, Any]]:
        details: dict[str, Any] = {}
        ok = True
        for consumer_name in self.store.required_consumers():
            checkpoints = self.store.checkpoints(consumer_name)
            details[consumer_name] = [
                checkpoint.as_dict() for checkpoint in checkpoints
            ]
            for checkpoint in checkpoints:
                if not checkpoint.is_consistent:
                    ok = False
        return ok, details
