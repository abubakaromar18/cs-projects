package dev.csprojects.prodcons;

import java.util.concurrent.Semaphore;
import java.util.concurrent.TimeUnit;

/**
 * A fixed-capacity circular buffer synchronized with the classic three-semaphore
 * solution to the producer-consumer problem (Dijkstra, 1965):
 *
 * <ul>
 *   <li>{@code emptySlots} – counts free slots; producers wait on it when the buffer is full.</li>
 *   <li>{@code filledSlots} – counts items available; consumers wait on it when the buffer is empty.</li>
 *   <li>{@code mutex} – a binary semaphore guarding the ring indices (the critical section).</li>
 * </ul>
 *
 * <p>The order of acquisition matters: a producer must acquire {@code emptySlots} <em>before</em>
 * {@code mutex}. Reversing it can deadlock — a producer would hold the mutex while sleeping on a
 * full buffer, so no consumer could ever enter to free a slot.
 *
 * @param <T> element type
 */
public final class BoundedBuffer<T> {

    private final Object[] slots;
    private final Semaphore emptySlots;
    private final Semaphore filledSlots;
    private final Semaphore mutex = new Semaphore(1, true);

    private int head; // next index to take from
    private int tail; // next index to put into
    private int count;

    public BoundedBuffer(int capacity) {
        if (capacity <= 0) {
            throw new IllegalArgumentException("capacity must be positive, got " + capacity);
        }
        this.slots = new Object[capacity];
        // Fair semaphores give FIFO wake-up order, which keeps the visualization intuitive
        // and prevents starvation of individual threads.
        this.emptySlots = new Semaphore(capacity, true);
        this.filledSlots = new Semaphore(0, true);
    }

    /** Inserts an item, blocking while the buffer is full. */
    public void put(T item) throws InterruptedException {
        emptySlots.acquire();          // P(empty)
        mutex.acquire();               // P(mutex)
        try {
            slots[tail] = item;
            tail = (tail + 1) % slots.length;
            count++;
        } finally {
            mutex.release();           // V(mutex)
        }
        filledSlots.release();         // V(full)
    }

    /**
     * Inserts an item, waiting at most {@code timeout} for a free slot.
     *
     * @return {@code true} if inserted, {@code false} if the timeout elapsed
     */
    public boolean offer(T item, long timeout, TimeUnit unit) throws InterruptedException {
        if (!emptySlots.tryAcquire(timeout, unit)) {
            return false;
        }
        mutex.acquire();
        try {
            slots[tail] = item;
            tail = (tail + 1) % slots.length;
            count++;
        } finally {
            mutex.release();
        }
        filledSlots.release();
        return true;
    }

    /** Removes and returns the oldest item, blocking while the buffer is empty. */
    public T take() throws InterruptedException {
        filledSlots.acquire();         // P(full)
        T item;
        mutex.acquire();               // P(mutex)
        try {
            item = removeHead();
        } finally {
            mutex.release();           // V(mutex)
        }
        emptySlots.release();          // V(empty)
        return item;
    }

    /**
     * Removes the oldest item, waiting at most {@code timeout} for one to arrive.
     *
     * @return the item, or {@code null} if the timeout elapsed
     */
    public T poll(long timeout, TimeUnit unit) throws InterruptedException {
        if (!filledSlots.tryAcquire(timeout, unit)) {
            return null;
        }
        T item;
        mutex.acquire();
        try {
            item = removeHead();
        } finally {
            mutex.release();
        }
        emptySlots.release();
        return item;
    }

    @SuppressWarnings("unchecked")
    private T removeHead() {
        T item = (T) slots[head];
        slots[head] = null; // allow GC and make the snapshot show the slot as empty
        head = (head + 1) % slots.length;
        count--;
        return item;
    }

    public int capacity() {
        return slots.length;
    }

    /** Current number of items. Takes the mutex so the value is consistent. */
    public int size() {
        mutex.acquireUninterruptibly();
        try {
            return count;
        } finally {
            mutex.release();
        }
    }

    /** A consistent copy of the ring for visualization: index i holds slot i (or null). */
    public Snapshot snapshot() {
        mutex.acquireUninterruptibly();
        try {
            return new Snapshot(slots.clone(), head, tail, count);
        } finally {
            mutex.release();
        }
    }

    /** Immutable view of the buffer at one instant. */
    public record Snapshot(Object[] slots, int head, int tail, int count) {
        public int capacity() {
            return slots.length;
        }
    }
}
