import os
import time
import carla

HOST = "127.0.0.1"
PORT = 2000
DURATION_SEC = 30
NUM_FRAMES_TO_SAVE = 10
OUTPUT_DIR = os.path.expanduser("~/portfolio_autonomous/carla_output/frames")


def main():
    os.makedirs(OUTPUT_DIR, exist_ok=True)

    client = carla.Client(HOST, PORT)
    client.set_timeout(20.0)
    world = client.get_world()
    print("connected. map:", world.get_map().name)

    blueprint_library = world.get_blueprint_library()
    vehicle_bp = blueprint_library.filter("vehicle.tesla.model3")[0]
    spawn_points = world.get_map().get_spawn_points()
    if not spawn_points:
        raise RuntimeError("no spawn points on this map")

    vehicle = None
    camera = None
    saved_count = [0]

    try:
        for sp in spawn_points:
            vehicle = world.try_spawn_actor(vehicle_bp, sp)
            if vehicle is not None:
                break
        if vehicle is None:
            raise RuntimeError("failed to spawn vehicle at any spawn point")
        print("vehicle spawned:", vehicle.type_id, "id=", vehicle.id)

        vehicle.set_autopilot(True)

        camera_bp = blueprint_library.find("sensor.camera.rgb")
        camera_bp.set_attribute("image_size_x", "640")
        camera_bp.set_attribute("image_size_y", "480")
        camera_bp.set_attribute("fov", "90")
        camera_transform = carla.Transform(carla.Location(x=1.5, z=2.4))
        camera = world.spawn_actor(camera_bp, camera_transform, attach_to=vehicle)
        print("camera attached:", camera.type_id, "id=", camera.id)

        def on_image(image):
            if saved_count[0] < NUM_FRAMES_TO_SAVE:
                path = os.path.join(OUTPUT_DIR, f"frame_{image.frame:06d}.png")
                image.save_to_disk(path)
                saved_count[0] += 1
                print("saved", path)

        camera.listen(on_image)

        t0 = time.time()
        while time.time() - t0 < DURATION_SEC:
            transform = vehicle.get_transform()
            velocity = vehicle.get_velocity()
            speed = (velocity.x ** 2 + velocity.y ** 2 + velocity.z ** 2) ** 0.5
            print(
                f"t={time.time()-t0:5.1f}s "
                f"loc=({transform.location.x:.1f},{transform.location.y:.1f}) "
                f"speed={speed*3.6:.1f}km/h "
                f"saved_frames={saved_count[0]}"
            )
            time.sleep(2)

        print(f"done. total frames saved: {saved_count[0]}")

    finally:
        if camera is not None:
            camera.stop()
            camera.destroy()
        if vehicle is not None:
            vehicle.destroy()
        print("actors cleaned up")


if __name__ == "__main__":
    main()
