.PHONY: all go java corpus clean

all: go java corpus

go:
	go build -o bin/pii-control ./cmd/pii-control
	go build -o bin/piictl ./cmd/piictl

java:
	mvn -q -f worker/pom.xml -DskipTests package
	cp worker/target/pii-worker.jar bin/pii-worker.jar

corpus:
	python3 tools/generate_corpus.py --output corpus --records 12000

clean:
	rm -rf bin worker/target corpus state reports