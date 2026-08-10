package reactor.core;

import reactor.common.Util;

public final class Service {
    public String ping() {
        return "core+" + Util.tag();
    }
}
