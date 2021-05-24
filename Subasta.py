from pyomo.environ import *
import pandas as pd
from openpyxl import load_workbook
from os import getcwd
import xlwings as xw
from pandasql import sqldf
import matplotlib.pylab as plt

x1 = []
y1 = []
x2 = []
y2 = []
x11 = []
y11 = []
x22 = []
y22 = []
b = 0

#Definir objeto con archivo de excel
xlFile = getcwd() + r"\Set de datos.XLSX"            

# # Definir objeto con información de excel
xl_datos = pd.ExcelFile(xlFile)

#Definir modelo de optimizacion
modelo = ConcreteModel("SubastaRenovables")

#LECTURA DE DATOS;
precio_compra = xl_datos.parse("compradores").set_index(["ID_oferta"])
precio_venta = xl_datos.parse("vendedores").set_index(["ID_oferta"])


#Indices del modelo
modelo.compra = Set(initialize=precio_compra.index)
modelo.venta = Set(initialize=precio_venta.index)

#Definir variables de decision
modelo.asignacionc = Var( modelo.compra, domain=PositiveReals )
modelo.asignacionv = Var( modelo.venta, domain=PositiveReals )
modelo.c = Var( modelo.compra, domain=Binary )
modelo.v = Var( modelo.venta, domain=Binary )


#Funcion graficadora
for i in modelo.compra:
    x1.append(precio_compra.compra_max[i])
    y1.append(precio_compra.precio[i])

for i in modelo.venta:
    x2.append(precio_venta.venta_max[i])
    y2.append(precio_venta.precio[i])

#Ordenar datos de la grafica
x11.append(0)
y11.append(y1[0])
x22.append(0)
y22.append(y2[0])

for i in range(0, len(x1)):
    a = x1[i]
    b = b + a
    x11.append(b)
    
b = 0

for i in range(0, len(x2)):
    a = x2[i]
    b = b + a
    x22.append(b)

for i in range(0, len(y1)):
    a = y1[i]
    y11.append(a)

for i in range(0, len(y2)):
    a = y2[i]
    y22.append(a)

plt.step(x11, y11, label = "Oferta de los compradores")
plt.step(x22, y22, label = "Oferta de los vendedores")
plt.title("Maximizacion de los beneficios del consumidor")
plt.xlabel("Energia(kWh)")
plt.ylabel("Precio(COP$/kWh)")
plt.grid()
plt.legend()

#Definir funcion objetivo
def objetivo(modelo):
    expr1 = sum(precio_compra.precio[c]*modelo.asignacionc[c]
                for c in modelo.compra)
    expr2 = sum(precio_venta.precio[v]*modelo.asignacionv[v]
                for v in modelo.venta)
    result = expr1 - expr2
    return result
modelo.FO = Objective(rule=objetivo, sense = maximize)

#Definir restricciones
#restriccion compra maxima
def r1(modelo,i):
    ecuacion = modelo.asignacionc[i]
    return ecuacion <= precio_compra.compra_max[i]*modelo.c[i]
modelo.r1 = Constraint(modelo.compra, rule = r1)

#restriccion venta maxima
def r2(modelo,i):
    ecuacion = modelo.asignacionv[i]
    return ecuacion <= precio_venta.venta_max[i]*modelo.v[i]
modelo.r2 = Constraint(modelo.venta, rule = r2)

#restriccion venta minima
def r3(modelo,i):
    ecuacion = modelo.asignacionv[i]
    return ecuacion >= precio_venta.venta_min[i]*modelo.v[i]
modelo.r3 = Constraint(modelo.venta, rule = r3)

#restriccion de balance entre asignacion de venta y compra
def r4(modelo):
    ecuacion1 = sum(modelo.asignacionc[c]
                    for c in modelo.compra)
    ecuacion2 = sum(modelo.asignacionv[v]
                    for v in modelo.venta)
    result = ecuacion1 - ecuacion2
    return result == 0
modelo.r4 = Constraint(rule = r4)

#restriccion simultanea
def r5(modelo,i):
    if str(precio_venta.simultanea[i]) == 'nan':
        return Constraint.Skip
    ecuacion1 = modelo.v[i]
    ecuacion2 = modelo.v[precio_venta.simultanea[i]]
    result = ecuacion1 - ecuacion2
    return result == 0
modelo.r5 = Constraint(modelo.venta, rule = r5)

#restriccion excluyente
def r6(modelo,i):
    if str(precio_venta.excluyente[i]) == 'nan':
        return Constraint.Skip
    ecuacion1 = modelo.v[i]
    ecuacion2 = modelo.v[precio_venta.excluyente[i]]
    result = ecuacion1 + ecuacion2
    return result <= 1
modelo.r6 = Constraint(modelo.venta, rule = r6)

#restriccion dependiente
def r7(modelo,i):
    if str(precio_venta.dependiente[i]) == 'nan':
        return Constraint.Skip
    ecuacion1 = modelo.v[i]
    ecuacion2 = modelo.v[precio_venta.dependiente[i]]
    result = ecuacion1 - ecuacion2
    return result <= 0
modelo.r7 = Constraint(modelo.venta, rule = r7)

#restriccion compra minima(auxiliar)
def r8(modelo,i):
    ecuacion = modelo.asignacionc[i]
    return ecuacion >= 1*modelo.c[i]
modelo.r8 = Constraint(modelo.compra, rule = r8)

#restriccion del promedio ponderado de venta menor al precio tope promedio
def r9(modelo):
    ecuacion1 = sum(modelo.asignacionv[v]*precio_venta.precio[v]
                    for v in modelo.venta)
    ecuacion2 = sum(modelo.asignacionv[v]
                    for v in modelo.venta)
    return ecuacion1 <= ecuacion2*200
modelo.r9 = Constraint(rule = r9)

#restriccion de precios de venta menores al precio tope superior
def r10(modelo,i):
    if precio_venta.precio[i] <= 250:
        return Constraint.Skip
    return modelo.v[i] == 0
modelo.r10 = Constraint(modelo.venta, rule = r10)

#restriccion del promedio ponderado de venta menor al precio
#de los compradores asignados
def r11(modelo,i):
    ecuacion1 = sum(modelo.asignacionv[v]*precio_venta.precio[v]
                    for v in modelo.venta)
    ecuacion2 = sum(modelo.asignacionv[v]
                    for v in modelo.venta)
    return ecuacion1 - ecuacion2*precio_compra.precio[i] <= 99999999999*(1 - modelo.c[i])
modelo.r11 = Constraint(modelo.compra, rule = r11)

#Definir Optimizador
opt = SolverFactory('cbc')

#Escribir archivo .lp
modelo.write("archivo.lp",io_options={"symbolic_solver_labels":True})

#Ejecutar el modelo
results = opt.solve(modelo,tee=0,logfile ="archivo.log", keepfiles= 0,symbolic_solver_labels=True)

modelo.pprint()

a = 0
b = 0

a = sum(value(modelo.asignacionv[i])*value(precio_venta.precio[i])
        for i in modelo.venta)
b = sum(value(modelo.asignacionv[i])
        for i in modelo.venta)

print("promedio ponderado: ", a/b)


#Escribir resultados en el excel
if (results.solver.status == SolverStatus.ok) and (results.solver.termination_condition == TerminationCondition.optimal):

    #Imprimir Resultados
    print ()
    print ("funcion objetivo ", value(modelo.FO))

    #Escribir los resultados
    wb1 = xw.Book(xlFile)
    hoja_out1 = wb1.sheets["asignacion_compradores"]
    
    wb2 = xw.Book(xlFile)
    hoja_out2 = wb2.sheets["asignacion_vendedores"]

    columnas1 = ["Comprador", "ID_oferta", "Asignacion de compra(kWh-dia)"]
    columnas2 = ["Vendedor", "ID_oferta", "Bloque", "Asignacion de venta(kWh-bloque)"]

    out1_ = pd.DataFrame(columns=columnas1)
    out2_ = pd.DataFrame(columns=columnas2)

    fila1 = 0
    for i in modelo.compra:
        fila1 += 1
        salida1 = []
        salida1.append(precio_compra.nombre[i])
        salida1.append(i)
        salida1.append(modelo.asignacionc[i].value) 
        out1_.loc[fila1] = salida1

    fila2 = 0
    for i in modelo.venta:
        fila2 += 1
        salida2 = []
        salida2.append(precio_venta.nombre[i])
        salida2.append(i)
        salida2.append(precio_venta.bloque[i])
        salida2.append(modelo.asignacionv[i].value) 
        out2_.loc[fila2] = salida2

    hoja_out1.clear_contents()
    hoja_out1.range('A1').value = out1_
    hoja_out2.clear_contents()
    hoja_out2.range('A1').value = out2_

    ###################################

    p = []
    sumac = sum(value(modelo.asignacionc[i])
            for i in modelo.compra)
    
    for i in modelo.compra:
        p.append(value(modelo.asignacionc[i])/sumac)

    wb3 = xw.Book(xlFile)
    hoja_out3 = wb3.sheets["asignacion_prorrata"]
    columnas3 = ["Comprador", "Vendedor", "Bloque", "Asignacion(kWh)"]

    out3_ = pd.DataFrame(columns=columnas3)

    fila3 = 0
    rango = 0

    for i in modelo.compra:
        for j in modelo.venta:
            salida3 = []
            salida3.append(precio_compra.nombre[i])
            salida3.append(precio_venta.nombre[j])
            salida3.append(precio_venta.bloque[j])
            if precio_venta.bloque[j] == "B1":
                salida3.append((value(modelo.asignacionv[j])*p[rango])/7)

            if precio_venta.bloque[j] == "B2":
                salida3.append((value(modelo.asignacionv[j])*p[rango])/10)

            if precio_venta.bloque[j] == "B3":
                salida3.append((value(modelo.asignacionv[j])*p[rango])/7)
                
            fila3 += 1
            out3_.loc[fila3] = salida3
        rango  = rango + 1
    
    hoja_out3.clear_contents()
    hoja_out3.range('A1').value = out3_


elif (results.solver.termination_condition == TerminationCondition.infeasible):
	print()
	print("EL PROBLEMA ES INFACTIBLE")

elif(results.solver.termination_condition == TerminationCondition.unbounded):
	print()
	print("EL PROBLEMA ES INFACTIBLE")
else:
    print("TERMINÓ EJECUCIÓN CON ERRORES")

plt.show()
