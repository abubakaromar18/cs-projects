"""GUI smoke tests. Skipped automatically when Tk or a display is missing.

On headless Linux run them with:  xvfb-run -a python -m pytest tests/test_gui.py
"""
import pytest

tk = pytest.importorskip("tkinter")

from colorpick.colors import RGB  # noqa: E402
from colorpick.model import PickerModel  # noqa: E402


@pytest.fixture
def root():
    try:
        r = tk.Tk()
    except tk.TclError:
        pytest.skip("no display available")
    r.withdraw()
    yield r
    r.destroy()


def test_app_renders_and_syncs(root):
    from colorpick.app import ColorPickerApp

    model = PickerModel(RGB(255, 136, 0))
    app = ColorPickerApp(root, model)
    root.update()
    assert app.format_vars["HEX"].get() == "#FF8800"
    assert app.scales["g"].get() == 136

    app.entry_var.set("hsl(120, 100%, 50%)")
    app._on_entry()
    root.update()
    assert model.color == RGB(0, 255, 0)
    assert app.scales["r"].get() == 0 and app.scales["g"].get() == 255

    app.entry_var.set("garbage")
    app._on_entry()
    assert app.entry_status.cget("text") == "Unrecognised color"

    app.copy("#00FF00")
    assert root.clipboard_get() == "#00FF00"


def test_screen_pick_with_fake_capture(root):
    pytest.importorskip("PIL.ImageTk")
    from PIL import Image

    from colorpick.app import ColorPickerApp, ScreenPickerOverlay

    img = Image.new("RGB", (200, 150), (10, 20, 30))
    img.putpixel((50, 60), (250, 0, 0))
    model = PickerModel(RGB(0, 0, 0))
    app = ColorPickerApp(root, model, grabber=lambda: img)
    app.pick_from_screen()
    root.update()
    overlays = [w for w in root.winfo_children() if isinstance(w, ScreenPickerOverlay)]
    assert len(overlays) == 1
    ov = overlays[0]
    ov._move(50, 60)
    ov._pick()
    root.update()
    assert model.color == RGB(250, 0, 0)
    assert model.history[0] == RGB(250, 0, 0)
