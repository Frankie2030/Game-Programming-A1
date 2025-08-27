# Whack-a-Zombie (Pygame)

A lightweight, dependency‑free (besides Pygame) Whack‑a‑Mole style game tailored to the **Assignment 1 Assessment Criteria**.

## ✅ Features (Rubric Mapping)

- **Background with multiple spawn locations (2 pts)**  
  9 spawn points (3×3 grid) rendered as round "holes".

- **Zombie design (1 pt)**  
  Procedurally drawn green head (no external files), with eyes and a scar. Consistent style.

- **Zombie head lifetime (1–2 pts)**  
  Randomized **800–1500 ms** lifetime; auto‑despawns on timeout (2 pts path).

- **Mouse interaction / hit detection (3 pts)**  
  Left‑click detection on a scaled ellipse (head). No double counting. Ignores extra clicks while resolving hits.

- **Score HUD (1–2 pts)**  
  Shows **hits**, **misses**, and **accuracy %** (2 pts).

### 🎁 Bonus (Extra Credit)
- **Audio:** Background music + hit SFX (auto‑loaded if files exist in `assets/`; press **M** to mute).  
- **Hit effects:** Flash overlay and squash/stretch on hit.  
- **Spawn/despawn animations:** Pop‑in (scale up) and shrink‑out (scale down).

> You can replace the procedural head with your own sprites; drop them into `assets/` and modify the draw code if desired.

---

## 📦 Requirements

- Python 3.8+
- `pygame`

Install:
```bash
pip install pygame
```

## ▶️ Run

```bash
python whack_a_zombie.py
```

Controls:
- **Left Click** – Whack a zombie  
- **R** – Reset scores  
- **M** – Mute / Unmute (if audio present)  
- **ESC / Q** – Quit

## 🔊 Optional Audio

Place files in `assets/` (next to `whack_a_zombie.py`):

- `bg_music.ogg` – background loop
- `hit.wav` – hit sound

If not present, the game still runs silently.

## 🧪 Design Notes

- All timing uses `pygame.time.get_ticks()` so spawn timing is stable across frame rates.  
- The spawner keeps at most **one active zombie** to ensure a single head counts per click (classic pacing).  
  Increase `MAX_CONCURRENT_ZOMBIES` to raise difficulty.
- Hit test uses ellipse math: `((x-cx)/rx)^2 + ((y-cy)/ry)^2 <= 1` on the animated head scale.

## 📄 License

MIT — do anything; attribution appreciated.
