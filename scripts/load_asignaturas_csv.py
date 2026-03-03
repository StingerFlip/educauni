"""
Lee un CSV de asignaturas (delimitador ;) y extrae title y BacherlorsDegree.
Guarda el resultado en fixtures/asignaturas_unican.json.

Uso (desde la raíz del proyecto):
    python scripts/load_asignaturas_csv.py path/al/archivo.csv
    python scripts/load_asignaturas_csv.py path/al/archivo.csv --output fixtures/mi_salida.json
"""
import argparse
import csv
import json
from pathlib import Path


def main():
    parser = argparse.ArgumentParser(description="Extrae title y BacherlorsDegree de un CSV (;)")
    parser.add_argument("csv_path", type=Path, help="Ruta al archivo CSV")
    parser.add_argument(
        "--output", "-o",
        type=Path,
        default=Path("fixtures/asignaturas_unican.json"),
        help="Ruta del JSON de salida (default: fixtures/asignaturas_unican.json)",
    )
    parser.add_argument(
        "--encoding",
        default="utf-8",
        help="Codificación del CSV (default: utf-8)",
    )
    args = parser.parse_args()

    csv_path = args.csv_path
    if not csv_path.is_file():
        raise SystemExit(f"No se encuentra el archivo: {csv_path}")

    # Nombres de columnas en el CSV (respeta mayúsculas del archivo)
    title_key = "title"
    degree_key = "BacherlorsDegree"

    rows = []
    with open(csv_path, encoding=args.encoding, newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        if title_key not in reader.fieldnames or degree_key not in reader.fieldnames:
            raise SystemExit(
                f"El CSV debe tener columnas '{title_key}' y '{degree_key}'. "
                f"Encontradas: {reader.fieldnames}"
            )
        for row in reader:
            title = (row.get(title_key) or "").strip()
            degree = (row.get(degree_key) or "").strip()
            if not title and not degree:
                continue
            rows.append({
                "identifier": (row.get("identifier") or "").strip().strip('"'),
                "title": title,
                "BacherlorsDegree": degree,
            })

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with open(args.output, "w", encoding="utf-8") as f:
        json.dump(rows, f, ensure_ascii=False, indent=2)

    print(f"Extraídas {len(rows)} filas → {args.output}")


if __name__ == "__main__":
    main()
