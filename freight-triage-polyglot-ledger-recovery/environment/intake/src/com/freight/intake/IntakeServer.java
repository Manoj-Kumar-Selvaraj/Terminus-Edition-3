package com.freight.intake;

import com.freight.intake.http.HealthHandler;
import com.freight.intake.http.HoldHandler;
import com.freight.intake.http.JournalHandler;
import com.freight.intake.http.NoteHandler;
import com.freight.intake.http.ReleaseHandler;
import com.sun.net.httpserver.HttpServer;

import java.io.IOException;
import java.net.InetAddress;
import java.net.InetSocketAddress;

/** JDK only HTTP surface for the freight intake API. */
public final class IntakeServer {

    private final HttpServer server;
    private final HoldStore store;

    public IntakeServer(HoldStore store, int port) throws IOException {
        this.store = store;
        InetSocketAddress address = new InetSocketAddress(InetAddress.getByName("127.0.0.1"), port);
        this.server = HttpServer.create(address, 32);
        this.server.createContext("/v2/holds", new HoldHandler(store));
        this.server.createContext("/v2/releases", new ReleaseHandler(store));
        this.server.createContext("/v2/notes", new NoteHandler(store));
        this.server.createContext("/v2/journal", new JournalHandler(store));
        this.server.createContext("/v2/healthz", new HealthHandler());
        this.server.setExecutor(java.util.concurrent.Executors.newFixedThreadPool(4));
    }

    public HoldStore store() {
        return store;
    }

    public int port() {
        return server.getAddress().getPort();
    }

    public String baseUrl() {
        return "http://127.0.0.1:" + port();
    }

    public void start() {
        server.start();
    }

    public void stop() {
        server.stop(0);
        java.util.concurrent.ExecutorService executor =
                (java.util.concurrent.ExecutorService) server.getExecutor();
        if (executor != null) {
            executor.shutdownNow();
        }
    }
}
