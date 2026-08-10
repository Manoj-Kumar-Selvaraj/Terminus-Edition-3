package reactor.web;

import reactor.core.Service;

public final class App {
    public static void main(String[] args) {
        System.out.println(new Service().ping());
    }
}
