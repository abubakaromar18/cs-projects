package dev.csprojects.prodcons;

import static org.junit.jupiter.api.Assertions.*;

import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;
import java.util.concurrent.Future;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicBoolean;
import java.util.concurrent.atomic.AtomicInteger;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;

@Timeout(10)
class BoundedBufferTest {

    @Test
    void rejectsNonPositiveCapacity() {
        assertThrows(IllegalArgumentException.class, () -> new BoundedBuffer<Integer>(0));
        assertThrows(IllegalArgumentException.class, () -> new BoundedBuffer<Integer>(-3));
    }

    @Test
    void isFifoAndWrapsAround() throws InterruptedException {
        BoundedBuffer<Integer> buf = new BoundedBuffer<>(3);
        // Push 10 items through a 3-slot ring so head/tail wrap several times.
        List<Integer> out = new ArrayList<>();
        for (int i = 0; i < 10; i++) {
            buf.put(i);
            if (buf.size() == 3) {
                out.add(buf.take());
            }
        }
        while (buf.size() > 0) {
            out.add(buf.take());
        }
        assertEquals(List.of(0, 1, 2, 3, 4, 5, 6, 7, 8, 9), out);
    }

    @Test
    void offerTimesOutWhenFull() throws InterruptedException {
        BoundedBuffer<String> buf = new BoundedBuffer<>(2);
        assertTrue(buf.offer("a", 0, TimeUnit.MILLISECONDS));
        assertTrue(buf.offer("b", 0, TimeUnit.MILLISECONDS));
        assertFalse(buf.offer("c", 20, TimeUnit.MILLISECONDS));
        assertEquals(2, buf.size());
    }

    @Test
    void pollTimesOutWhenEmpty() throws InterruptedException {
        BoundedBuffer<String> buf = new BoundedBuffer<>(2);
        assertNull(buf.poll(20, TimeUnit.MILLISECONDS));
    }

    @Test
    void putBlocksUntilConsumerFreesASlot() throws Exception {
        BoundedBuffer<Integer> buf = new BoundedBuffer<>(1);
        buf.put(1);

        AtomicBoolean secondPutDone = new AtomicBoolean(false);
        CountDownLatch started = new CountDownLatch(1);
        Thread producer = new Thread(() -> {
            try {
                started.countDown();
                buf.put(2);
                secondPutDone.set(true);
            } catch (InterruptedException e) {
                Thread.currentThread().interrupt();
            }
        });
        producer.start();
        started.await();
        Thread.sleep(100);
        assertFalse(secondPutDone.get(), "put must block while the buffer is full");
        assertEquals(Thread.State.WAITING, producer.getState());

        assertEquals(1, buf.take());
        producer.join(2000);
        assertTrue(secondPutDone.get(), "put must resume once a slot frees up");
        assertEquals(2, buf.take());
    }

    @Test
    void takeBlocksUntilProducerAddsAnItem() throws Exception {
        BoundedBuffer<String> buf = new BoundedBuffer<>(2);
        ExecutorService ex = Executors.newSingleThreadExecutor();
        try {
            Future<String> taken = ex.submit(buf::take);
            Thread.sleep(100);
            assertFalse(taken.isDone(), "take must block while the buffer is empty");
            buf.put("hello");
            assertEquals("hello", taken.get(2, TimeUnit.SECONDS));
        } finally {
            ex.shutdownNow();
        }
    }

    @Test
    void manyProducersAndConsumersLoseAndDuplicateNothing() throws Exception {
        final int producers = 4, consumers = 4, perProducer = 2_000, capacity = 8;
        BoundedBuffer<Integer> buf = new BoundedBuffer<>(capacity);
        Set<Integer> seen = Collections.synchronizedSet(new HashSet<>());
        AtomicInteger duplicates = new AtomicInteger();
        AtomicInteger maxSeen = new AtomicInteger();

        ExecutorService pool = Executors.newFixedThreadPool(producers + consumers);
        List<Future<?>> futures = new ArrayList<>();
        for (int p = 0; p < producers; p++) {
            final int base = p * perProducer;
            futures.add(pool.submit(() -> {
                for (int i = 0; i < perProducer; i++) {
                    buf.put(base + i);
                    maxSeen.accumulateAndGet(buf.size(), Math::max);
                }
                return null;
            }));
        }
        final int perConsumer = producers * perProducer / consumers;
        for (int c = 0; c < consumers; c++) {
            futures.add(pool.submit(() -> {
                for (int i = 0; i < perConsumer; i++) {
                    if (!seen.add(buf.take())) {
                        duplicates.incrementAndGet();
                    }
                }
                return null;
            }));
        }
        for (Future<?> f : futures) {
            f.get(8, TimeUnit.SECONDS);
        }
        pool.shutdown();

        assertEquals(0, duplicates.get());
        assertEquals(producers * perProducer, seen.size());
        assertEquals(0, buf.size());
        assertTrue(maxSeen.get() <= capacity, "occupancy must never exceed capacity");
    }

    @Test
    void snapshotReflectsRingLayout() throws InterruptedException {
        BoundedBuffer<String> buf = new BoundedBuffer<>(3);
        buf.put("a");
        buf.put("b");
        buf.take();
        buf.put("c");
        buf.put("d"); // wraps into slot 0

        BoundedBuffer.Snapshot s = buf.snapshot();
        assertEquals(3, s.count());
        assertEquals(1, s.head());
        assertEquals(1, s.tail());
        assertArrayEquals(new Object[] {"d", "b", "c"}, s.slots());
    }
}
