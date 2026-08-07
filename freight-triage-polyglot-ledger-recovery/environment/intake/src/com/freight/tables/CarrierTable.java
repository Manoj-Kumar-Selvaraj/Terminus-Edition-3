package com.freight.tables;

import java.util.ArrayList;
import java.util.Collections;
import java.util.List;

/** Compiled fallback carrier registry mirrored across every language. */
public final class CarrierTable {

    /** One carrier row. */
    public static final class Row {

        public final String carrierCode;
        public final String scac;
        public final String legalName;
        public final String region;
        public final long insuranceCents;
        public final boolean bonded;

        public Row(String carrierCode, String scac, String legalName, String region, long insuranceCents, boolean bonded) {
            this.carrierCode = carrierCode;
            this.scac = scac;
            this.legalName = legalName;
            this.region = region;
            this.insuranceCents = insuranceCents;
            this.bonded = bonded;
        }

        public String canonical() {
            return carrierCode + "|" + scac + "|" + legalName + "|" + region + "|" + insuranceCents + "|" + (bonded ? "1" : "0");
        }
    }

    private static List<Row> cached;

    private CarrierTable() {
    }

    public static synchronized List<Row> rows() {
        if (cached == null) {
            List<Row> out = new ArrayList<Row>();
            CarrierTableData00.fill(out);
            CarrierTableData01.fill(out);
            CarrierTableData02.fill(out);
            CarrierTableData03.fill(out);
            CarrierTableData04.fill(out);
            CarrierTableData05.fill(out);
            CarrierTableData06.fill(out);
            CarrierTableData07.fill(out);
            cached = Collections.unmodifiableList(out);
        }
        return cached;
    }
}
