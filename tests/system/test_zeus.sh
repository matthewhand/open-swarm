#!/bin/bash
# System smoke test for zeus CLI registration
python3 -c 'from swarm.blueprints.zeus.blueprint_zeus import ZeusCoordinatorBlueprint; print(ZeusCoordinatorBlueprint.get_metadata())'
