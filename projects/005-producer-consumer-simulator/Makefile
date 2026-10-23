# Convenience targets wrapping Maven.
JAR := target/producer-consumer-simulator-1.0.0.jar

.PHONY: build test run clean

build:
	mvn -q -B package -DskipTests

test:
	mvn -B test

run: build
	java -jar $(JAR) $(ARGS)

clean:
	mvn -q clean
