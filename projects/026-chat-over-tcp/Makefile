ADDR ?= 127.0.0.1:9000

.PHONY: server client build test cover vet fmt clean

server:
	go run ./cmd/chat-server -addr $(ADDR)

client:
	go run ./cmd/chat-client -addr $(ADDR)

build:
	go build -o bin/chat-server ./cmd/chat-server
	go build -o bin/chat-client ./cmd/chat-client

test:
	go test -race ./...

cover:
	go test -coverprofile=coverage.out ./... && go tool cover -func=coverage.out

vet:
	go vet ./...

fmt:
	gofmt -w .

clean:
	rm -rf bin coverage.out
