import argparse

from swarm.blueprints.zeus.blueprint_zeus import ZeusCoordinatorBlueprint


def main():
    parser = argparse.ArgumentParser(description="Zeus: Coordinator agent demo")
    parser.add_argument("--message", type=str, help="User message to process", default="Summon the pantheon!")
    args = parser.parse_args()
    bp = ZeusCoordinatorBlueprint()
    response = bp.assist(args.message)
    print(response)

if __name__ == "__main__":
    main()
