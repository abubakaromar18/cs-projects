package dev.csprojects.prodcons;

/**
 * Simulation parameters. Use {@link #parse(String[])} to build one from command-line flags.
 *
 * @param capacity       buffer slots
 * @param producers      number of producer threads
 * @param consumers      number of consumer threads
 * @param itemsPerProducer how many items each producer makes
 * @param produceDelayMs mean time a producer spends "making" an item
 * @param consumeDelayMs mean time a consumer spends "processing" an item
 * @param seed           RNG seed for delay jitter (same seed, same delays)
 * @param color          use ANSI colors in output
 * @param quiet          print only the final statistics
 */
public record Config(
        int capacity,
        int producers,
        int consumers,
        int itemsPerProducer,
        int produceDelayMs,
        int consumeDelayMs,
        long seed,
        boolean color,
        boolean quiet) {

    public static final String USAGE = """
            Usage: java -jar producer-consumer-simulator.jar [options]

              -b, --capacity N        buffer slots                  (default 5)
              -p, --producers N       producer threads              (default 2)
              -c, --consumers N       consumer threads              (default 2)
              -n, --items N           items per producer            (default 8)
                  --produce-delay MS  mean production time          (default 40)
                  --consume-delay MS  mean consumption time         (default 60)
                  --seed N            jitter seed                   (default 42)
                  --no-color          disable ANSI colors
              -q, --quiet             only print the summary
              -h, --help              show this help
            """;

    public Config {
        requirePositive("capacity", capacity);
        requirePositive("producers", producers);
        requirePositive("consumers", consumers);
        requirePositive("items", itemsPerProducer);
        requireNonNegative("produce-delay", produceDelayMs);
        requireNonNegative("consume-delay", consumeDelayMs);
    }

    public static Config defaults() {
        return new Config(5, 2, 2, 8, 40, 60, 42L, true, false);
    }

    public int totalItems() {
        return producers * itemsPerProducer;
    }

    /**
     * Parses command-line flags on top of {@link #defaults()}.
     *
     * @throws IllegalArgumentException on unknown flags or bad values
     * @throws HelpRequested            if -h/--help is present
     */
    public static Config parse(String[] args) {
        Config d = defaults();
        int capacity = d.capacity, producers = d.producers, consumers = d.consumers;
        int items = d.itemsPerProducer, pDelay = d.produceDelayMs, cDelay = d.consumeDelayMs;
        long seed = d.seed;
        boolean color = d.color, quiet = d.quiet;

        for (int i = 0; i < args.length; i++) {
            String flag = args[i];
            switch (flag) {
                case "-h", "--help" -> throw new HelpRequested();
                case "--no-color" -> color = false;
                case "-q", "--quiet" -> quiet = true;
                case "-b", "--capacity" -> capacity = intValue(flag, args, ++i);
                case "-p", "--producers" -> producers = intValue(flag, args, ++i);
                case "-c", "--consumers" -> consumers = intValue(flag, args, ++i);
                case "-n", "--items" -> items = intValue(flag, args, ++i);
                case "--produce-delay" -> pDelay = intValue(flag, args, ++i);
                case "--consume-delay" -> cDelay = intValue(flag, args, ++i);
                case "--seed" -> seed = longValue(flag, args, ++i);
                default -> throw new IllegalArgumentException("unknown option: " + flag);
            }
        }
        return new Config(capacity, producers, consumers, items, pDelay, cDelay, seed, color, quiet);
    }

    private static String value(String flag, String[] args, int i) {
        if (i >= args.length) {
            throw new IllegalArgumentException(flag + " needs a value");
        }
        return args[i];
    }

    private static int intValue(String flag, String[] args, int i) {
        String v = value(flag, args, i);
        try {
            return Integer.parseInt(v);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException(flag + " expects an integer, got '" + v + "'");
        }
    }

    private static long longValue(String flag, String[] args, int i) {
        String v = value(flag, args, i);
        try {
            return Long.parseLong(v);
        } catch (NumberFormatException e) {
            throw new IllegalArgumentException(flag + " expects an integer, got '" + v + "'");
        }
    }

    private static void requirePositive(String name, int v) {
        if (v <= 0) {
            throw new IllegalArgumentException(name + " must be positive, got " + v);
        }
    }

    private static void requireNonNegative(String name, int v) {
        if (v < 0) {
            throw new IllegalArgumentException(name + " must be >= 0, got " + v);
        }
    }

    /** Thrown by {@link #parse} when the user asks for help. */
    public static final class HelpRequested extends RuntimeException {
        private static final long serialVersionUID = 1L;

        HelpRequested() {
            super(null, null, false, false);
        }
    }
}
