package bootstrap

import (
	"context"
	"errors"
	"fmt"
	"log/slog"
	"os"
	"os/signal"
	"sync"
	"syscall"
	"time"

	"edge-router/internal/admin"
	"edge-router/internal/checkpoint"
	"edge-router/internal/compiler"
	"edge-router/internal/config"
	"edge-router/internal/drain"
	"edge-router/internal/health"
	"edge-router/internal/reconcile"
	"edge-router/internal/router"
	rt "edge-router/internal/runtime"
	"edge-router/internal/selection"
	"edge-router/internal/telemetry"
	"edge-router/internal/upstream"
)

type Options struct {
	ConfigPath string
	StateDir string
	ListenAddr string
	AdminAddr string
	LogLevel slog.Level
}

type App struct {
	options Options
	logger *slog.Logger
	registry *rt.Registry
	store *rt.PublicationStore
	ingress *config.Ingress
	compiler *compiler.Compiler
	checkpoints *checkpoint.Store
	reconciler *reconcile.Reconciler
	health *health.Manager
	drain *drain.Manager
	metrics *telemetry.Registry
	selector *selection.Engine
	transport *upstream.Transport
	dataPlane *router.Server
	admin *admin.Server
	cancel context.CancelFunc
	wg sync.WaitGroup
}

func New(options Options) (*App, error) {
	if options.ConfigPath == "" {
		return nil, errors.New("config path is required")
	}
	if options.StateDir == "" {
		return nil, errors.New("state directory is required")
	}
	if options.ListenAddr == "" {
		options.ListenAddr = ":8080"
	}
	if options.AdminAddr == "" {
		options.AdminAddr = "127.0.0.1:9901"
	}
	logger := slog.New(slog.NewJSONHandler(os.Stderr, &slog.HandlerOptions{Level: options.LogLevel}))
	registry := rt.NewRegistry()
	store := rt.NewPublicationStore()
	ingress := config.NewIngress(64)
	compilerInstance := compiler.New(registry)
	checkpoints := checkpoint.New(options.StateDir)
	reconcilerInstance := reconcile.New(ingress, compilerInstance, store, checkpoints, registry)
	healthManager := health.New(registry)
	drainManager := drain.New(registry)
	metrics := telemetry.New()
	selector := selection.New(registry, store)
	transport := upstream.New()
	dataPlane := router.New(options.ListenAddr, store, selector, transport, metrics, logger)
	adminPlane := admin.New(options.AdminAddr, ingress, reconcilerInstance, store, registry, healthManager, drainManager, checkpoints, metrics, logger)
	app := &App{
		options: options,
		logger: logger,
		registry: registry,
		store: store,
		ingress: ingress,
		compiler: compilerInstance,
		checkpoints: checkpoints,
		reconciler: reconcilerInstance,
		health: healthManager,
		drain: drainManager,
		metrics: metrics,
		selector: selector,
		transport: transport,
		dataPlane: dataPlane,
		admin: adminPlane,
	}
	app.configureHooks()
	return app, nil
}

func (a *App) configureHooks() {
	a.reconciler.SetPublishHook(func(previous, current *rt.RuntimeSnapshot) {
		if current == nil {
			return
		}
		owner := telemetry.GenerationOwner(current.Generation)
		a.metrics.Set(owner, "edge_router_generation", nil, float64(current.Generation))
		a.metrics.Set(owner, "edge_router_routes", nil, float64(len(current.Routes)))
		a.metrics.Set(owner, "edge_router_pools", nil, float64(len(current.Pools)))
		if previous == nil {
			return
		}
		currentIDs := make(map[string]struct{})
		for _, pool := range current.Pools {
			for _, endpoint := range pool.Endpoints {
				currentIDs[endpoint.Identity] = struct{}{}
			}
		}
		for _, pool := range previous.Pools {
			for _, endpoint := range pool.Endpoints {
				if _, present := currentIDs[endpoint.Identity]; present || endpoint.Runtime == nil {
					continue
				}
				timeout := time.Duration(pool.Drain.TimeoutMillis) * time.Millisecond
				a.drain.Begin(endpoint.Runtime, timeout)
				a.transport.CloseEndpoint(endpoint.Runtime)
			}
		}
	})
}

func (a *App) ValidateConfig() error {
	state, err := config.ParseFile(a.options.ConfigPath)
	if err != nil {
		return err
	}
	validation := config.Validate(state)
	if err := config.ValidationErrors(validation); err != nil {
		return err
	}
	_, err = a.compiler.Compile(validation.State, 1)
	return err
}

func (a *App) Start(ctx context.Context) error {
	if err := a.checkpoints.Ensure(); err != nil {
		return err
	}
	if err := a.checkpoints.DurabilityProbe(); err != nil {
		return fmt.Errorf("state directory durability probe: %w", err)
	}
	bootstrapState, err := config.ParseFile(a.options.ConfigPath)
	if err != nil {
		return fmt.Errorf("load bootstrap configuration: %w", err)
	}
	validation := config.Validate(bootstrapState)
	if err := config.ValidationErrors(validation); err != nil {
		return fmt.Errorf("validate bootstrap configuration: %w", err)
	}
	rootCtx, cancel := context.WithCancel(ctx)
	a.cancel = cancel

	a.wg.Add(1)
	go func() {
		defer a.wg.Done()
		if err := a.reconciler.Run(rootCtx); err != nil && rootCtx.Err() == nil {
			a.logger.Error("reconciler stopped", "error", err)
			cancel()
		}
	}()

	body, source, recoverErr := a.checkpoints.Recover(&validation.State)
	if recoverErr == nil && source == "current" {
		if _, err := a.reconciler.Recover(body); err != nil {
			return fmt.Errorf("recover runtime snapshot: %w", err)
		}
		a.ingress.InstallRecoveredSources(body.SourceRevisions, body.SourceDigests)
	} else {
		if _, err := a.reconciler.Bootstrap(validation.State); err != nil {
			return fmt.Errorf("publish bootstrap runtime snapshot: %w", err)
		}
	}

	a.dataPlane.SetReady(true)
	a.startBackground(rootCtx)
	return nil
}

func (a *App) startBackground(ctx context.Context) {
	a.wg.Add(1)
	go func() {
		defer a.wg.Done()
		if err := a.health.Run(ctx, a.store); err != nil && ctx.Err() == nil {
			a.logger.Error("health manager stopped", "error", err)
		}
	}()
	a.wg.Add(1)
	go func() {
		defer a.wg.Done()
		if err := a.drain.Run(ctx); err != nil && ctx.Err() == nil {
			a.logger.Error("drain manager stopped", "error", err)
		}
	}()
	a.wg.Add(1)
	go func() {
		defer a.wg.Done()
		if err := a.dataPlane.ListenAndServe(); err != nil && ctx.Err() == nil {
			a.logger.Error("data plane stopped", "error", err)
			a.cancel()
		}
	}()
	a.wg.Add(1)
	go func() {
		defer a.wg.Done()
		if err := a.admin.ListenAndServe(); err != nil && ctx.Err() == nil {
			a.logger.Error("admin plane stopped", "error", err)
			a.cancel()
		}
	}()
}

func (a *App) WaitForSignal(ctx context.Context) error {
	signalContext, stop := signal.NotifyContext(ctx, syscall.SIGINT, syscall.SIGTERM)
	defer stop()
	<-signalContext.Done()
	return a.Shutdown(context.Background())
}

func (a *App) Shutdown(ctx context.Context) error {
	if a.cancel != nil {
		a.cancel()
	}
	a.dataPlane.SetReady(false)
	a.reconciler.SetReady(false)
	shutdownCtx, cancel := context.WithTimeout(ctx, 15*time.Second)
	defer cancel()
	var firstErr error
	if err := a.admin.Shutdown(shutdownCtx); err != nil && firstErr == nil {
		firstErr = err
	}
	if err := a.dataPlane.Shutdown(shutdownCtx); err != nil && firstErr == nil {
		firstErr = err
	}
	a.ingress.Close()
	a.transport.CloseAll()
	done := make(chan struct{})
	go func() {
		a.wg.Wait()
		close(done)
	}()
	select {
	case <-done:
	case <-shutdownCtx.Done():
		if firstErr == nil {
			firstErr = shutdownCtx.Err()
		}
	}
	return firstErr
}

func (a *App) Status() reconcile.Status {
	return a.reconciler.Status()
}
