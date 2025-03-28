#!/usr/bin/env python
import os
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "swarm.settings")
import pytest
import sys
sys.exit(pytest.main())