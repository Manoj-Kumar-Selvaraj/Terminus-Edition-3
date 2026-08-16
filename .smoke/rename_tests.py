"""Rename verifier tests onto the workspace F2P/P2P naming convention."""

from pathlib import Path

TARGET = (
    Path(__file__).resolve().parent.parent
    / "codecommit-iam-merge-fence"
    / "tests"
    / "test_outputs.py"
)

RENAMES = {
    "test_clone_only_account_cannot_push": "test_f2p_clone_only_account_cannot_push",
    "test_wildcard_action_stays_inside_its_resource": "test_f2p_wildcard_action_stays_in_resource",
    "test_repository_listing_is_scoped_by_resource": "test_f2p_repository_listing_is_scoped",
    "test_explicit_deny_beats_a_matching_allow": "test_f2p_explicit_deny_beats_matching_allow",
    "test_runner_cannot_deliver_outside_mainline": "test_f2p_runner_cannot_deliver_off_mainline",
    "test_offsite_audit_read_is_denied": "test_f2p_offsite_audit_read_is_denied",
    "test_mainline_push_without_mfa_is_denied": "test_f2p_mainline_push_without_mfa_denied",
    "test_mainline_push_from_offsite_is_denied": "test_f2p_mainline_push_from_offsite_denied",
    "test_conditioned_grant_needs_the_context_key": "test_f2p_conditioned_grant_needs_key",
    "test_reviewer_cannot_stamp_from_offsite": "test_f2p_reviewer_cannot_stamp_offsite",
    "test_single_stamp_does_not_satisfy_mainline_quorum": "test_f2p_single_stamp_misses_quorum",
    "test_repeated_stamp_counts_once": "test_f2p_repeated_stamp_counts_once",
    "test_stamp_from_outside_the_pool_does_not_count": "test_f2p_out_of_pool_stamp_ignored",
    "test_author_cannot_stamp_their_own_request": "test_f2p_author_stamp_does_not_count",
    "test_quorum_merge_is_a_true_fast_forward": "test_f2p_quorum_merge_is_fast_forward",
    "test_stale_destination_cannot_be_landed": "test_f2p_stale_destination_not_landed",
    "test_repeated_delivery_journals_one_event": "test_f2p_repeat_delivery_journals_once",
    "test_ref_spelling_does_not_split_a_delivery": "test_f2p_ref_spelling_shares_delivery",
    "test_journal_row_shape_is_contracted": "test_f2p_journal_row_shape_is_contracted",
    "test_event_id_is_derived_from_the_delivery_coordinates": (
        "test_f2p_event_id_is_coordinate_digest"
    ),
    "test_repeated_delivery_does_not_duplicate_outbox_rows": (
        "test_f2p_delivery_keeps_one_outbox_row"
    ),
    "test_unreachable_endpoint_stops_after_its_attempt_budget": (
        "test_f2p_unreachable_endpoint_dies"
    ),
    "test_failed_attempt_waits_for_its_backoff": "test_f2p_failed_attempt_waits_backoff",
    "test_audit_filters_combine_with_and": "test_f2p_audit_filters_combine_with_and",
    "test_denied_decisions_record_the_attempted_action": "test_f2p_deny_rows_record_the_action",
    "test_api_merge_is_authorized": "test_f2p_api_merge_is_authorized",
    "test_api_merge_respects_the_merge_fence": "test_f2p_api_merge_respects_the_fence",
    "test_api_does_not_assert_mfa_for_the_caller": "test_f2p_api_forwards_caller_mfa_claim",
    "test_unknown_principal_is_a_recorded_denial": "test_f2p_unknown_principal_is_recorded",
    "test_cli_and_api_agree_on_a_denied_request": "test_f2p_cli_and_api_agree_on_denial",
    "test_plane_layout_is_present": "test_p2p_plane_layout_is_present",
    "test_seeded_configuration_is_unchanged": "test_p2p_seeded_configuration_unchanged",
    "test_onboarding_account_can_still_clone": "test_p2p_onboarding_account_can_clone",
    "test_developer_can_push_own_branch": "test_p2p_developer_can_push_own_branch",
    "test_mainline_push_with_mfa_from_office_is_allowed": "test_p2p_mainline_push_with_mfa_ok",
    "test_unknown_repository_reports_not_found": "test_p2p_unknown_repository_not_found",
    "test_security_reader_can_query_from_office": "test_p2p_security_reader_queries_onsite",
    "test_api_health_needs_no_identity": "test_p2p_api_health_needs_no_identity",
    "test_api_server_serves_the_same_router": "test_p2p_api_server_serves_the_router",
    "test_ref_without_a_binding_delivers_nothing": "test_p2p_unbound_ref_delivers_nothing",
    "test_documented_read_surface_answers": "test_p2p_documented_read_surface_answers",
    "test_missing_approval_rule_blocks_a_merge": "test_p2p_missing_rule_blocks_a_merge",
    "test_parked_binding_is_reported_and_not_started": "test_p2p_parked_binding_not_started",
    "test_delivered_row_is_not_sent_twice": "test_p2p_delivered_row_sent_once",
}

if __name__ == "__main__":
    text = TARGET.read_text(encoding="utf-8")
    for old, new in RENAMES.items():
        needle = f"def {old}("
        assert needle in text, f"missing {old}"
        text = text.replace(needle, f"def {new}(")
    TARGET.write_text(text, encoding="utf-8", newline="\n")
    print(f"renamed {len(RENAMES)} tests")
