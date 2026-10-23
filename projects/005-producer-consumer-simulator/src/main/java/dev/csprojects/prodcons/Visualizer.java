package dev.csprojects.prodcons;

import java.io.PrintStream;
import java.util.function.Consumer;

/**
 * Renders each {@link Event} as one terminal line: a timestamped description followed by
 * a picture of the ring buffer, e.g.
 *
 * <pre>
 *    41.2 ms  P1  put P1#1           [P1#1  ····· ····· ····· ·····]  1/5  H0 T1
 * </pre>
 *
 * Slots holding items are shown by name; empty slots as dots. H and T are the ring's
 * head (next take) and tail (next put) indices.
 *
 * <p>Called concurrently by worker threads, so {@link #accept} is synchronized to keep each
 * line intact.
 */
public final class Visualizer implements Consumer<Event> {

    private static final String RESET = "\u001B[0m";
    private static final String GREEN = "\u001B[32m";
    private static final String CYAN = "\u001B[36m";
    private static final String YELLOW = "\u001B[33m";
    private static final String DIM = "\u001B[2m";

    private static final int CELL_WIDTH = 5;

    private final PrintStream out;
    private final boolean color;

    public Visualizer(PrintStream out, boolean color) {
        this.out = out;
        this.color = color;
    }

    @Override
    public synchronized void accept(Event e) {
        out.println(renderLine(e));
    }

    /** Builds the full output line for an event (no trailing newline). */
    public String renderLine(Event e) {
        String text = String.format("%-34s", e.describe());
        return paint(text, colorFor(e.type())) + "  " + renderBuffer(e.buffer());
    }

    /** Draws the ring buffer, e.g. {@code [P1#1  P2#1  ····· ·····]  2/4  H0 T2}. */
    public String renderBuffer(BoundedBuffer.Snapshot s) {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < s.capacity(); i++) {
            if (i > 0) {
                sb.append(' ');
            }
            Object slot = s.slots()[i];
            if (slot == null) {
                sb.append(paint("·".repeat(CELL_WIDTH), DIM));
            } else {
                sb.append(pad(slot.toString()));
            }
        }
        sb.append("]  ").append(s.count()).append('/').append(s.capacity());
        sb.append("  H").append(s.head()).append(" T").append(s.tail());
        if (s.count() == s.capacity()) {
            sb.append(paint("  FULL", YELLOW));
        } else if (s.count() == 0) {
            sb.append(paint("  EMPTY", YELLOW));
        }
        return sb.toString();
    }

    private static String pad(String s) {
        if (s.length() >= CELL_WIDTH) {
            return s.substring(0, CELL_WIDTH);
        }
        return s + " ".repeat(CELL_WIDTH - s.length());
    }

    private static String colorFor(Event.Type t) {
        return switch (t) {
            case PUT -> GREEN;
            case TAKE -> CYAN;
            case WAIT_PUT, WAIT_TAKE -> YELLOW;
            case DONE -> DIM;
        };
    }

    private String paint(String s, String ansi) {
        return color ? ansi + s + RESET : s;
    }
}
