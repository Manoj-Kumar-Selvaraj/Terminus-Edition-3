package com.freight.hash;

/** jenkins_oaat over raw bytes. */
public final class JenkinsOaat implements HashAlgorithm {

    @Override
    public String name() {
        return "jenkins_oaat";
    }

    @Override
    public long apply(byte[] data) {
        long state = 0L;
        for (int i = 0; i < data.length; i++) {
            state = (state + (data[i] & 0xFF)) & 0xFFFFFFFFL;
            state = (state + (state << 10)) & 0xFFFFFFFFL;
            state ^= (state >>> 6);
        }
        state = (state + (state << 3)) & 0xFFFFFFFFL;
        state ^= (state >>> 11);
        state = (state + (state << 15)) & 0xFFFFFFFFL;
        return state;
    }
}
