def interactive_shell():
    print("Welcome to Swarm Core CLI Interactive Shell!")
    print("Type 'help' for available commands.")
    while True:
        try:
            cmd = input("swarm> ").strip()
            if cmd in ("exit", "quit"): break
            elif cmd == "help":
                print("Available commands: list, edit-config, validate-env, validate-envvars, blueprint-manage, config-manage")
            elif cmd:
                print(f"Command '{cmd}' not recognized (type 'help').")
        except KeyboardInterrupt:
            print("\nExiting shell.")
            break
