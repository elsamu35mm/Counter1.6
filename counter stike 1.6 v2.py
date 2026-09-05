import sys
import random
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from direct.gui.OnscreenText import OnscreenText
from panda3d.core import (
    WindowProperties,
    Vec3,
    CollisionTraverser,
    CollisionNode,
    CollisionRay,
    CollisionHandlerQueue,
    BitMask32,
    TextNode
)

# Configuración de las armas estilo CS 1.6
WEAPONS = {
    "AK-47": {"ammo": 30, "max_ammo": 30, "damage": 35, "fire_rate": 0.1, "recoil": 1.2},
    "M4A1":  {"ammo": 30, "max_ammo": 30, "damage": 30, "fire_rate": 0.09, "recoil": 0.8},
    "AWP":   {"ammo": 10, "max_ammo": 10, "damage": 100, "fire_rate": 1.2, "recoil": 4.0}
}

class CSAdvancedGame(ShowBase):
    def __init__(self):
        super().__init__()

        # --- Configuración de Ventana y Captura de Ratón ---
        props = WindowProperties()
        props.setCursorHidden(True)
        props.setMouseMode(WindowProperties.M_relative)
        self.win.requestProperties(props)
        self.disableMouse()

        # --- Estado del Jugador ---
        self.health = 100
        self.speed = 18.0
        self.sensitivity = 0.15
        self.key_map = {"forward": False, "back": False, "left": False, "right": False}
        
        # Físicas y Salto
        self.velocity_z = 0.0
        self.gravity = -35.0
        self.jump_force = 12.0
        self.is_grounded = True
        self.eye_height = 2.0

        # --- Sistema de Armas ---
        self.current_weapon_name = "AK-47"
        self.weapons_state = {k: v.copy() for k, v in WEAPONS.items()}
        self.can_shoot = True
        self.is_reloading = False

        # --- Configuración de Cámara e Iluminación ---
        self.camera.setPos(0, 0, self.eye_height)

        # --- Sistema de Colisiones y Raycasting ---
        self.cTrav = CollisionTraverser()
        self.ray_queue = CollisionHandlerQueue()
        self.picker_node = CollisionNode('shootRay')
        self.picker_np = self.camera.attachNewNode(self.picker_node)
        self.picker_node.setFromCollideMask(BitMask32.bit(1))
        self.picker_ray = CollisionRay()
        self.picker_node.addSolid(self.picker_ray)
        self.cTrav.addCollider(self.picker_np, self.ray_queue)

        # --- Inicialización de la Escena, HUD y Controles ---
        self.setup_scene()
        self.setup_hud()
        self.setup_controls()

        # Bucle principal de actualización
        self.taskMgr.add(self.update_game, "UpdateGame")

    def setup_scene(self):
        # Escenario
        self.environment = self.loader.loadModel("models/environment")
        self.environment.reparentTo(self.render)
        self.environment.setScale(0.3)
        self.environment.setPos(-8, 42, 0)

        # Crear Bot Enemigo (Representado por una estructura 3D)
        self.bot = self.loader.loadModel("models/box")
        self.bot.reparentTo(self.render)
        self.bot.setPos(0, 25, 1.5)
        self.bot.setScale(1.2, 1.2, 3)
        self.bot_health = 100

        # Máscara de Colisión para el Bot
        bot_cnode = self.bot.attachNewNode(CollisionNode('bot_hitbox'))
        bot_cnode.node().addSolid(CollisionRay(0, 0, 0, 0, 1, 0))
        bot_cnode.node().setIntoCollideMask(BitMask32.bit(1))

    def setup_hud(self):
        # Retícula central (Crosshair)
        self.crosshair = OnscreenText(text="+", pos=(0, 0), scale=0.08, fg=(0, 1, 0, 1), align=TextNode.ACenter)
        
        # HUD Inferior estilo CS 1.6
        self.hud_health = OnscreenText(text="SALUD: 100", pos=(-1.1, -0.85), scale=0.07, fg=(1, 0.3, 0.3, 1), align=TextNode.ALeft)
        self.hud_weapon = OnscreenText(text="ARMA: AK-47", pos=(1.1, -0.78), scale=0.06, fg=(1, 0.9, 0.2, 1), align=TextNode.ARight)
        self.hud_ammo = OnscreenText(text="MUNICIÓN: 30 / 30", pos=(1.1, -0.88), scale=0.07, fg=(1, 0.9, 0.2, 1), align=TextNode.ARight)
        self.hud_status = OnscreenText(text="", pos=(0, -0.5), scale=0.06, fg=(1, 1, 1, 1), align=TextNode.ACenter)

    def setup_controls(self):
        # Movimiento WASD
        self.accept("w", self.set_key, ["forward", True])
        self.accept("w-up", self.set_key, ["forward", False])
        self.accept("s", self.set_key, ["back", True])
        self.accept("s-up", self.set_key, ["back", False])
        self.accept("a", self.set_key, ["left", True])
        self.accept("a-up", self.set_key, ["left", False])
        self.accept("d", self.set_key, ["right", True])
        self.accept("d-up", self.set_key, ["right", False])

        # Acciones adicionales
        self.accept("space", self.jump)
        self.accept("r", self.reload_weapon)
        self.accept("mouse1", self.shoot)
        
        # Selección de Armas (1, 2, 3)
        self.accept("1", self.select_weapon, ["AK-47"])
        self.accept("2", self.select_weapon, ["M4A1"])
        self.accept("3", self.select_weapon, ["AWP"])
        
        self.accept("escape", sys.exit)

    def set_key(self, key, value):
        self.key_map[key] = value

    def select_weapon(self, name):
        if not self.is_reloading:
            self.current_weapon_name = name
            self.update_hud()

    def jump(self):
        if self.is_grounded:
            self.velocity_z = self.jump_force
            self.is_grounded = False

    def reload_weapon(self):
        w_data = self.weapons_state[self.current_weapon_name]
        if w_data["ammo"] < w_data["max_ammo"] and not self.is_reloading:
            self.is_reloading = True
            self.hud_status.setText("-- RECARGANDO --")
            self.taskMgr.doMethodLater(1.8, self.finish_reload, "FinishReload")

    def finish_reload(self, task):
        w_data = self.weapons_state[self.current_weapon_name]
        w_data["ammo"] = w_data["max_ammo"]
        self.is_reloading = False
        self.hud_status.setText("")
        self.update_hud()
        return Task.done

    def shoot(self):
        if self.is_reloading or not self.can_shoot:
            return

        w_data = self.weapons_state[self.current_weapon_name]
        if w_data["ammo"] <= 0:
            self.hud_status.setText("¡SIN MUNICIÓN! Presiona R para recargar")
            return

        # Consumo de munición
        w_data["ammo"] -= 1
        self.update_hud()

        # Tiempo de cadencia entre disparos
        self.can_shoot = False
        self.taskMgr.doMethodLater(WEAPONS[self.current_weapon_name]["fire_rate"], self.reset_shoot, "ResetShoot")

        # Aplicar retroceso visual (Recoil)
        recoil = WEAPONS[self.current_weapon_name]["recoil"]
        self.camera.setP(self.camera.getP() + recoil)

        # Raycast para impacto de bala
        self.picker_ray.setFromLens(self.camNode, 0, 0)
        self.cTrav.traverse(self.render)

        if self.ray_queue.getNumEntries() > 0:
            self.ray_queue.sortEntries()
            hit_obj = self.ray_queue.getEntry(0).getIntoNodePath()

            if hit_obj.isAncestorOf(self.bot):
                self.bot_health -= w_data["damage"]
                print(f"Impacto en bot! Salud restante: {self.bot_health}")
                if self.bot_health <= 0:
                    self.respawn_bot()

    def reset_shoot(self, task):
        self.can_shoot = True
        return Task.done

    def respawn_bot(self):
        self.bot_health = 100
        # Reubicar el bot aleatoriamente
        self.bot.setPos(random.uniform(-10, 10), random.uniform(20, 35), 1.5)

    def update_hud(self):
        w_data = self.weapons_state[self.current_weapon_name]
        self.hud_weapon.setText(f"ARMA: {self.current_weapon_name}")
        self.hud_ammo.setText(f"MUNICIÓN: {w_data['ammo']} / {w_data['max_ammo']}")
        self.hud_health.setText(f"SALUD: {self.health}")

    def update_game(self, task):
        dt = globalClock.getDt()

        # --- 1. Control de Visión con Ratón ---
        if self.mouseWatcherNode.hasMouse():
            md = self.win.getPointer(0)
            center_x = self.win.getProperties().getXSize() // 2
            center_y = self.win.getProperties().getYSize() // 2

            delta_x = md.getX() - center_x
            delta_y = md.getY() - center_y

            self.camera.setH(self.camera.getH() - delta_x * self.sensitivity)
            self.camera.setP(self.camera.getP() - delta_y * self.sensitivity)

            # Límite de Pitch (-89° a 89°)
            if self.camera.getP() > 89: self.camera.setP(89)
            if self.camera.getP() < -89: self.camera.setP(-89)

            self.win.movePointer(0, center_x, center_y)

        # --- 2. Movimiento Horizontal del Jugador ---
        move_vec = Vec3(0, 0, 0)
        if self.key_map["forward"]: move_vec.addY(1)
        if self.key_map["back"]: move_vec.addY(-1)
        if self.key_map["left"]: move_vec.addX(-1)
        if self.key_map["right"]: move_vec.addX(1)

        move_vec.normalize()
        self.camera.setPos(self.camera, move_vec * self.speed * dt)

        # --- 3. Física de Gravedad y Salto ---
        cam_pos = self.camera.getPos()
        self.velocity_z += self.gravity * dt
        cam_pos.setZ(cam_pos.getZ() + self.velocity_z * dt)

        # Colisión básica con el suelo
        if cam_pos.getZ() <= self.eye_height:
            cam_pos.setZ(self.eye_height)
            self.velocity_z = 0.0
            self.is_grounded = True

        self.camera.setPos(cam_pos)

        # --- 4. IA del Bot (Comportamiento simple) ---
        # El bot rota para mirar permanentemente al jugador
        self.bot.lookAt(self.camera)

        return Task.cont

if __name__ == "__main__":
    game = CSAdvancedGame()
    game.run()