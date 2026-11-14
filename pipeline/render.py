#!/usr/bin/env python3
"""Render the canvas scene to an MP4 by screenshotting every frame in headless Chromium."""
import argparse, os, subprocess, time

ap = argparse.ArgumentParser()
ap.add_argument("--workdir", required=True, help="folder containing index.html + config.js + notes.js")
ap.add_argument("--audio", required=True)
ap.add_argument("--out", required=True)
ap.add_argument("--fps", type=int, default=30)
ap.add_argument("--duration", type=float, required=True)
ap.add_argument("--preview", type=float, default=0, help="render only the first N seconds (test mode)")
ap.add_argument("--crf", type=int, default=18)
ap.add_argument("--preset", default="slow")
ap.add_argument("--quality", type=int, default=93)
a = ap.parse_args()

import imageio_ffmpeg
from playwright.sync_api import sync_playwright

dur = min(a.duration, a.preview) if a.preview else a.duration
n = max(1, int(round(a.fps * dur)))
os.makedirs(os.path.dirname(os.path.abspath(a.out)), exist_ok=True)

cmd = [imageio_ffmpeg.get_ffmpeg_exe(), "-y", "-loglevel", "error",
       "-f", "image2pipe", "-framerate", str(a.fps), "-i", "-",
       "-i", a.audio,
       "-c:v", "libx264", "-preset", a.preset, "-crf", str(a.crf),
       "-pix_fmt", "yuv420p", "-profile:v", "high",
       "-c:a", "aac", "-b:a", "192k", "-ar", "48000",
       "-shortest", "-movflags", "+faststart", a.out]
ff = subprocess.Popen(cmd, stdin=subprocess.PIPE)

t0 = time.time()
with sync_playwright() as p:
    b = p.chromium.launch(args=["--force-color-profile=srgb", "--disable-lcd-text"])
    pg = b.new_page(viewport={"width": 1920, "height": 1080}, device_scale_factor=1)
    pg.goto("file://" + os.path.join(os.path.abspath(a.workdir), "index.html"))
    pg.wait_for_timeout(500)
    vw = pg.evaluate("window.VIDEO.width")
    vh = pg.evaluate("window.VIDEO.height")
    # resize the page to the real pixel size before grabbing frames
    pg.set_viewport_size({"width": int(vw), "height": int(vh)})
    pg.wait_for_timeout(200)
    for i in range(n):
        t = i / a.fps
        pg.evaluate(f"window.drawFrame({t})")
        ff.stdin.write(pg.screenshot(type="jpeg", quality=a.quality))
        if i and i % 300 == 0:
            print(f"  {i}/{n} frames  {time.time()-t0:.0f}s", flush=True)
    b.close()
ff.stdin.close()
ff.wait()
if ff.returncode != 0:
    raise SystemExit(f"ffmpeg failed with code {ff.returncode}")
print(f"rendered {n} frames in {time.time()-t0:.0f}s -> {a.out}")
