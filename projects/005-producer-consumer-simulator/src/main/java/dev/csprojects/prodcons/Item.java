package dev.csprojects.prodcons;

/**
 * A unit of work moving through the buffer.
 *
 * @param producerId which producer made it (1-based)
 * @param sequence   that producer's running count (1-based)
 */
public record Item(int producerId, int sequence) {

    /** Sentinel ("poison pill") telling a consumer to stop. */
    public static final Item POISON = new Item(0, 0);

    public boolean isPoison() {
        return this == POISON;
    }

    @Override
    public String toString() {
        return isPoison() ? "STOP" : "P" + producerId + "#" + sequence;
    }
}
