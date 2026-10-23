package dev.csprojects.prodcons;

/** Command-line entry point. */
public final class Main {

    private Main() {
    }

    public static void main(String[] args) throws InterruptedException {
        Config config;
        try {
            config = Config.parse(args);
        } catch (Config.HelpRequested h) {
            System.out.print(Config.USAGE);
            return;
        } catch (IllegalArgumentException e) {
            System.err.println("error: " + e.getMessage());
            System.err.print(Config.USAGE);
            System.exit(2);
            return;
        }

        System.out.printf("Producer-Consumer: %d producer(s) x %d item(s), %d consumer(s), buffer of %d%n%n",
                config.producers(), config.itemsPerProducer(), config.consumers(), config.capacity());

        Visualizer visualizer = new Visualizer(System.out, config.color());
        Simulation sim = new Simulation(config, config.quiet() ? e -> { } : visualizer);
        Stats stats = sim.run();

        System.out.println();
        System.out.print(stats.summary(config.capacity()));
    }
}
