from nutricosto.insumos import ParametrosLote
from nutricosto.modelo import resolver_simplex
from nutricosto.sacos import plan_de_compra

p = ParametrosLote()
s = resolver_simplex(p)
plan = plan_de_compra(p, s, lotes=10)

print(f'Plan para {plan.lotes} lotes = {plan.masa_total_kg:.0f} kg totales\n')
print(f'{"Insumo":<10} {"kg req":>8} {"kg/saco":>8} {"sacos":>6} {"sobrante":>9} {"S/. saco":>9} {"costo real":>11}')
print('-' * 70)
for f in plan.filas:
    print(f'{f.nombre:<10} {f.kg_requeridos:>8.2f} {f.kg_por_saco:>8.0f} {f.sacos_a_comprar:>6} {f.sobrante_kg:>9.2f} {f.precio_saco:>9.2f} {f.costo_real:>11.2f}')

total_sacos = sum(f.sacos_a_comprar for f in plan.filas)
print('-' * 70)
print(f'Total sacos a comprar:        {total_sacos}')
print(f'Costo real (sacos enteros):   S/. {plan.costo_real_total:.2f}')
print(f'Costo teorico continuo (kg):  S/. {plan.costo_teorico_total:.2f}')
print(f'Sobrecosto por discretizacion: S/. {plan.sobre_costo:.2f}')
