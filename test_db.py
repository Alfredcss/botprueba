import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from database import buscar_propiedades

print("Test 1: Only Fovissste")
res, _ = buscar_propiedades(tipo_inmueble="Casa", tipo_operacion="Venta", zona="San Juan del Río", presupuesto=30000000, caracteristica=None, tipo_credito="fovissste")
print(f"Found: {len(res)}")
for p in res: print(f" - {p.get('id')} / {p.get('clave')} / {p.get('precio')}")

print("\nTest 2: With caracteristica='acepte'")
res, _ = buscar_propiedades(tipo_inmueble="Casa", tipo_operacion="Venta", zona="San Juan del Río", presupuesto=30000000, caracteristica="acepte", tipo_credito="fovissste")
print(f"Found: {len(res)}")
for p in res: print(f" - {p.get('id')} / {p.get('clave')} / {p.get('precio')}")

print("\nTest 3: No zona, but 30M budget, Fovissste")
res, _ = buscar_propiedades(tipo_inmueble="Casa", tipo_operacion="Venta", zona=None, presupuesto=30000000, caracteristica=None, tipo_credito="fovissste")
print(f"Found: {len(res)}")
for p in res: print(f" - {p.get('id')} / {p.get('clave')} / {p.get('precio')}")
