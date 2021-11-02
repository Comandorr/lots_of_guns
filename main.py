from ursina import *
from ursina.shaders import lit_with_shadows_shader
from ursina.prefabs.conversation import Conversation
from ursina import curve
from ursina.prefabs.trail_renderer import TrailRenderer
from ursina.prefabs.health_bar import HealthBar
from random import randint, choice
import time


class Cam(EditorCamera):
    def input(self, key):
        pass


app = Ursina(fullscreen=True)
sky = Sky(texture='bloody.jpg', texture_scale=(50, 50))
ground = Entity(model='plane', scale=(100, 1, 100), texture='bloody2.jpg', texture_scale=(1, 1),
                shader=lit_with_shadows_shader)
ec = Cam(rotation=(30, 0, 0), rotation_speed=0)
camera.orthographic = True
camera.fov = 100
camera.clip_plane_near = False
camera.clip_plane_far = False
mouse.visible = False

shot = Audio('sounds/barret.mp3', autoplay=False, volume=0.8, pitch=0.7)
shot2 = Audio('sounds/ar10.mp3', autoplay=False, volume=1, pitch=0.7)
shot3 = Audio('sounds/rifle.mp3', autoplay=False, volume=1, pitch=0.7)
dogma = Audio('sounds/dogma.mp3', autoplay=False)
riptear = Audio('sounds/rip&tear.mp3', autoplay=False)

player = Entity(model='Ducky.obj', texture='texture.png', collider='box', y=0, shader=lit_with_shadows_shader)
ec.add_script(SmoothFollow(target=player, offset=(0, 0, 0)))
sun = PointLight(parent=player, y=2, shadows=True, color=color.red)
player.speed = 10
player.hp = 100
cursor = Entity(model='sphere', scale=.2, color=color.violet, y=.5, shader=lit_with_shadows_shader)
enemies = []
bar = HealthBar(bar_color=color.lime.tint(-.25), roundness=.5, value=player.hp, x=0 - .25, y=0.49)
print(bar.position)


def player_hurt():
    player.hp -= 1
    if player.hp <= 0:
        global start
        start = False
        Sequence(0.02, Func(change_fov, +0.1), Func(setattr, riptear, 'volume', 0.35), loop=True).start()


class Gun(Entity):
    def __init__(self, name, speed, mode, max_ammo, reload_speed, caliber, sound, **kwargs):
        super().__init__(**kwargs)
        self.model = 'weapons/' + name + '.obj'
        self.texture = 'weapons.png'
        self.speed = speed
        self.mode = mode
        self.max_ammo = max_ammo
        self.reload_speed = reload_speed
        self.caliber = caliber
        self.parent = None
        self.shooting = Sequence(Func(self.shoot), Wait(self.speed), loop=True, paused=True)
        self.sound = sound

    def shoot(self):
        self.sound.play()
        if self.parent == player:
            shake_cam()
            camera.fov += randint(-1, 1)
            camera.fov += randint(-1, 1)
            camera.fov += randint(-1, 1)
        Bullet(self, position=self.world_position + self.right * 13)


gun1 = Gun(name='w1', speed=0.12, mode='auto', max_ammo=30, reload_speed=0.5, caliber=0.1, scale=.1, y=.4,
           rotation_y=-90, sound=shot)


class Bullet(Entity):
    def __init__(self, master, **kwargs):
        super().__init__(**kwargs)
        self.model = 'sphere'
        if master.parent == player:
            self.color = color.red
        else:
            self.color = color.blue
        self.trail = TrailRenderer(parent=self, thickness=100, color=self.color, length=6)
        self.collider = SphereCollider(self, center=Vec3(0, 0, 0), radius=2)
        self.scale = master.caliber
        self.rotation = master.world_rotation + (0, 90, 0)
        self.light = PointLight(parent=self, shadows=True)
        self.shader = lit_with_shadows_shader

    def update(self):
        self.position += self.forward * 5
        self.light.world_position = self.world_position
        if distance(self, player) > 15:
            self.disable()
        hitinfo = self.intersects()
        if hitinfo.hit:
            if self.color == color.red and hitinfo.entity.type in ['Shooter', 'Mother',
                                                                   'Biter'] and hitinfo.entity.alive and self.enabled:
                hitinfo.entity.hurt()
                self.disable()
            if self.color == color.blue and hitinfo.entity == player and self.enabled:
                self.disable()
                player_hurt()


class Enemy(Entity):
    def __init__(self, name, hp, speed, alive=True, **kwargs):
        super().__init__(**kwargs)
        self.shader = lit_with_shadows_shader
        self.rotation_y += 180
        self.model = 'demons/' + name + '.obj'
        self.texture = 'demons/' + name + '.png'
        if alive:
            self.collider = 'box'
        self.speed = speed
        self.hp = hp
        self.alive = alive
        enemies.append(self)

    def rise(self):
        self.y = 0

    def activate(self):
        self.alive = True
        self.collider = 'box'

    def move(self):
        self.position += self.forward * self.speed

    def update(self):
        global start
        if self.alive and start and distance(player, self) < 20:
            self.look_at(player)

            hitinfo = self.intersects()
            if hitinfo.hit and hitinfo.entity == player:
                player_hurt()

    def hurt(self):
        self.blink(color.red, duration=.5)
        self.hp -= 1
        if self.hp <= 0:
            self.die()

    def die(self):
        if self.type == 'Shooter':
            self.gun.shooting.pause()
        if self in enemies:
            enemies.remove(self)
        self.alive = False
        self.disable()


class Biter(Enemy):
    def __init__(self, **kwargs):
        super().__init__(name='demon1', speed=0.15, hp=10, **kwargs)

    def update(self):
        global start
        if self.alive and start and distance(player, self) < 20:
            super().update()
            super().move()
            hitinfo = self.intersects()
            if hitinfo.hit and hitinfo.entity == player:
                self.position += self.back * 5


class Shooter(Enemy):
    def __init__(self, **kwargs):
        super().__init__(name='demon3', speed=0.07, hp=20, **kwargs)
        self.gun = Gun(name='w2', speed=0.30, mode='auto', max_ammo=15, reload_speed=0.5, caliber=0.2, scale=.1, y=.4,
                       rotation_y=-90, sound=shot)
        self.gun.parent = self
        self.gun.position += self.left * 0.1 + self.back + self.up

    def update(self):
        global start
        if self.alive and start and distance(player, self) < 20:
            super().update()
            if distance(player, self) >= 10:
                super().move()
            self.gun.look_at(player)
            self.gun.rotation_y += -90
            if self.gun.shooting.paused:
                self.gun.shooting.start()


class Mother(Enemy):
    def __init__(self, **kwargs):
        super().__init__(name='demon2', speed=0.1, hp=50, **kwargs)
        self.cooldown = 10
        self.last = time.time()
        self.light = PointLight(parent=self, y=2, shadows=True, color=color.black)
        self.portal = Entity(model='quad', position=(0, -3, 0), texture='portal2.png', rotation_x=90, scale=2)

    def portal_off(self):
        self.portal.y = -3

    def spawn(self):
        x = self.x + randint(-5, 5)
        z = self.z + randint(-5, 5)
        self.portal.position = (x, 0.1, z)
        c = choice(['Biter', 'Shooter'])
        if c == 'Biter':
            new = Biter(position=(x, -2.5, z), alive=False)
        elif c == 'Shooter':
            new = Shooter(position=(x, -2.5, z), alive=False)

        Sequence(Wait(randint(1, 5)), Func(new.rise), Wait(randint(1, 5)), Func(new.activate), Func(self.portal_off),
                 loop=False, paused=True).start()

    def update(self):
        global start
        if self.alive and start:
            super().update()
            if (time.time() - self.last) > self.cooldown and len(enemies) < 10:
                self.spawn()
                self.last = time.time()




Mother(position=(0, 0, 25))
Mother(position=(0, 0, -25))
Mother(position=(25, 0, 0))
Mother(position=(-25, 0, 0))

Biter(position=(-7, 0, 7))
Biter(position=(7, 0, 7))
Shooter(position=(0, 0, 10))
Shooter(position=(-7, 0, -5), rotation_y=-90)
Shooter(position=(7, 0, -5), rotation_y=90)
Biter(position=(-4, 0, -15), rotation_y=180)
Biter(position=(4, 0, -15), rotation_y=180)
player.gun = gun1
player.gun.parent = player
player.gun.position += player.right * .25
demons = []
start = False


def update():
    global start
    if start:
        bar.value = player.hp
        player.z += (held_keys['w'] - held_keys['s']) * time.dt * player.speed
        player.x += (held_keys['d'] - held_keys['a']) * time.dt * player.speed * 0.7
        cursor.x = player.x + mouse.position[0] * 10
        cursor.z = player.z + mouse.position[1] * 20
        player.look_at(cursor.position)
        if len(enemies) == 0:
            Text(text='ВЫ ПОБЕДИЛИ', origin=(0, 0), background=True)


def input(key):
    if start:
        if key == 'left mouse down':
            player.gun.shooting.start()
        if key == 'left mouse up':
            player.gun.shooting.pause()
            camera.fov = 10


def shake_cam():
    vec = (randint(-1, 1) * .15, randint(-1, 1) * .15, randint(-1, 1) * .15)
    camera.position += vec
    invoke(Func(setattr, camera, 'position', camera.position - vec), delay=.1)


def begin():
    global start
    start = True
    if not riptear.playing:
        riptear.play()
    camera.fov = 10


def change_fov(f):
    camera.fov += f


def cutscene():
    camera.fov = 23
    player.rotation_y = 0
    player.animate_rotation((0, 180, 0), duration=2, delay=41)
    dogma.play()
    for i in range(2000):
        Sequence((i + 1) * 0.02, Func(change_fov, -0.01), loop=False).start()
    Sequence(45, Func(riptear.play)).start()
    Sequence(45, Func(begin)).start()


# begin()
cutscene()
app.run()
