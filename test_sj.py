import database
import json

propiedades, _ = database.buscar_propiedades(None, None, "San Juan", None, recamaras=4, banios=3)
print(f"Propiedades para 'San Juan' con 4 rec e 3 banios: {len(propiedades)}")
for p in propiedades:
    print(f"- {p.get('clave')}: {p.get('municipio')} - {p.get('recamaras')} rec, {p.get('banios')} banios - {p.get('precio')}")
