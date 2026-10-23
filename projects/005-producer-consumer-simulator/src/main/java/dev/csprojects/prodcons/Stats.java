package dev.csprojects.prodcons;

import java.util.Arrays;
import java.util.Collections;
import java.util.HashSet;
import java.util.Set;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.atomic.AtomicIntegerArray;

/**
 * Thread-safe counters gathered while the simulation runs. Atomics are used instead of
 * locks because each update is a single independent increment.
 */
public final class Stats {

    private final AtomicIntegerArray producedBy;
    private final AtomicIntegerArray consumedBy;
    private final AtomicInteger producerBlocks = new AtomicInteger();
    private final AtomicInteger consumerBlocks = new AtomicInteger();
    private final AtomicInteger maxOccupancy = new AtomicInteger();
    private final Set<Item> consumedItems = ConcurrentHashMap.newKeySet();
    private final AtomicInteger duplicateTakes = new AtomicInteger();
    private volatile long elapsedNanos;

    Stats(int producers, int consumers) {
        this.producedBy = new AtomicIntegerArray(producers);
        this.consumedBy = new AtomicIntegerArray(consumers);
    }

    void recordProduced(int producerId) {
        producedBy.incrementAndGet(producerId - 1);
    }

    void recordConsumed(int consumerId, Item item) {
        consumedBy.incrementAndGet(consumerId - 1);
        if (!consumedItems.add(item)) {
            duplicateTakes.incrementAndGet(); // would indicate a broken buffer
        }
    }

    void recordProducerBlocked() {
        producerBlocks.incrementAndGet();
    }

    void recordConsumerBlocked() {
        consumerBlocks.incrementAndGet();
    }

    void observeOccupancy(int n) {
        maxOccupancy.accumulateAndGet(n, Math::max);
    }

    void finish(long nanos) {
        this.elapsedNanos = nanos;
    }

    public int produced() {
        return sum(producedBy);
    }

    public int consumed() {
        return sum(consumedBy);
    }

    public int producedBy(int producerId) {
        return producedBy.get(producerId - 1);
    }

    public int consumedBy(int consumerId) {
        return consumedBy.get(consumerId - 1);
    }

    public int producerBlocks() {
        return producerBlocks.get();
    }

    public int consumerBlocks() {
        return consumerBlocks.get();
    }

    public int maxOccupancy() {
        return maxOccupancy.get();
    }

    public int duplicateTakes() {
        return duplicateTakes.get();
    }

    public Set<Item> consumedItems() {
        return Collections.unmodifiableSet(new HashSet<>(consumedItems));
    }

    public double elapsedMillis() {
        return elapsedNanos / 1_000_000.0;
    }

    /** Items consumed per second of wall-clock time. */
    public double throughput() {
        return elapsedNanos == 0 ? 0 : consumed() / (elapsedNanos / 1e9);
    }

    public String summary(int capacity) {
        StringBuilder sb = new StringBuilder();
        sb.append("Summary\n");
        sb.append(String.format("  elapsed            %.1f ms%n", elapsedMillis()));
        sb.append(String.format("  produced/consumed  %d / %d%n", produced(), consumed()));
        sb.append(String.format("  throughput         %.1f items/s%n", throughput()));
        sb.append(String.format("  peak occupancy     %d / %d%n", maxOccupancy(), capacity));
        sb.append(String.format("  producer blocks    %d  (buffer full)%n", producerBlocks()));
        sb.append(String.format("  consumer blocks    %d  (buffer empty)%n", consumerBlocks()));
        sb.append("  per consumer       ").append(perConsumer()).append('\n');
        sb.append("  integrity          ")
          .append(duplicateTakes() == 0 && produced() == consumed() ? "OK (every item consumed exactly once)"
                  : "BROKEN (" + duplicateTakes() + " duplicates)")
          .append('\n');
        return sb.toString();
    }

    private String perConsumer() {
        String[] parts = new String[consumedBy.length()];
        for (int i = 0; i < parts.length; i++) {
            parts[i] = "C" + (i + 1) + "=" + consumedBy.get(i);
        }
        return String.join("  ", Arrays.asList(parts));
    }

    private static int sum(AtomicIntegerArray a) {
        int s = 0;
        for (int i = 0; i < a.length(); i++) {
            s += a.get(i);
        }
        return s;
    }
}
