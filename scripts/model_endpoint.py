"""Load the endpoint contract without importing an OVOS skill."""
import importlib.util
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    '_jarvis_endpoint', Path(__file__).resolve().parents[1] /
    'ovos_skill_jarvis_dispatcher/model_endpoint.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
model_port = module.model_port
GENERAL_PORT = module.GENERAL_PORT
PRIVATE_PORT = module.PRIVATE_PORT
