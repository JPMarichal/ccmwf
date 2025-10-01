"""Configuraciones comunes de pytest para el proyecto CCM."""

import sys
from pathlib import Path

# Asegurar que `src/` esté en PYTHONPATH para importar paquetes `app.*`
ROOT_PATH = Path(__file__).resolve().parents[1]
SRC_PATH = ROOT_PATH

if str(SRC_PATH) not in sys.path:
    sys.path.insert(0, str(SRC_PATH))
