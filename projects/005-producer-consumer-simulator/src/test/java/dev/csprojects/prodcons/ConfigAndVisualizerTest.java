package dev.csprojects.prodcons;

import static org.junit.jupiter.api.Assertions.*;

import java.io.ByteArrayOutputStream;
import java.io.PrintStream;
import java.nio.charset.StandardCharsets;
import org.junit.jupiter.api.Test;

class ConfigAndVisualizerTest {

    @Test
    void parsesAllFlags() {
        Config c = Config.parse(new String[] {
                "-b", "7", "-p", "3", "-c", "4", "-n", "11",
                "--produce-delay", "5", "--consume-delay", "0", "--seed", "99", "--no-color", "-q"});
        assertEquals(new Config(7, 3, 4, 11, 5, 0, 99L, false, true), c);
        assertEquals(33, c.totalItems());
    }

    @Test
    void emptyArgsGiveDefaults() {
        assertEquals(Config.defaults(), Config.parse(new String[0]));
    }

    @Test
    void rejectsBadInput() {
        assertThrows(IllegalArgumentException.class, () -> Config.parse(new String[] {"--bogus"}));
        assertThrows(IllegalArgumentException.class, () -> Config.parse(new String[] {"-b"}));
        assertThrows(IllegalArgumentException.class, () -> Config.parse(new String[] {"-b", "x"}));
        assertThrows(IllegalArgumentException.class, () -> Config.parse(new String[] {"-b", "0"}));
        assertThrows(IllegalArgumentException.class, () -> Config.parse(new String[] {"--consume-delay", "-1"}));
        assertThrows(Config.HelpRequested.class, () -> Config.parse(new String[] {"--help"}));
    }

    @Test
    void rendersBufferWithoutColor() {
        Visualizer v = new Visualizer(System.out, false);
        var snap = new BoundedBuffer.Snapshot(
                new Object[] {new Item(1, 1), null, new Item(2, 10)}, 2, 1, 2);
        assertEquals("[P1#1  ····· P2#10]  2/3  H2 T1", v.renderBuffer(snap));
    }

    @Test
    void flagsFullAndEmpty() {
        Visualizer v = new Visualizer(System.out, false);
        var full = new BoundedBuffer.Snapshot(new Object[] {new Item(1, 1)}, 0, 0, 1);
        var empty = new BoundedBuffer.Snapshot(new Object[] {null}, 0, 0, 0);
        assertTrue(v.renderBuffer(full).endsWith("FULL"));
        assertTrue(v.renderBuffer(empty).endsWith("EMPTY"));
    }

    @Test
    void colorModeEmitsAnsiCodes() {
        Visualizer v = new Visualizer(System.out, true);
        var snap = new BoundedBuffer.Snapshot(new Object[] {null}, 0, 0, 0);
        assertTrue(v.renderBuffer(snap).contains("\u001B["));
    }

    @Test
    void printsOneLinePerEvent() {
        ByteArrayOutputStream bytes = new ByteArrayOutputStream();
        Visualizer v = new Visualizer(new PrintStream(bytes, true, StandardCharsets.UTF_8), false);
        var snap = new BoundedBuffer.Snapshot(new Object[] {new Item(1, 1), null}, 0, 1, 1);
        v.accept(new Event(1_500_000, Event.Type.PUT, "P1", new Item(1, 1), snap));
        String out = bytes.toString(StandardCharsets.UTF_8);
        assertTrue(out.contains("1.5 ms  P1  put P1#1"), out);
        assertTrue(out.contains("[P1#1  ·····]  1/2  H0 T1"), out);
        assertEquals(1, out.lines().count());
    }
}
