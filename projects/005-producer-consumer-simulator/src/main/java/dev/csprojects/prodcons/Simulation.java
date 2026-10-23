package dev.csprojects.prodcons;

import java.util.ArrayList;
import java.util.List;
import java.util.Random;
import java.util.concurrent.TimeUnit;
import java.util.function.Consumer;

/**
 * Runs producers and consumers against a shared {@link BoundedBuffer} and reports every
 * interesting step to an event listener.
 *
 * <p>Shutdown uses the poison-pill pattern: once all producers have finished, the
 * coordinator inserts one {@link Item#POISON} per consumer. Because the buffer is FIFO,
 * each consumer sees its pill only after every real item ahead of it has been taken.
 */
public final class Simulation {

    private final Config config;
    private final BoundedBuffer<Item> buffer;
    private final Consumer<Event> listener;
    private final Stats stats;
    private long startNanos;

    /**
     * @param listener receives events from many threads concurrently; it must be thread-safe
     */
    public Simulation(Config config, Consumer<Event> listener) {
        this.config = config;
        this.buffer = new BoundedBuffer<>(config.capacity());
        this.listener = listener;
        this.stats = new Stats(config.producers(), config.consumers());
    }

    /** Runs to completion and returns the collected statistics. */
    public Stats run() throws InterruptedException {
        startNanos = System.nanoTime();

        List<Thread> producers = new ArrayList<>();
        for (int id = 1; id <= config.producers(); id++) {
            producers.add(start("producer-" + id, producerTask(id)));
        }
        List<Thread> consumers = new ArrayList<>();
        for (int id = 1; id <= config.consumers(); id++) {
            consumers.add(start("consumer-" + id, consumerTask(id)));
        }

        for (Thread t : producers) {
            t.join();
        }
        // All real items are in (or through) the buffer; tell each consumer to stop.
        for (int i = 0; i < config.consumers(); i++) {
            buffer.put(Item.POISON);
        }
        for (Thread t : consumers) {
            t.join();
        }

        stats.finish(System.nanoTime() - startNanos);
        return stats;
    }

    private static Thread start(String name, Runnable task) {
        Thread t = new Thread(task, name);
        t.start();
        return t;
    }

    private Runnable producerTask(int id) {
        String actor = "P" + id;
        Random rng = new Random(config.seed() * 31 + id);
        return () -> {
            try {
                for (int seq = 1; seq <= config.itemsPerProducer(); seq++) {
                    work(rng, config.produceDelayMs());
                    Item item = new Item(id, seq);
                    // Try without waiting first so we only report a WAIT when we really block.
                    if (!buffer.offer(item, 0, TimeUnit.MILLISECONDS)) {
                        stats.recordProducerBlocked();
                        emit(Event.Type.WAIT_PUT, actor, item);
                        buffer.put(item);
                    }
                    stats.recordProduced(id);
                    emit(Event.Type.PUT, actor, item);
                }
                emit(Event.Type.DONE, actor, null);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        };
    }

    private Runnable consumerTask(int id) {
        String actor = "C" + id;
        Random rng = new Random(config.seed() * 37 + 1000 + id);
        return () -> {
            try {
                while (true) {
                    Item item = buffer.poll(0, TimeUnit.MILLISECONDS);
                    if (item == null) {
                        stats.recordConsumerBlocked();
                        emit(Event.Type.WAIT_TAKE, actor, null);
                        item = buffer.take();
                    }
                    if (item.isPoison()) {
                        break;
                    }
                    stats.recordConsumed(id, item);
                    emit(Event.Type.TAKE, actor, item);
                    work(rng, config.consumeDelayMs());
                }
                emit(Event.Type.DONE, actor, null);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        };
    }

    /** Simulates work: sleeps for mean +/- 50% jitter. */
    private static void work(Random rng, int meanMs) throws InterruptedException {
        if (meanMs == 0) {
            return;
        }
        int jitter = meanMs / 2;
        int ms = meanMs - jitter + rng.nextInt(2 * jitter + 1);
        Thread.sleep(ms);
    }

    private void emit(Event.Type type, String actor, Item item) {
        BoundedBuffer.Snapshot snap = buffer.snapshot();
        stats.observeOccupancy(snap.count());
        listener.accept(new Event(System.nanoTime() - startNanos, type, actor, item, snap));
    }
}
