# Simulación del Problema de Parqueaderos – Centro Comercial Supercentro

## Descripción del Proyecto

Simulación de un sistema de pago de parqueaderos para el **Centro Comercial Supercentro** utilizando el modelo de colas **M/M/1** (Markoviano / Markoviano / 1 servidor). El sistema cuenta con múltiples cajeros automáticos en los puntos de salida, cada uno operando como una cola independiente.

El objetivo es evaluar si la cantidad actual de cajeros (3 por punto de salida) es suficiente para atender la demanda de los diferentes tipos de usuarios, y proponer estrategias de mejora.

### Parámetros del Modelo

| Tipo de Usuario | Tiempo de Servicio (Exp.) | Media de Llegada (Exp.) |
|-----------------|:-------------------------:|:-----------------------:|
| Rápido          | 1 minuto                  | 3 minutos               |
| Normal          | 3 minutos                 | 3 minutos               |
| Lento           | 4 minutos                 | 5 minutos               |
| Muy Lento       | 6 minutos                 | 7 minutos               |

---

## Requisitos del Sistema

- **Python** 3.8 o superior
- **Librerías de Python:**
  - `simpy` – Motor de simulación de eventos discretos
  - `numpy` – Cálculos numéricos y estadísticos
  - `matplotlib` – Generación de gráficas
  - `scipy` – Funciones estadísticas avanzadas

---

## Instalación

1. **Clonar o descargar** el repositorio:
   ```bash
   git clone https://github.com/SantiJaramilloDev/Actividad-didactica-2-M4.git
   cd Actividad-didactica-2-M4
   ```

2. **Instalar las dependencias** necesarias:
   ```bash
   pip install simpy numpy matplotlib scipy
   ```

---

## Ejecución del Proyecto

Para ejecutar la simulación completa:

```bash
python simulacion_problema_parqueadero.py
```

El programa ejecutará automáticamente todos los análisis y generará las gráficas en la carpeta `graficas/`.

> **Nota:** La ejecución puede tomar algunos segundos debido a las múltiples réplicas de simulación (30 réplicas por escenario).

---

## Estructura del Proyecto

```
Actividad didáctica 2-M4/
│
├── simulacion_problema_parqueadero.py   # Script principal de simulación
├── README.md                            # Este archivo
│
└── graficas/                            # Gráficas generadas (auto-creada)
    ├── punto_a_analisis_estadistico.png
    ├── punto_b_tendencia_central.png
    ├── punto_c_escenarios.png
    ├── punto_d_verificacion.png
    ├── punto_e_transitorio.png
    └── evolucion_colas.png
```

---

## Descripción de los Análisis

### Punto A – Análisis Estadístico del Modelo

Calcula las estadísticas necesarias para identificar el cajero con **menor y mayor tiempo promedio de atención**:

- **Wq**: Tiempo promedio de espera en cola (minutos)
- **Ws**: Tiempo promedio en el sistema (espera + servicio)
- **E[S]**: Tiempo promedio de servicio
- **ρ (rho)**: Utilización del servidor (proporción del tiempo ocupado)
- **Lq**: Longitud promedio de la cola
- Intervalos de confianza al 95%

**Gráfica:** `punto_a_analisis_estadistico.png`

### Punto B – Medidas de Tendencia Central

Calcula el **promedio de usuarios de cada tipo** en la totalidad de cajeros:

- Media, mediana, desviación estándar, mínimo y máximo por tipo de usuario
- Porcentaje de cada tipo respecto al total
- Distribución por cajero

**Gráfica:** `punto_b_tendencia_central.png` (barras, gráfico circular y boxplot)

### Punto C – Análisis de Escenarios

Define una estrategia para **mejorar la situación actual** del centro comercial comparando tres escenarios:

| Escenario   | Cajeros | Descripción                     |
|-------------|:-------:|--------------------------------|
| Base        | 3       | Configuración actual            |
| Alternativo | 4       | Un cajero adicional             |
| Óptimo      | 5       | Dos cajeros adicionales         |

Se comparan las métricas Wq, Ws, ρ y Lq, y se emite una **recomendación fundamentada**.

**Gráfica:** `punto_c_escenarios.png`

### Punto D – Verificación, Calibración y Validación

- **Verificación**: Comparación de valores simulados vs. fórmulas teóricas M/M/1
- **Calibración**: Los parámetros provienen directamente del enunciado del problema
- **Validación**: Análisis de convergencia del promedio acumulado conforme aumentan las réplicas

**Gráfica:** `punto_d_verificacion.png` (convergencia e histograma)

### Punto E – Eliminación del Estado Transitorio

- Detección del período transitorio mediante **análisis de medias por bloque**
- Eliminación de las observaciones iniciales (warm-up)
- Comparación de estadísticas **antes y después** de eliminar el transitorio
- Media móvil para visualizar la estabilización

**Gráfica:** `punto_e_transitorio.png` (series temporales, bloques e histogramas)

### Gráfica Adicional – Evolución de Colas

Muestra la evolución temporal de la longitud de cola en cada cajero durante una jornada completa de 8 horas.

**Gráfica:** `evolucion_colas.png`

---

## Metodología de Simulación

1. **Modelo**: Cada cajero es una cola M/M/1 independiente
2. **Llegadas**: Procesos de Poisson independientes por tipo de usuario
3. **Servicio**: Distribución exponencial con media según el tipo de usuario
4. **Asignación**: Los usuarios se asignan aleatoriamente a un cajero (preserva la propiedad de Poisson)
5. **Réplicas**: 30 corridas independientes para significancia estadística
6. **Tiempo**: 480 minutos (8 horas) por réplica

---

## Resultados Principales

- Con **3 cajeros**, la utilización es extremadamente alta (ρ ≈ 0.90+), generando colas y tiempos de espera excesivos.
- Con **4 cajeros**, el sistema se estabiliza (ρ ≈ 0.72) con mejoras significativas.
- Con **5 cajeros**, la carga es moderada (ρ ≈ 0.59) y el servicio es fluido.
- **Recomendación**: Instalar al menos 4 cajeros; idealmente 5 para garantizar tiempos de espera aceptables.

---

## Conclusiones

1. El análisis demuestra que **3 cajeros son insuficientes** para manejar la demanda actual del centro comercial.
2. La utilización cercana al 100% provoca tiempos de espera que crecen exponencialmente.
3. Agregar **1 o 2 cajeros adicionales** reduce drásticamente los tiempos de espera y la longitud de las colas.
4. El modelo M/M/1 proporciona una aproximación razonable del sistema real, validada mediante comparación con valores teóricos.
5. La eliminación del estado transitorio mejora la precisión de las estimaciones del estado estable.

---

## Tecnologías Utilizadas

- **Python 3.11**
- **SimPy** – Simulación de eventos discretos
- **NumPy** – Cálculos numéricos
- **Matplotlib** – Visualización de datos
- **SciPy** – Análisis estadístico

---

## Autor

Brayan Santiago Jaramillo Amézquita
Actividad Didáctica 2-M4 – Simulación  
IU Digital de Antioquia  
06 de Junio de 2026
