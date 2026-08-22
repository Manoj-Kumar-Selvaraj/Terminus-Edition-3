package model

import (
	"fmt"
	"net"
	"regexp"
)

var identifier = regexp.MustCompile(`^[a-z][a-z0-9-]{0,62}$`)

func ValidateDesired(value Desired) error {
	if value.Revision == 0 { return fmt.Errorf("revision must be positive") }
	if err := validateLimits(value.Limits); err != nil { return err }
	if len(value.Listeners) == 0 || len(value.Listeners) > value.Limits.MaxListeners { return fmt.Errorf("listener count out of range") }
	if len(value.TargetGroups) == 0 || len(value.TargetGroups) > value.Limits.MaxTargetGroups { return fmt.Errorf("target group count out of range") }
	if value.Rollout.PrepareQuorum < 1 || value.Rollout.ActivateQuorum < 1 { return fmt.Errorf("rollout quorum must be positive") }
	if value.Rollout.PrepareTimeout < 100 || value.Rollout.ActivateTimeout < 100 { return fmt.Errorf("rollout timeout too small") }
	groups := make(map[string]struct{}, len(value.TargetGroups))
	targetCount := 0
	for _, group := range value.TargetGroups {
		if err := validateGroup(group); err != nil { return fmt.Errorf("target group %q: %w", group.Name, err) }
		if _, exists := groups[group.Name]; exists { return fmt.Errorf("duplicate target group %q", group.Name) }
		groups[group.Name] = struct{}{}
		targetCount += len(group.Targets)
	}
	if targetCount > value.Limits.MaxTargets { return fmt.Errorf("target count exceeds limit") }
	listenerNames := map[string]struct{}{}
	binds := map[string]struct{}{}
	for _, listener := range value.Listeners {
		if !identifier.MatchString(listener.Name) { return fmt.Errorf("invalid listener name %q", listener.Name) }
		if net.ParseIP(listener.Address) == nil { return fmt.Errorf("listener %q has invalid address", listener.Name) }
		if listener.Port < 1 || listener.Port > 65535 { return fmt.Errorf("listener %q has invalid port", listener.Name) }
		if _, ok := groups[listener.TargetGroup]; !ok { return fmt.Errorf("listener %q references unknown group", listener.Name) }
		if listener.ConnectTimeout < 1 || listener.IdleTimeout < 1 { return fmt.Errorf("listener %q has invalid timeout", listener.Name) }
		if listener.BufferBytes < 4096 || listener.BufferBytes > value.Limits.MaxBufferBytes { return fmt.Errorf("listener %q has invalid buffer", listener.Name) }
		if _, exists := listenerNames[listener.Name]; exists { return fmt.Errorf("duplicate listener %q", listener.Name) }
		listenerNames[listener.Name] = struct{}{}
		bind := net.JoinHostPort(listener.Address, fmt.Sprint(listener.Port))
		if _, exists := binds[bind]; exists { return fmt.Errorf("duplicate listener address %s", bind) }
		binds[bind] = struct{}{}
	}
	return nil
}

func validateGroup(group TargetGroup) error {
	if !identifier.MatchString(group.Name) { return fmt.Errorf("invalid name") }
	if group.Policy != "round_robin" && group.Policy != "least_connections" && group.Policy != "source_hash" { return fmt.Errorf("invalid balancing policy") }
	if group.ZonePolicy != "cross_zone" && group.ZonePolicy != "same_zone_preferred" { return fmt.Errorf("invalid zone policy") }
	if group.DrainTimeout < 1 { return fmt.Errorf("invalid drain timeout") }
	if len(group.Targets) == 0 { return fmt.Errorf("requires targets") }
	if err := validateHealth(group.Health); err != nil { return err }
	identities := map[string]struct{}{}
	endpoints := map[string]struct{}{}
	for _, target := range group.Targets {
		if !identifier.MatchString(target.ID) || !identifier.MatchString(target.Zone) { return fmt.Errorf("invalid target identity") }
		if net.ParseIP(target.Address) == nil || target.Port < 1 || target.Port > 65535 { return fmt.Errorf("invalid target endpoint") }
		if target.AdministrativeState != "enabled" && target.AdministrativeState != "disabled" && target.AdministrativeState != "draining" { return fmt.Errorf("invalid administrative state") }
		if target.Weight < 1 || target.Weight > 1000 || target.Incarnation == 0 { return fmt.Errorf("invalid target weight or incarnation") }
		identity := target.ID + "/" + fmt.Sprint(target.Incarnation)
		if _, exists := identities[identity]; exists { return fmt.Errorf("duplicate target identity") }
		identities[identity] = struct{}{}
		endpoint := net.JoinHostPort(target.Address, fmt.Sprint(target.Port))
		if _, exists := endpoints[endpoint]; exists { return fmt.Errorf("duplicate target endpoint") }
		endpoints[endpoint] = struct{}{}
	}
	return nil
}

func validateHealth(value HealthPolicy) error {
	if value.Interval < 100 || value.Timeout < 1 || value.Timeout >= value.Interval { return fmt.Errorf("invalid active health timing") }
	if value.HealthyThreshold < 1 || value.UnhealthyThreshold < 1 { return fmt.Errorf("invalid health threshold") }
	if value.PassiveFailures < 1 || value.PassiveWindow < 1 || value.Ejection < 1 { return fmt.Errorf("invalid passive health policy") }
	if len(value.Send) > 256 || len(value.Expect) > 256 { return fmt.Errorf("health payload too long") }
	return nil
}

func validateLimits(value Limits) error {
	values := []int{value.MaxListeners, value.MaxTargetGroups, value.MaxTargets, value.MaxFrameBytes, value.MaxQueueMessages, value.MaxAuditEvents, value.RetainedGenerations, value.MaxHealthSamples, value.MaxConnectionRecords, value.MaxBufferBytes}
	for _, item := range values { if item < 1 { return fmt.Errorf("limits must be positive") } }
	if value.MaxListeners > 1024 || value.MaxTargetGroups > 1024 || value.MaxTargets > 65536 { return fmt.Errorf("configuration limit exceeds hard ceiling") }
	if value.MaxFrameBytes > 16<<20 || value.MaxBufferBytes > 4<<20 { return fmt.Errorf("byte limit exceeds hard ceiling") }
	return nil
}