import os
from openai import OpenAI

PROMPT = (
    "Analiza la imagen y devuelve SOLO un JSON con esta forma: "
    '{"queries": ["query 1", "query 2", "query 3"]}. '
    "Las queries deben servir para buscar modelos STL o 3D print similares. "
    "No agregues texto fuera del JSON."
)


def get_client():
    api_key = os.getenv("OPENAI_API_KEY")
    if not api_key:
        raise RuntimeError("OPENAI_API_KEY no configurada")
    return OpenAI(api_key=api_key)
