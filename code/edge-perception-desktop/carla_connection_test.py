import carla

def main():
    client = carla.Client("127.0.0.1", 2000)
    client.set_timeout(20.0)

    print("client version:", client.get_client_version())
    print("server version:", client.get_server_version())

    world = client.get_world()
    print("current map:", world.get_map().name)

    maps = client.get_available_maps()
    print(f"available maps ({len(maps)}):")
    for m in maps:
        print(" -", m)

    settings = world.get_settings()
    print("synchronous_mode:", settings.synchronous_mode)
    print("fixed_delta_seconds:", settings.fixed_delta_seconds)

if __name__ == "__main__":
    main()
