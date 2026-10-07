"""Neon Drift: a small, self-contained top-down shooter made with Tkinter."""

import math
import random
import tkinter as tk


WIDTH = 1000
HEIGHT = 680
BG_TOP = (7, 10, 27)
BG_BOTTOM = (16, 23, 49)
CYAN = "#55f6ff"
PINK = "#ff4fa3"
WHITE = "#eff8ff"


def color_mix(start, end, amount):
    amount = max(0.0, min(1.0, amount))
    channels = [
        round(first + (last - first) * amount)
        for first, last in zip(start, end)
    ]
    return "#{:02x}{:02x}{:02x}".format(*channels)


def unit_vector(dx, dy):
    length = math.hypot(dx, dy)
    if length < 0.001:
        return 0.0, -1.0
    return dx / length, dy / length


class Enemy:
    def __init__(self, x, y, wave, kind="drone"):
        self.x = x
        self.y = y
        self.kind = kind
        self.phase = random.random() * math.tau
        self.radius = 34 if kind == "boss" else (19 if kind == "brute" else 14)
        if kind == "boss":
            self.max_hp = 8 + wave * 2
            self.speed = 40 + wave * 1.2
            self.color = "#ff4f89"
        elif kind == "brute":
            self.max_hp = 3 + wave // 4
            self.speed = 48 + wave * 1.1
            self.color = "#ff9c5b"
        elif kind == "runner":
            self.max_hp = 1
            self.speed = 105 + wave * 2.5
            self.color = "#bd7aff"
        else:
            self.max_hp = 1 + wave // 5
            self.speed = 65 + wave * 1.8
            self.color = "#ff5f83"
        self.hp = self.max_hp


class Bullet:
    def __init__(self, x, y, dx, dy):
        self.x = x
        self.y = y
        self.dx = dx
        self.dy = dy
        self.life = 0.8
        self.trail = []


class Particle:
    def __init__(self, x, y, color, dx, dy, size, life):
        self.x = x
        self.y = y
        self.color = color
        self.dx = dx
        self.dy = dy
        self.size = size
        self.life = life
        self.max_life = life


class NeonDrift:
    def __init__(self, root):
        self.root = root
        self.root.title("NEON DRIFT  |  Arcade")
        self.root.resizable(False, False)
        self.root.configure(bg="#070a1b")

        self.canvas = tk.Canvas(
            root,
            width=WIDTH,
            height=HEIGHT,
            bg="#090d20",
            highlightthickness=0,
            cursor="none",
        )
        self.canvas.pack()

        self.keys = set()
        self.mouse_x = WIDTH / 2
        self.mouse_y = HEIGHT / 2 - 120
        self.mouse_down = False
        self.state = "menu"
        self.last_time = None
        self._make_background()
        self._bind_events()
        self.reset_game()
        self.state = "menu"
        self._frame()

    def _bind_events(self):
        self.root.bind("<KeyPress>", self._key_down)
        self.root.bind("<KeyRelease>", self._key_up)
        self.canvas.bind("<Motion>", self._mouse_move)
        self.canvas.bind("<ButtonPress-1>", self._mouse_press)
        self.canvas.bind("<ButtonRelease-1>", self._mouse_release)
        self.root.bind("<FocusOut>", lambda _event: self.keys.clear())
        self.canvas.focus_set()

    def _make_background(self):
        for row in range(HEIGHT):
            color = color_mix(BG_TOP, BG_BOTTOM, row / HEIGHT)
            self.canvas.create_line(0, row, WIDTH, row, fill=color, tags="background")

        self.canvas.create_oval(
            575, 28, 945, 398, fill="#111837", outline="#252957", width=2,
            tags="background",
        )
        self.canvas.create_oval(
            610, 63, 910, 363, fill="#121a39", outline="#303361", width=2,
            tags="background",
        )
        for offset in (-80, -35, 10, 55, 100):
            self.canvas.create_arc(
                575, 115 + offset, 945, 315 + offset, start=0, extent=180,
                style="arc", outline="#252c53", width=1, tags="background",
            )
        self.canvas.create_rectangle(
            0, 0, WIDTH, HEIGHT, outline="#263052", width=2, tags="background"
        )

        self.stars = []
        for _ in range(105):
            self.stars.append(
                [
                    random.uniform(0, WIDTH),
                    random.uniform(0, HEIGHT),
                    random.choice((1, 1, 1, 2)),
                    random.uniform(8, 34),
                    random.uniform(0, math.tau),
                ]
            )

        for y in range(440, HEIGHT, 34):
            self.canvas.create_line(
                0, y, WIDTH, y, fill="#141b38", width=1, tags="background"
            )
        for x in range(-400, WIDTH + 400, 72):
            self.canvas.create_line(
                WIDTH / 2, 416, x, HEIGHT, fill="#141b38", width=1,
                tags="background",
            )
        self.canvas.create_line(
            0, 439, WIDTH, 439, fill="#273154", width=1, tags="background"
        )

    def reset_game(self):
        self.player_x = WIDTH / 2
        self.player_y = HEIGHT - 116
        self.player_hp = 100
        self.score = 0
        self.wave = 1
        self.kills = 0
        self.enemies = []
        self.bullets = []
        self.particles = []
        self.enemy_spawn_timer = 0.7
        self.enemies_to_spawn = 6
        self.boss_pending = False
        self.fire_timer = 0
        self.hit_flash = 0
        self.shake = 0
        self.elapsed = 0

    def start_game(self):
        self.reset_game()
        self.state = "playing"
        self.last_time = None

    def _key_down(self, event):
        key = event.keysym.lower()
        self.keys.add(key)
        if key in ("return", "space") and self.state in ("menu", "game_over"):
            self.start_game()
        elif key == "p":
            if self.state == "playing":
                self.state = "paused"
            elif self.state == "paused":
                self.state = "playing"
                self.last_time = None
        elif key == "escape" and self.state == "playing":
            self.state = "paused"

    def _key_up(self, event):
        self.keys.discard(event.keysym.lower())

    def _mouse_move(self, event):
        self.mouse_x = event.x
        self.mouse_y = event.y

    def _mouse_press(self, event):
        self.mouse_x = event.x
        self.mouse_y = event.y
        self.mouse_down = True
        if self.state in ("menu", "game_over"):
            self.start_game()

    def _mouse_release(self, _event):
        self.mouse_down = False

    def _frame(self):
        now = self.root.tk.call("clock", "milliseconds")
        if self.last_time is None:
            dt = 0.016
        else:
            dt = min(0.04, max(0.0, (int(now) - int(self.last_time)) / 1000))
        self.last_time = now

        if self.state == "playing":
            self._update(dt)
        self._draw()
        self.root.after(16, self._frame)

    def _update(self, dt):
        self.elapsed += dt
        self.fire_timer = max(0.0, self.fire_timer - dt)
        self.hit_flash = max(0.0, self.hit_flash - dt)
        self.shake = max(0.0, self.shake - dt * 22)
        for star in self.stars:
            star[1] += star[3] * dt
            if star[1] > HEIGHT:
                star[0] = random.uniform(0, WIDTH)
                star[1] = -2

        move_x = int("d" in self.keys or "right" in self.keys) - int(
            "a" in self.keys or "left" in self.keys
        )
        move_y = int("s" in self.keys or "down" in self.keys) - int(
            "w" in self.keys or "up" in self.keys
        )
        if move_x or move_y:
            move_x, move_y = unit_vector(move_x, move_y)
            self.player_x += move_x * 300 * dt
            self.player_y += move_y * 300 * dt
        self.player_x = max(28, min(WIDTH - 28, self.player_x))
        self.player_y = max(80, min(HEIGHT - 36, self.player_y))

        if self.mouse_down and self.fire_timer <= 0:
            self._fire()

        self.enemy_spawn_timer -= dt
        if self.enemy_spawn_timer <= 0:
            self._spawn_enemy()
            self.enemy_spawn_timer = max(0.28, 0.92 - self.wave * 0.025)

        self._update_bullets(dt)
        self._update_enemies(dt)
        self._update_particles(dt)

        if (
            self.enemies_to_spawn == 0
            and not self.boss_pending
            and not self.enemies
        ):
            self.wave += 1
            self.enemies_to_spawn = 5 + self.wave * 2
            self.boss_pending = self.wave % 5 == 0
            self.enemy_spawn_timer = 1.0
            self._burst(WIDTH / 2, 250, CYAN, 28)

    def _spawn_enemy(self):
        if self.boss_pending and self.enemies_to_spawn == 0:
            self.boss_pending = False
            kind = "boss"
        elif self.enemies_to_spawn > 0:
            self.enemies_to_spawn -= 1
            roll = random.random()
            kind = "runner" if self.wave >= 2 and roll < 0.22 else (
                "brute" if self.wave >= 3 and roll < 0.43 else "drone"
            )
        else:
            return

        edge = random.choice(("top", "left", "right"))
        if edge == "top":
            x, y = random.uniform(36, WIDTH - 36), -35
        elif edge == "left":
            x, y = -35, random.uniform(70, HEIGHT - 80)
        else:
            x, y = WIDTH + 35, random.uniform(70, HEIGHT - 80)
        self.enemies.append(Enemy(x, y, self.wave, kind))

    def _fire(self):
        dx, dy = unit_vector(self.mouse_x - self.player_x, self.mouse_y - self.player_y)
        nose_x = self.player_x + dx * 27
        nose_y = self.player_y + dy * 27
        bullet = Bullet(nose_x, nose_y, dx * 700, dy * 700)
        self.bullets.append(bullet)
        self.fire_timer = 0.14
        self._burst(nose_x, nose_y, CYAN, 3, speed=65, size=2)

    def _update_bullets(self, dt):
        remaining = []
        for bullet in self.bullets:
            bullet.trail.insert(0, (bullet.x, bullet.y))
            bullet.trail = bullet.trail[:4]
            bullet.x += bullet.dx * dt
            bullet.y += bullet.dy * dt
            bullet.life -= dt
            hit_enemy = None
            for enemy in self.enemies:
                if math.hypot(enemy.x - bullet.x, enemy.y - bullet.y) < enemy.radius + 5:
                    hit_enemy = enemy
                    break
            if hit_enemy is not None:
                hit_enemy.hp -= 1
                self._burst(bullet.x, bullet.y, hit_enemy.color, 5, speed=100)
                if hit_enemy.hp <= 0:
                    self._destroy_enemy(hit_enemy)
                continue
            if bullet.life > 0 and -20 < bullet.x < WIDTH + 20 and -20 < bullet.y < HEIGHT + 20:
                remaining.append(bullet)
        self.bullets = remaining

    def _update_enemies(self, dt):
        for enemy in self.enemies[:]:
            dx, dy = unit_vector(self.player_x - enemy.x, self.player_y - enemy.y)
            enemy.phase += dt * (2.3 if enemy.kind != "boss" else 1.1)
            sway = math.sin(enemy.phase) * (0.35 if enemy.kind != "boss" else 0.12)
            enemy.x += (dx - dy * sway) * enemy.speed * dt
            enemy.y += (dy + dx * sway) * enemy.speed * dt
            if math.hypot(self.player_x - enemy.x, self.player_y - enemy.y) < enemy.radius + 17:
                self.player_hp -= 22 if enemy.kind == "boss" else 13
                self.hit_flash = 0.18
                self.shake = 8
                self._burst(enemy.x, enemy.y, enemy.color, 13, speed=170)
                self.enemies.remove(enemy)
                if self.player_hp <= 0:
                    self.player_hp = 0
                    self.state = "game_over"
                    self.mouse_down = False
                    self._burst(self.player_x, self.player_y, CYAN, 32, speed=220)
                    return

    def _destroy_enemy(self, enemy):
        if enemy not in self.enemies:
            return
        self.enemies.remove(enemy)
        points = 250 if enemy.kind == "boss" else (
            120 if enemy.kind == "brute" else 75 if enemy.kind == "runner" else 50
        )
        self.score += points * self.wave
        self.kills += 1
        self.shake = max(self.shake, 3 if enemy.kind != "boss" else 10)
        self._burst(enemy.x, enemy.y, enemy.color, 20 if enemy.kind == "boss" else 12)
        if random.random() < 0.12 and self.player_hp < 100:
            self.particles.append(
                Particle(enemy.x, enemy.y, "#70ffb6", 0, 18, 9, 9)
            )

    def _update_particles(self, dt):
        for particle in self.particles[:]:
            particle.life -= dt
            if particle.life <= 0:
                self.particles.remove(particle)
                continue
            if particle.size == 9 and particle.color == "#70ffb6":
                dx, dy = self.player_x - particle.x, self.player_y - particle.y
                distance = math.hypot(dx, dy)
                if distance < 24:
                    self.player_hp = min(100, self.player_hp + 22)
                    self._burst(particle.x, particle.y, particle.color, 10)
                    self.particles.remove(particle)
                    continue
                particle.x += dx / max(1, distance) * 85 * dt
                particle.y += dy / max(1, distance) * 85 * dt
            else:
                particle.x += particle.dx * dt
                particle.y += particle.dy * dt
                particle.dx *= 0.97
                particle.dy *= 0.97

    def _burst(self, x, y, color, count, speed=145, size=3):
        for _ in range(count):
            angle = random.random() * math.tau
            velocity = random.uniform(speed * 0.25, speed)
            life = random.uniform(0.18, 0.55)
            self.particles.append(
                Particle(
                    x, y, color,
                    math.cos(angle) * velocity,
                    math.sin(angle) * velocity,
                    random.uniform(1.5, size + 1),
                    life,
                )
            )

    def _draw(self):
        self.canvas.delete("dynamic")
        self._draw_stars()
        if self.state != "menu":
            self._draw_world()
            self._draw_hud()
        if self.state == "menu":
            self._draw_menu()
        elif self.state == "paused":
            self._draw_overlay("PAUSED", "Press P to jump back in", "RESUME")
        elif self.state == "game_over":
            self._draw_game_over()
        self._draw_crosshair()

    def _draw_stars(self):
        for x, y, size, speed, phase in self.stars:
            shimmer = 0.35 + 0.65 * abs(math.sin(self.elapsed * 1.4 + phase))
            fill = color_mix((54, 74, 112), (182, 227, 255), shimmer)
            self.canvas.create_oval(
                x, y, x + size, y + size, fill=fill, outline="",
                tags="dynamic",
            )

    def _draw_world(self):
        offset_x = random.uniform(-self.shake, self.shake) if self.shake else 0
        offset_y = random.uniform(-self.shake, self.shake) if self.shake else 0
        for enemy in self.enemies:
            self._draw_enemy(enemy, offset_x, offset_y)
        for bullet in self.bullets:
            for index, (x, y) in enumerate(bullet.trail):
                radius = max(1, 4 - index)
                self.canvas.create_oval(
                    x - radius, y - radius, x + radius, y + radius,
                    fill=color_mix((30, 114, 147), (85, 246, 255), 1 - index / 5),
                    outline="", tags="dynamic",
                )
            self.canvas.create_line(
                bullet.x, bullet.y, bullet.x - bullet.dx * 0.035,
                bullet.y - bullet.dy * 0.035, fill=WHITE, width=3,
                tags="dynamic",
            )
        for particle in self.particles:
            factor = particle.life / particle.max_life
            radius = max(1, particle.size * factor)
            self.canvas.create_oval(
                particle.x - radius, particle.y - radius,
                particle.x + radius, particle.y + radius,
                fill=particle.color, outline="", tags="dynamic",
            )
        self._draw_player(offset_x, offset_y)

    def _draw_enemy(self, enemy, offset_x, offset_y):
        x, y = enemy.x + offset_x, enemy.y + offset_y
        radius = enemy.radius
        pulse = 1 + math.sin(enemy.phase * 2) * 0.06
        self.canvas.create_oval(
            x - radius * 1.45, y - radius * 1.45,
            x + radius * 1.45, y + radius * 1.45,
            outline=color_mix((36, 37, 70), (90, 45, 96), 0.7),
            width=2, tags="dynamic",
        )
        if enemy.kind == "boss":
            for angle in range(0, 360, 45):
                radians = math.radians(angle) + enemy.phase
                px = x + math.cos(radians) * radius * 1.25
                py = y + math.sin(radians) * radius * 1.25
                self.canvas.create_oval(
                    px - 4, py - 4, px + 4, py + 4,
                    fill="#ff91be", outline="", tags="dynamic",
                )
        self.canvas.create_oval(
            x - radius * pulse, y - radius * pulse,
            x + radius * pulse, y + radius * pulse,
            fill="#1b1530", outline=enemy.color, width=3, tags="dynamic",
        )
        self.canvas.create_oval(
            x - radius * 0.57, y - radius * 0.57,
            x + radius * 0.57, y + radius * 0.57,
            fill=enemy.color, outline="", tags="dynamic",
        )
        eye_offset = radius * 0.3
        self.canvas.create_oval(
            x - eye_offset - 3, y - 2, x - eye_offset + 3, y + 4,
            fill=WHITE, outline="", tags="dynamic",
        )
        self.canvas.create_oval(
            x + eye_offset - 3, y - 2, x + eye_offset + 3, y + 4,
            fill=WHITE, outline="", tags="dynamic",
        )
        if enemy.hp < enemy.max_hp or enemy.kind == "boss":
            bar_width = radius * 2
            left = x - bar_width / 2
            top = y - radius - 10
            self.canvas.create_rectangle(
                left, top, left + bar_width, top + 4,
                fill="#351c36", outline="", tags="dynamic",
            )
            self.canvas.create_rectangle(
                left, top, left + bar_width * enemy.hp / enemy.max_hp, top + 4,
                fill=enemy.color, outline="", tags="dynamic",
            )

    def _draw_player(self, offset_x, offset_y):
        x, y = self.player_x + offset_x, self.player_y + offset_y
        dx, dy = unit_vector(self.mouse_x - self.player_x, self.mouse_y - self.player_y)
        side_x, side_y = -dy, dx

        def point(forward, side):
            return x + dx * forward + side_x * side, y + dy * forward + side_y * side

        for scale, color in ((1.65, "#153c58"), (1.3, "#176276")):
            glow = [point(23 * scale, 0), point(-13 * scale, 14 * scale),
                    point(-7 * scale, 0), point(-13 * scale, -14 * scale)]
            self.canvas.create_polygon(
                *[coordinate for pair in glow for coordinate in pair],
                fill=color, outline="", tags="dynamic",
            )
        ship = [point(24, 0), point(-12, 13), point(-7, 0), point(-12, -13)]
        self.canvas.create_polygon(
            *[coordinate for pair in ship for coordinate in pair],
            fill="#d9fbff", outline=CYAN, width=2, tags="dynamic",
        )
        cockpit = point(4, 0)
        self.canvas.create_oval(
            cockpit[0] - 4, cockpit[1] - 4, cockpit[0] + 4, cockpit[1] + 4,
            fill=CYAN, outline="", tags="dynamic",
        )
        if self.hit_flash:
            self.canvas.create_oval(
                x - 27, y - 27, x + 27, y + 27,
                outline="#ff637c", width=3, tags="dynamic",
            )

    def _draw_hud(self):
        self._panel(20, 18, 246, 92)
        self._text(38, 34, "SCORE", 9, "#8592ba", "w", bold=True)
        self._text(38, 53, f"{self.score:07d}", 23, WHITE, "w", bold=True)
        self._text(38, 88, f"WAVE  {self.wave:02d}", 10, CYAN, "w", bold=True)
        self._panel(WIDTH - 274, 18, WIDTH - 20, 92)
        self._text(WIDTH - 254, 34, "HULL INTEGRITY", 9, "#8592ba", "w", bold=True)
        self.canvas.create_rectangle(
            WIDTH - 254, 53, WIDTH - 42, 66, fill="#271c37",
            outline="", tags="dynamic",
        )
        health_color = "#70ffb6" if self.player_hp > 55 else (
            "#ffd166" if self.player_hp > 25 else "#ff5577"
        )
        self.canvas.create_rectangle(
            WIDTH - 254, 53,
            WIDTH - 254 + 212 * self.player_hp / 100, 66,
            fill=health_color, outline="", tags="dynamic",
        )
        self._text(
            WIDTH - 42, 83, f"{self.player_hp:03d}%", 11, WHITE, "e", bold=True
        )
        self._text(
            WIDTH / 2, 28, f"SECTOR {self.wave:02d}", 10, "#a3acc9",
            "center", bold=True,
        )
        self._text(
            WIDTH / 2, HEIGHT - 20, "WASD / ARROWS  MOVE     •     HOLD CLICK  FIRE     •     P  PAUSE",
            9, "#7480a5", "center", bold=True,
        )
        if self.wave % 5 == 0 and (self.boss_pending or any(e.kind == "boss" for e in self.enemies)):
            self._text(WIDTH / 2, 55, "ELITE TARGET DETECTED", 11, PINK, "center", bold=True)

    def _draw_menu(self):
        self._panel(245, 115, 755, 555, fill="#0b1026")
        self._text(WIDTH / 2, 190, "NEON", 20, CYAN, "center", bold=True)
        self._text(WIDTH / 2, 235, "DRIFT", 54, WHITE, "center", bold=True)
        self._text(
            WIDTH / 2, 300, "A LAST STAND AMONG THE STARS", 11, "#97a2c5",
            "center", bold=True,
        )
        self._button(WIDTH / 2 - 100, 365, WIDTH / 2 + 100, 423, "DEPLOY")
        self._text(
            WIDTH / 2, 463, "WASD / ARROWS  ·  MOVE", 11, "#c0c9e3",
            "center", bold=True,
        )
        self._text(
            WIDTH / 2, 490, "AIM WITH YOUR MOUSE  ·  HOLD LEFT CLICK TO FIRE",
            10, "#8e9aba", "center", bold=True,
        )
        self._text(
            WIDTH / 2, 525, "SURVIVE THE WAVES. WATCH FOR ELITE TARGETS.",
            9, "#586687", "center", bold=True,
        )

    def _draw_game_over(self):
        self._panel(305, 180, 695, 500, fill="#0b1026")
        self._text(WIDTH / 2, 235, "SIGNAL LOST", 30, PINK, "center", bold=True)
        self._text(
            WIDTH / 2, 298, f"{self.score:07d}", 34, WHITE, "center", bold=True
        )
        self._text(
            WIDTH / 2, 337, "FINAL SCORE", 9, "#8996ba", "center", bold=True
        )
        self._text(
            WIDTH / 2, 380, f"SECTOR {self.wave:02d}    ·    {self.kills} TARGETS CLEARED",
            10, "#adb8d5", "center", bold=True,
        )
        self._button(WIDTH / 2 - 100, 419, WIDTH / 2 + 100, 473, "PLAY AGAIN")

    def _draw_overlay(self, title, subtitle, button_text):
        self._panel(320, 220, 680, 465, fill="#0b1026")
        self._text(WIDTH / 2, 285, title, 34, WHITE, "center", bold=True)
        self._text(
            WIDTH / 2, 345, subtitle, 11, "#9aa7c7", "center", bold=True
        )
        self._button(
            WIDTH / 2 - 90, 382, WIDTH / 2 + 90, 432, button_text
        )

    def _draw_crosshair(self):
        if self.state == "playing":
            x, y = self.mouse_x, self.mouse_y
            self.canvas.create_oval(
                x - 11, y - 11, x + 11, y + 11,
                outline=CYAN, width=1, tags="dynamic",
            )
            self.canvas.create_line(
                x - 17, y, x - 6, y, fill=CYAN, width=1, tags="dynamic"
            )
            self.canvas.create_line(
                x + 6, y, x + 17, y, fill=CYAN, width=1, tags="dynamic"
            )
            self.canvas.create_line(
                x, y - 17, x, y - 6, fill=CYAN, width=1, tags="dynamic"
            )
            self.canvas.create_line(
                x, y + 6, x, y + 17, fill=CYAN, width=1, tags="dynamic"
            )

    def _panel(self, left, top, right, bottom, fill="#0b1127"):
        points = [
            left + 12, top, right - 12, top, right, top + 12,
            right, bottom - 12, right - 12, bottom, left + 12, bottom,
            left, bottom - 12, left, top + 12,
        ]
        self.canvas.create_polygon(
            points, fill=fill, outline="#273455", width=1, smooth=True,
            tags="dynamic",
        )
        self.canvas.create_line(
            left + 14, top + 1, left + 58, top + 1,
            fill=CYAN, width=2, tags="dynamic",
        )

    def _button(self, left, top, right, bottom, label):
        self.canvas.create_rectangle(
            left, top, right, bottom, fill="#123343", outline=CYAN,
            width=2, tags="dynamic",
        )
        self.canvas.create_text(
            (left + right) / 2, (top + bottom) / 2,
            text=label, fill=WHITE, font=("Segoe UI", 12, "bold"),
            tags="dynamic",
        )
        self.canvas.create_text(
            (left + right) / 2, bottom + 18,
            text="CLICK OR PRESS ENTER", fill="#7585a8",
            font=("Segoe UI", 8, "bold"), tags="dynamic",
        )

    def _text(self, x, y, text, size, color, anchor="center", bold=False):
        font = ("Segoe UI", size, "bold" if bold else "normal")
        self.canvas.create_text(
            x, y, text=text, fill=color, font=font, anchor=anchor,
            tags="dynamic",
        )


def main():
    root = tk.Tk()
    NeonDrift(root)
    root.mainloop()


if __name__ == "__main__":
    main()