import httpx
import sys

TOKEN_URL = "http://127.0.0.1:8080/realms/datatutor/protocol/openid-connect/token"
API_URL = "http://127.0.0.1:8000/api/v1/chat"


def get_token(username, password):
    data = {
        "client_id": "datatutor-swagger",
        "username": username,
        "password": password,
        "grant_type": "password"
    }
    r = httpx.post(TOKEN_URL, data=data)
    if r.status_code != 200:
        print(f"[ERROR] Falló autenticación para {username}: {r.status_code}")
        sys.exit(1)
    return r.json()["access_token"]


def main():
    print("[-] 1. Solicitando tokens para 'estudiante' y 'admin'...")
    token_user1 = get_token("estudiante", "estudiante123")
    token_user2 = get_token("admin", "admin123")
    print("  [OK] Tokens obtenidos.")

    print("\n[-] 2. Prueba de Seguridad: Petición sin token...")
    r_fail1 = httpx.post(API_URL, json={"question": "hola"})
    assert r_fail1.status_code == 401, f"Fallo: Esperaba 401, obtuve {r_fail1.status_code}"
    print("  [OK] Bloqueada correctamente (401).")

    print("\n[-] 3. Prueba de Seguridad: Petición con token manipulado...")
    # Cortamos el token original e inyectamos basura para invalidar la firma RSA
    r_fail2 = httpx.post(API_URL, json={"question": "hola"},
                         headers={"Authorization": f"Bearer {token_user1[:-10]}xxxxxxxxxx"})
    assert r_fail2.status_code == 401, f"Fallo: Esperaba 401, obtuve {r_fail2.status_code}"
    print("  [OK] Token manipulado bloqueado (401).")

    print("\n[-] 4. Prueba Funcional: Flujo completo RAG (Usuario 1)...")
    headers1 = {"Authorization": f"Bearer {token_user1}"}
    r_api1 = httpx.post(API_URL, json={"question": "¿Cuáles son las 7 formas en que falla un proyecto de datos?"},
                        headers=headers1, timeout=90.0)
    assert r_api1.status_code == 200, f"Error en API: {r_api1.text}"
    res1 = r_api1.json()
    conv_id = res1['conversation_id']
    print(f"  [OK] Respuesta exitosa generada y guardada. ID Conversación: {conv_id}")

    print("\n[-] 5. Prueba de Aislamiento: Usuario 2 intenta secuestrar la conversación del Usuario 1...")
    headers2 = {"Authorization": f"Bearer {token_user2}"}
    r_api2 = httpx.post(API_URL, json={"question": "Dime más", "conversation_id": conv_id}, headers=headers2,
                        timeout=60.0)
    assert r_api2.status_code == 404, f"Fallo crítico: Esperaba 404 genérico para proteger privacidad, obtuve {r_api2.status_code}"
    print("  [OK] Acceso denegado correctamente (404), usuarios aislados.")

    print("\n🚀 TODAS LAS VALIDACIONES SUPERADAS.")


if __name__ == "__main__":
    main()