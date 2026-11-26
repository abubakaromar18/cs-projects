BIN := bin/serialterm

.PHONY: build test race vet cross clean

build:
	go build -o $(BIN) ./cmd/serialterm

test:
	go test ./...

race:
	go test -race ./...

vet:
	go vet ./...

# Compile-check every back-end from any host.
cross:
	GOOS=linux   GOARCH=amd64 go build -o /dev/null ./...
	GOOS=darwin  GOARCH=arm64 go build -o /dev/null ./...
	GOOS=windows GOARCH=amd64 go build -o /dev/null ./...

clean:
	rm -rf bin
