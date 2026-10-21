# The SQLite driver uses cgo, so a C compiler (gcc/clang) must be installed.
export CGO_ENABLED=1

.PHONY: run build test cover vet fmt clean

run:
	go run ./cmd/shortener

build:
	go build -o bin/shortener ./cmd/shortener

test:
	go test -race ./...

cover:
	go test -coverprofile=coverage.out ./... && go tool cover -func=coverage.out

vet:
	go vet ./...

fmt:
	gofmt -w .

clean:
	rm -rf bin coverage.out *.db *.db-shm *.db-wal
