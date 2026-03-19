#!
'''Programa para la simulación de los productos amortizables de COF_ES'''

import datetime as dt
import calendar as cl
from decimal import Decimal, ROUND_HALF_UP, getcontext
import pandas as pd
import bin.COFES___TAE as tools_tae
import bin.COFES___tools as tools



getcontext().prec = 10

# ---------------------------------------------------------
# FUNCIONES AUXILIARES
# ---------------------------------------------------------

def primer_recibo(fecha_inicio):
    if fecha_inicio.day < 2:
        return fecha_inicio.replace(day=2)
    if fecha_inicio.month == 12:
        return dt.date(fecha_inicio.year + 1, 1, 2)
    return dt.date(fecha_inicio.year, fecha_inicio.month + 1, 2)

def siguiente_recibo(fecha):
    if fecha.month == 12:
        return dt.date(fecha.year + 1, 1, 2)
    return dt.date(fecha.year, fecha.month + 1, 2)

FECHAS_BLOQUEO = pd.read_csv('./data/COFES_01_Date_Blocage.csv', sep=';', parse_dates=['Fecha_BLOQUEO'], dayfirst=True).sort_values(by='Fecha_BLOQUEO')

    
''Calcular la fecha del primer vencimiento en base a la fecha de bloqueo posterior a la fecha de financiación'''
    proximas_db = FECHAS_BLOQUEO[FECHAS_BLOQUEO['Fecha_BLOQUEO'] >= fecha_financiacion]
    fecha_primer_vencimiento = proximas_db['Fecha_BLOQUEO'].iloc[0].replace(day=dia_pago) + pd.DateOffset(months=1)


# ---------------------------------------------------------
# CALCULO INTERESES
# ---------------------------------------------------------

def interes_preciso(capital, tin, fecha_inicio, fecha_fin):

    capital = Decimal(str(capital))
    tin = Decimal(str(tin)) / Decimal("100")

    fecha_inicio = pd.to_datetime(fecha_inicio).date()
    fecha_fin = pd.to_datetime(fecha_fin).date()

    interes_diciembre = Decimal("0")
    interes_enero = Decimal("0")

    if fecha_fin.month == 1 and fecha_inicio.year < fecha_fin.year:

        year_prev = fecha_inicio.year
        year_curr = fecha_fin.year

        bisiesto_prev = cl.isleap(year_prev)
        bisiesto_curr = cl.isleap(year_curr)

        if bisiesto_prev != bisiesto_curr:

            dias_dic = 29
            base_dic = 366 if bisiesto_prev else 365

            interes_diciembre = (
                capital * tin * Decimal(dias_dic) / Decimal(base_dic)
            ).quantize(Decimal("0.00001"))

            dias_ene = (fecha_fin - dt.date(year_curr,1,1)).days + 1
            base_ene = 366 if bisiesto_curr else 365

            interes_enero = (
                capital * tin * Decimal(dias_ene) / Decimal(base_ene)
            ).quantize(Decimal("0.00001"))

            interes_total = (interes_diciembre + interes_enero).quantize(Decimal("0.00001"))

            return interes_total, interes_diciembre, interes_enero

    dias_tramo = (fecha_fin - fecha_inicio).days
    base = tools.dias_año(fecha_inicio)

    interes_total = (
        capital * tin * Decimal(dias_tramo) / Decimal(base)
    ).quantize(Decimal("0.00001"))

    return interes_total, Decimal("0"), interes_total

# ---------------------------------------------------------
# SIMULADOR
# ---------------------------------------------------------

def simulador(capital, tin, tipo_calculo, valor, fecha_inicio, seguro_tasa=0):

    capital = Decimal(str(capital))
    saldo = capital
    seguro_tasa = Decimal(str(seguro_tasa))

    fecha_pago = primer_recibo(fecha_inicio)
    fecha_anterior = fecha_inicio

    datos = []
    mes = 1

    if tipo_calculo == "Vitesse":
        cuota = (capital * Decimal(str(valor)) / Decimal("100")).quantize(Decimal("0.01"),ROUND_HALF_UP)

    elif tipo_calculo == "Cuota":
        cuota = Decimal(str(valor)).quantize(Decimal("0.01"),ROUND_HALF_UP)

    while saldo > 0:

        interes_total, interes_dic, interes_ene = interes_preciso(
            saldo, tin, fecha_anterior, fecha_pago
        )

        interes_total = interes_total.quantize(Decimal("0.01"),ROUND_HALF_UP)

        seguro = ((saldo + interes_total) * seguro_tasa).quantize(Decimal("0.01"),ROUND_HALF_UP)

        if saldo + interes_total <= cuota:

            amort = saldo.quantize(Decimal("0.01"),ROUND_HALF_UP)
            saldo = Decimal("0")

            cuota_final = (amort + interes_total).quantize(Decimal("0.01"),ROUND_HALF_UP)

        else:

            amort = (cuota - interes_total).quantize(Decimal("0.01"),ROUND_HALF_UP)
            saldo = (saldo - amort).quantize(Decimal("0.01"),ROUND_HALF_UP)

            cuota_final = cuota

        datos.append({
            "Mes": mes,
            "Fecha recibo": fecha_pago,
            "Capital pendiente (€)": float(saldo + amort),
            "Cuota (€)": float(cuota_final),
            "Intereses diciembre (€)": float(interes_dic),
            "Intereses enero (€)": float(interes_ene),
            "Intereses total (€)": float(interes_total),
            "Amortización (€)": float(amort),
            "Saldo (€)": float(saldo),
            "Seguro (€)": float(seguro),
            "Recibo total (€)": float(cuota_final + seguro)
        })

        fecha_anterior = fecha_pago
        fecha_pago = siguiente_recibo(fecha_pago)

        mes += 1

        if mes > 600:
            break

    return pd.DataFrame(datos)

# ---------------------------------------------------------
# CALCULO TAE
# ---------------------------------------------------------

def calcular_tae(cuotas, fechas):

    tiempos=[0.0]

    for i in range(1,len(fechas)):
        f0=pd.to_datetime(fechas[i-1]).date()
        f1=pd.to_datetime(fechas[i]).date()

        fraccion=(f1-f0).days/tools.dias_año(f0)
        tiempos.append(tiempos[-1]+fraccion)

    def van(tasa):
        return sum(c/((1+tasa)**t) for c,t in zip(cuotas,tiempos))

    minimo=-0.9999
    maximo=10

    for _ in range(1000):

        medio=(minimo+maximo)/2
        valor=van(medio)

        if abs(valor)<1e-10:
            return round(medio*100,2)

        if valor>0:
            minimo=medio
        else:
            maximo=medio

    return round(medio*100,2)

