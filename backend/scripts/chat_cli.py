
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))

from app.agents.graph import agent_app


def main():
    print("DataTutor CLI (escribe 'salir' para terminar)")

    while True:
        try:
            question = input("\nTú: ").strip()

            if question.lower() in {"salir", "exit", "quit"}:
                break

            if not question:
                continue

            state_input = {
                "question": question,
                "owner_id": "global",
                "history": [],
                "retries": 0,
            }

            final_state = {}

            print("Procesando el grafo...")

            # Ejecutar el grafo una sola vez.
            for event in agent_app.stream(
                state_input,
                stream_mode="updates",
            ):
                for node, node_state in event.items():
                    print(f"  [>] Nodo ejecutado: {node}")

                    if isinstance(node_state, dict):
                        final_state.update(node_state)

            print(
                f"\nDataTutor ({final_state.get('decision', 'N/A')}):"
            )
            print(final_state.get("answer", "Sin respuesta."))

            sources = final_state.get("sources", [])

            if sources:
                print("\nFuentes:")

                for source in sources:
                    print(
                        f"  - {source['document']} "
                        f"(pág. {source['page']}) "
                        f"[Similitud: {source['score']:.3f}]"
                    )

        except KeyboardInterrupt:
            print("\nEjecución interrumpida.")
            break

        except Exception as exc:
            print(f"\n[ERROR] Falló la ejecución: {exc}")


if __name__ == "__main__":
    main()
