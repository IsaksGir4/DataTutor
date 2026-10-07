import sys
import psycopg
import httpx

# Configuración quemada solo para el script de verificación
DB_URL = "postgresql://postgres:postgres@localhost:5432/datatutor"
OLLAMA_URL = "http://localhost:11434"
KEYCLOAK_JWKS = "http://localhost:8080/realms/datatutor/protocol/openid-connect/certs"


def check_postgres():
    print("[-] Verificando PostgreSQL y pgvector...")
    try:
        with psycopg.connect(DB_URL) as conn:
            with conn.cursor() as cur:
                # Intenta crear la extensión si no existe y verifica
                cur.execute("CREATE EXTENSION IF NOT EXISTS vector;")
                cur.execute("SELECT extname FROM pg_extension WHERE extname = 'vector';")
                res = cur.fetchone()
                if res:
                    print("  [OK] PostgreSQL conectado y pgvector disponible.")
                else:
                    print("  [ERROR] PostgreSQL conectado, pero pgvector no está instalado.")
                    sys.exit(1)
    except Exception as e:
        print(f"  [ERROR] Falló la conexión a PostgreSQL: {e}")
        sys.exit(1)


def check_ollama():
    print("[-] Verificando Ollama y modelos...")
    try:
        with httpx.Client(timeout=10.0) as client:
            # Verificar modelo de chat
            chat_payload = {
                "model": "qwen2.5:3b",
                "prompt": "Responde 'ok'",
                "stream": False,
                "options": {"num_ctx": 4096}
            }
            res_chat = client.post(f"{OLLAMA_URL}/api/generate", json=chat_payload)
            if res_chat.status_code == 200:
                print("  [OK] Ollama responde y qwen2.5:3b está disponible con num_ctx=4096.")
            else:
                print(
                    f"  [ERROR] qwen2.5:3b no disponible. Código: {res_chat.status_code}. ¿Ejecutaste 'ollama run qwen2.5:3b'?")
                sys.exit(1)

            # Verificar modelo de embeddings
            embed_payload = {
                "model": "bge-m3",
                "input": "prueba de embedding"
            }

            res_embed = client.post(
                f"{OLLAMA_URL}/api/embed",
                json=embed_payload
            )

            if res_embed.status_code == 200:
                embeddings = res_embed.json().get("embeddings", [])

                if embeddings and len(embeddings[0]) == 1024:
                    print("  [OK] bge-m3 disponible y generando embeddings de dimensión 1024.")
                else:
                    dimension = len(embeddings[0]) if embeddings else 0
                    print(f"  [ERROR] Dimensión incorrecta: {dimension}")
                    sys.exit(1)
            else:
                print(
                    f"  [ERROR] bge-m3 no disponible. "
                    f"Código: {res_embed.status_code}"
                )
                sys.exit(1)
    except Exception as e:
        print(f"  [ERROR] Falló la conexión a Ollama (¿Está corriendo?): {e}")
        sys.exit(1)


def check_keycloak():
    print("[-] Verificando Keycloak JWKS...")
    try:
        with httpx.Client(timeout=5.0) as client:
            res = client.get(KEYCLOAK_JWKS)
            if res.status_code == 200 and "keys" in res.json():
                print("  [OK] Keycloak en línea y exponiendo claves JWKS.")
            else:
                print(f"  [ERROR] Keycloak no expone JWKS. Código: {res.status_code}")
                sys.exit(1)
    except Exception as e:
        print(f"  [ERROR] Falló la conexión a Keycloak: {e}")
        sys.exit(1)


if __name__ == "__main__":
    check_postgres()
    check_keycloak()
    check_ollama()
    print("\n🚀 Todos los sistemas base están operativos. ¡Entorno validado!")