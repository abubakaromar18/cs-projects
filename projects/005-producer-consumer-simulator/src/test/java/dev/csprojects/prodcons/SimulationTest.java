package dev.csprojects.prodcons;

import static org.junit.jupiter.api.Assertions.*;

import java.util.List;
import java.util.Map;
import java.util.concurrent.CopyOnWriteArrayList;
import java.util.stream.Collectors;
import org.junit.jupiter.api.Test;
import org.junit.jupiter.api.Timeout;

@Timeout(15)
class SimulationTest {

    private static Config config(int cap, int p, int c, int n, int pd, int cd) {
        return new Config(cap, p, c, n, pd, cd, 7L, false, true);
    }

    @Test
    void everyItemIsConsumedExactlyOnce() throws InterruptedException {
        Config cfg = config(3, 3, 2, 20, 0, 1);
        Stats stats = new Simulation(cfg, e -> { }).run();

        assertEquals(60, stats.produced());
        assertEquals(60, stats.consumed());
        assertEquals(0, stats.duplicateTakes());
        assertEquals(60, stats.consumedItems().size());
        for (int p = 1; p <= 3; p++) {
            assertEquals(20, stats.producedBy(p));
        }
        assertFalse(stats.consumedItems().contains(Item.POISON), "poison pills are not counted");
        assertTrue(stats.maxOccupancy() <= 3);
    }

    @Test
    void fastProducersSlowConsumersFillTheBuffer() throws InterruptedException {
        Stats stats = new Simulation(config(2, 2, 1, 6, 0, 10), e -> { }).run();
        assertTrue(stats.producerBlocks() > 0, "producers should hit a full buffer");
        assertEquals(2, stats.maxOccupancy());
    }

    @Test
    void slowProducersFastConsumersDrainTheBuffer() throws InterruptedException {
        Stats stats = new Simulation(config(4, 1, 2, 5, 10, 0), e -> { }).run();
        assertTrue(stats.consumerBlocks() > 0, "consumers should hit an empty buffer");
    }

    @Test
    void eventsAreEmittedInPerProducerOrder() throws InterruptedException {
        List<Event> events = new CopyOnWriteArrayList<>();
        new Simulation(config(2, 2, 2, 5, 1, 1), events::add).run();

        Map<String, List<Integer>> putsByProducer = events.stream()
                .filter(e -> e.type() == Event.Type.PUT)
                .collect(Collectors.groupingBy(Event::actor,
                        Collectors.mapping(e -> e.item().sequence(), Collectors.toList())));
        assertEquals(List.of(1, 2, 3, 4, 5), putsByProducer.get("P1"));
        assertEquals(List.of(1, 2, 3, 4, 5), putsByProducer.get("P2"));

        long done = events.stream().filter(e -> e.type() == Event.Type.DONE).count();
        assertEquals(4, done, "every producer and consumer reports DONE");
        assertTrue(events.stream().allMatch(e -> e.buffer().count() <= 2));
    }

    @Test
    void summaryReportsIntegrity() throws InterruptedException {
        Stats stats = new Simulation(config(2, 1, 1, 3, 0, 0), e -> { }).run();
        String summary = stats.summary(2);
        assertTrue(summary.contains("produced/consumed  3 / 3"), summary);
        assertTrue(summary.contains("integrity          OK"), summary);
    }
}
