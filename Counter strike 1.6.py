import sys
from direct.showbase.ShowBase import ShowBase
from direct.task import Task
from panda3d.core import (
    WindowProperties,
    Vec3,
    CollisionTraverser,
    CollisionNode,
    CollisionRay,
    CollisionHandlerQueue,
    BitMask32
)

class CounterStrikeBase(ShowBase):
    def __init__(self):
        super().__init__()

        # Configuración de la ventana y ocultar el cursor
        props = WindowProperties()
        props.setCursorHidden(True)
        props.setMouseMode(WindowProperties.M_relative)
        self.win.requestProperties(props)

        # Iluminación básica
        self.disableMouse()  # Desactivar el control por defecto de la cámara

        # Variables de movimiento del jugador
        self.speed = 15.0
        self.sensitivity = 0.15
        self.key_map = {"forward": False, "back": False, "left": False, "right": False}

        # Posición inicial de la cámara (Ojos del jugador)
        self.camera.setPos(0, 0, 2)

        # Sistema de colisiones para disparos (Raycasting)
        self.cTrav = CollisionTraverser()
        self.ray_queue = CollisionHandlerQueue()
        self.picker_node = CollisionNode('mouseRay')
        self.picker_np = self.camera.attachNewNode(self.picker_node)
        self.picker_node.setFromCollideMask(BitMask32.bit(1))
        self.picker_ray = CollisionRay()
        self.picker_node.addSolid(self.picker_ray)
        self.cTrav.addCollider(self.picker_np, self.ray_queue)

        # Cargar entorno y blanco de prueba
        self.setup_scene()

        # Configurar controles de teclado y ratón
        self.setup_controls()

        # Tareas de actualización por frame
        self.taskMgr.add(self.update_player, "UpdatePlayer")

    def setup_scene(self):
        # Cargar modelo de entorno (caja por defecto de Panda3D como suelo)
        self.environment = self.loader.loadModel("models/environment")
        self.environment.reparentTo(self.render)
        self.environment.setScale(0.25, 0.25, 0.25)
        self.environment.setPos(-8, 42, 0)

        # Crear un objetivo de práctica (enemigo)
        self.target = self.loader.loadModel("models/box")
        self.target.reparentTo(self.render)
        self.target.setPos(0, 15, 1)
        self.target.setScale(1, 1, 2)
        
        # Asignar máscara de colisión al objetivo para detectar disparos
        target_cnode = self.target.attachNewNode(CollisionNode('target_node'))
        target_cnode.node().addSolid(CollisionRay(0, 0, 0, 0, 1, 0))
        target_cnode.node().setIntoCollideMask(BitMask32.bit(1))

    def setup_controls(self):
        # Mapeo de teclas
        self.accept("w", self.set_key, ["forward", True])
        self.accept("w-up", self.set_key, ["forward", False])
        self.accept("s", self.set_key, ["back", True])
        self.accept("s-up", self.set_key, ["back", False])
        self.accept("a", self.set_key, ["left", True])
        self.accept("a-up", self.set_key, ["left", False])
        self.accept("d", self.set_key, ["right", True])
        self.accept("d-up", self.set_key, ["right", False])
        
        # Disparo y salir
        self.accept("mouse1", self.shoot)
        self.accept("escape", sys.exit)

    def set_key(self, key, value):
        self.key_map[key] = value

    def update_player(self, task):
        dt = globalClock.getDt()

        # Control de cámara con el ratón
        if self.mouseWatcherNode.hasMouse():
            md = self.win.getPointer(0)
            x = md.getX()
            y = md.getY()

            center_x = self.win.getProperties().getXSize() // 2
            center_y = self.win.getProperties().getYSize() // 2

            delta_x = x - center_x
            delta_y = y - center_y

            # Rotación en H (Yaw) y P (Pitch)
            self.camera.setH(self.camera.getH() - delta_x * self.sensitivity)
            self.camera.setP(self.camera.getP() - delta_y * self.sensitivity)

            # Mantener el Pitch dentro de límites para no voltear la cámara completamente
            if self.camera.getP() > 89: self.camera.setP(89)
            if self.camera.getP() < -89: self.camera.setP(-89)

            # Reposicionar cursor al centro
            self.win.movePointer(0, center_x, center_y)

        # Movimiento de desplazamiento (WASD) relativo a la dirección de la cámara
        move_vec = Vec3(0, 0, 0)
        if self.key_map["forward"]: move_vec.addY(1)
        if self.key_map["back"]: move_vec.addY(-1)
        if self.key_map["left"]: move_vec.addX(-1)
        if self.key_map["right"]: move_vec.addX(1)

        move_vec.normalize()
        self.camera.setPos(self.camera, move_vec * self.speed * dt)

        # Mantener la altura del jugador constante (física básica de suelo)
        self.camera.setZ(2)

        return Task.cont

    def shoot(self):
        # Raycast desde el centro de la pantalla
        self.picker_ray.setFromLens(self.camNode, 0, 0)
        self.cTrav.traverse(self.render)

        if self.ray_queue.getNumEntries() > 0:
            self.ray_queue.sortEntries()
            hit_obj = self.ray_queue.getEntry(0).getIntoNodePath()
            
            # Verificar si se impactó al objetivo
            if hit_obj.isAncestorOf(self.target):
                print("¡Impacto confirmado!")
                # Cambiar posición del objetivo como respuesta al disparo
                self.target.setX(self.target.getX() + 2)

if __name__ == "__main__":
    game = CounterStrikeBase()
    game.run()