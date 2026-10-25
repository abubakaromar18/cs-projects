import os

# Let the pygame tests run on CI / servers with no display or sound card.
os.environ.setdefault("SDL_VIDEODRIVER", "dummy")
os.environ.setdefault("SDL_AUDIODRIVER", "dummy")
