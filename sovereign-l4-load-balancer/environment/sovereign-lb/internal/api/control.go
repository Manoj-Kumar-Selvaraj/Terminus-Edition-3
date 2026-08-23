package api

import (
	"context"
	"encoding/json"
	"errors"
	"io"
	"log"
	"net"
	"time"

	"sovereign-lb/internal/model"
	"sovereign-lb/internal/protocol"
	"sovereign-lb/internal/snapshot"
)

type nodeSession struct {
	nodeID    string
	sessionID string
	outbound  chan model.Envelope
	sequence  uint64
}

func (service *Service) ServeControl(ctx context.Context, listener net.Listener, maximum uint32) error {
	go func() { <-ctx.Done(); _ = listener.Close() }()
	for {
		connection, err := listener.Accept()
		if err != nil { if ctx.Err() != nil { return nil }; return err }
		go service.serveNode(ctx, connection, maximum)
	}
}

func (service *Service) serveNode(ctx context.Context, connection net.Conn, maximum uint32) {
	defer connection.Close()
	stream := protocol.New(connection, connection, maximum)
	_ = connection.SetReadDeadline(time.Now().Add(15*time.Second))
	hello, err := stream.Read(); if err != nil || hello.Type != "hello" { return }
	zone, _ := hello.Body["zone"].(string); if zone == "" { return }
	service.nodes.Register(hello.NodeID, hello.SessionID, zone, time.Now())
	session := service.addSession(hello.NodeID, hello.SessionID)
	defer service.removeSession(session)
	defer service.nodes.Disconnect(hello.NodeID, hello.SessionID, time.Now())
	_ = connection.SetReadDeadline(time.Time{})
	writeFailed := make(chan struct{})
	go func() {
		defer close(writeFailed)
		for {
			select {
			case <-ctx.Done():
				return
			case envelope, open := <-session.outbound:
				if !open || stream.Write(envelope) != nil { return }
			}
		}
	}()
	for {
		select { case <-ctx.Done(): return; case <-writeFailed: return; default: }
		envelope, readErr := stream.Read()
		if readErr != nil { if !errors.Is(readErr, io.EOF) { log.Printf("node %s control read: %v", hello.NodeID, readErr) }; return }
		if envelope.NodeID != hello.NodeID || envelope.SessionID != hello.SessionID { return }
		if _, acceptErr := service.nodes.Accept(envelope, time.Now()); acceptErr != nil { return }
		if envelope.Type == "prepared" || envelope.Type == "active" || envelope.Type == "rejected" {
			previous, _ := service.rollout.Snapshot()
			state, recordErr := service.rollout.Record(envelope, time.Now(), 15*time.Second)
			if recordErr == nil && previous.Phase == "preparing" && state.Phase == "activating" {
				service.dispatchActivate(state)
			}
			if recordErr == nil && state.Phase == "active" { service.mutex.Lock(); service.active = state.Generation; service.mutex.Unlock(); _ = service.repository.SetCurrent(state.Generation) }
		}
	}
}

func (service *Service) addSession(nodeID, sessionID string) *nodeSession {
	service.mutex.Lock()
	defer service.mutex.Unlock()
	key := nodeID + "\x00" + sessionID
	value := &nodeSession{nodeID: nodeID, sessionID: sessionID, outbound: make(chan model.Envelope, 256)}
	service.sessions[key] = value
	service.metrics.Set("sovereign_current_sessions", int64(len(service.sessions)))
	return value
}

func (service *Service) removeSession(session *nodeSession) {
	service.mutex.Lock()
	defer service.mutex.Unlock()
	key := session.nodeID + "\x00" + session.sessionID
	if service.sessions[key] == session {
		delete(service.sessions, key)
		close(session.outbound)
	}
	service.metrics.Set("sovereign_current_sessions", int64(len(service.sessions)))
}

func (service *Service) dispatchPrepare(compiled snapshot.Compiled) {
	body := map[string]any{}
	encoded, err := json.Marshal(compiled.Snapshot)
	if err != nil { return }
	var snapshotBody any
	if json.Unmarshal(encoded, &snapshotBody) != nil { return }
	body["snapshot"] = snapshotBody
	service.mutex.Lock()
	defer service.mutex.Unlock()
	for _, session := range service.sessions {
		session.sequence++
		envelope := model.Envelope{
			Type: "prepare", NodeID: session.nodeID, SessionID: session.sessionID,
			Sequence: session.sequence, SentAt: time.Now().UTC().Format(time.RFC3339Nano),
			Generation: compiled.Snapshot.Generation, Digest: compiled.Digest, Body: body,
		}
		select {
		case session.outbound <- envelope:
		default:
			service.metrics.Inc("sovereign_control_queue_dropped_total", "message=prepare")
		}
	}
}

func (service *Service) dispatchActivate(state model.Rollout) {
	service.mutex.Lock()
	defer service.mutex.Unlock()
	for nodeID, response := range state.NodeResponses {
		if response.State != "prepared" { continue }
		key := nodeID + "\x00" + response.SessionID
		session, current := service.sessions[key]
		if !current { continue }
		session.sequence++
		envelope := model.Envelope{
			Type: "activate", NodeID: nodeID, SessionID: response.SessionID,
			Sequence: session.sequence, SentAt: time.Now().UTC().Format(time.RFC3339Nano),
			Generation: state.Generation, Digest: state.Digest, Body: map[string]any{},
		}
		select {
		case session.outbound <- envelope:
		default:
			service.metrics.Inc("sovereign_control_queue_dropped_total", "message=activate")
		}
	}
}

func Message(messageType string, node model.NodeStatus, generation uint64, digest string, sequence uint64) model.Envelope { return model.Envelope{Type:messageType,NodeID:node.NodeID,SessionID:node.SessionID,Sequence:sequence,SentAt:time.Now().UTC().Format(time.RFC3339Nano),Generation:generation,Digest:digest,Body:map[string]any{}} }