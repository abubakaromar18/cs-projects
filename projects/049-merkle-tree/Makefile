BIN := bin/merkle

.PHONY: build test cover vet run clean

build:
	go build -o $(BIN) ./cmd/merkle

test:
	go test ./...

cover:
	go test -coverprofile=coverage.out ./...
	go tool cover -func=coverage.out

vet:
	go vet ./...

run: build
	./$(BIN) $(ARGS)

clean:
	rm -rf bin coverage.out coverage.html
