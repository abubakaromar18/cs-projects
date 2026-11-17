.PHONY: all deps test run demo gun format clean

all: test

deps:
	mix deps.get

test:
	mix test

format:
	mix format

run:
	mix life --pattern glider --wrap --gens 40

demo:
	mix life --random --seed 1 --width 60 --height 24 --wrap --gens 200 --delay 60

gun:
	mix life --file examples/gosper-gun.txt --gens 60 --verify

clean:
	rm -rf _build
