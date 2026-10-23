package dev.csprojects.prodcons;

/**
 * Something that happened during the simulation. Events are emitted by worker threads
 * and drained by the renderer, so they must be immutable.
 *
 * @param nanos  time since simulation start
 * @param type   what happened
 * @param actor  thread label, e.g. "P1" or "C2"
 * @param item   item involved, or null
 * @param buffer consistent buffer snapshot taken right after the event
 */
public record Event(long nanos, Type type, String actor, Item item, BoundedBuffer.Snapshot buffer) {

    public enum Type {
        /** Producer is about to wait for a free slot. */
        WAIT_PUT,
        /** Producer inserted an item. */
        PUT,
        /** Consumer is about to wait for an item. */
        WAIT_TAKE,
        /** Consumer removed an item. */
        TAKE,
        /** Thread finished its work. */
        DONE
    }

    public String describe() {
        String what = switch (type) {
            case WAIT_PUT -> "waits for a free slot";
            case PUT -> "put " + item;
            case WAIT_TAKE -> "waits for an item";
            case TAKE -> "took " + item;
            case DONE -> "finished";
        };
        return String.format("%7.1f ms  %-3s %s", nanos / 1_000_000.0, actor, what);
    }
}
