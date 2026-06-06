"""
=============================================================================
  Simulación del Problema de Parqueaderos – Centro Comercial Supercentro
  Modelo de Colas M/M/1
=============================================================================

  Actividad Didáctica 2-M4 · Simulación · IU Digital

  Descripción
  -----------
  Simulación de un sistema de pago de parqueaderos con múltiples cajeros
  independientes modelados como colas M/M/1.  Se resuelven los siguientes
  puntos:

      A. Análisis estadístico: cajero con menor y mayor tiempo promedio.
      B. Medidas de tendencia central: promedio de usuarios por tipo.
      C. Análisis de escenarios: 3, 4 y 5 cajeros.
      D. Verificación, calibración y validación del modelo.
      E. Eliminación del estado transitorio.

  Librerías requeridas
  --------------------
  simpy, numpy, matplotlib, scipy
"""

# =====================================================================
#  IMPORTS
# =====================================================================
import simpy
import numpy as np
import matplotlib
matplotlib.use("Agg")                 # Backend no interactivo para guardar PNG
import matplotlib.pyplot as plt
from scipy import stats as sp_stats
from collections import defaultdict
import random
import os
import warnings
import sys
import io

# Forzar codificación UTF-8 en la consola de Windows
if sys.platform == "win32":
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8",
                                  errors="replace")
    sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding="utf-8",
                                  errors="replace")

warnings.filterwarnings("ignore")

# =====================================================================
#  CONFIGURACIÓN GLOBAL
# =====================================================================
RANDOM_SEED      = 42
SIMULATION_TIME  = 480          # minutos (8 horas de operación)
NUM_REPLICAS     = 30           # número de corridas independientes
NUM_CAJEROS_BASE = 3            # cantidad inicial de cajeros por salida
OUTPUT_DIR       = "graficas"   # directorio para gráficas PNG

# Tipos de usuario con sus parámetros
# ─ tiempo_servicio : media de la distribución exponencial de servicio (min)
# ─ media_llegada   : media de la distribución exponencial entre llegadas (min)
TIPOS_USUARIO = {
    "Rápido":    {"tiempo_servicio": 1, "media_llegada": 3},
    "Normal":    {"tiempo_servicio": 3, "media_llegada": 3},
    "Lento":     {"tiempo_servicio": 4, "media_llegada": 5},
    "Muy Lento": {"tiempo_servicio": 6, "media_llegada": 7},
}

# Estilo de las gráficas
plt.rcParams.update({
    "figure.figsize":  (14, 9),
    "figure.dpi":      150,
    "axes.grid":       True,
    "grid.alpha":      0.30,
    "font.size":       11,
})

COLORES_CAJERO = ["#2196F3", "#4CAF50", "#FF9800", "#E91E63", "#9C27B0"]
COLORES_TIPO   = {
    "Rápido":    "#4CAF50",
    "Normal":    "#2196F3",
    "Lento":     "#FF9800",
    "Muy Lento": "#E91E63",
}


# =====================================================================
#  RECOLECTOR DE ESTADÍSTICAS POR CAJERO
# =====================================================================
class EstadisticasCajero:
    """Almacena las métricas observadas en un cajero durante una réplica."""

    def __init__(self):
        self.tiempos_espera   = []   # Wq por usuario
        self.tiempos_servicio = []   # S  por usuario
        self.tiempos_sistema  = []   # Ws por usuario
        self.conteo_tipos     = defaultdict(int)
        self.total_usuarios   = 0
        # Series temporales para análisis de transitorio
        self.serie_espera     = []   # [(t_llegada, Wq), ...]
        self.serie_sistema    = []   # [(t_llegada, Ws), ...]
        self.serie_cola       = []   # [(t, longitud_cola), ...]

    def registrar(self, tipo, t_llegada, t_espera, t_servicio, t_sistema):
        """Registra la atención completa de un usuario."""
        self.tiempos_espera.append(t_espera)
        self.tiempos_servicio.append(t_servicio)
        self.tiempos_sistema.append(t_sistema)
        self.conteo_tipos[tipo] += 1
        self.total_usuarios += 1
        self.serie_espera.append((t_llegada, t_espera))
        self.serie_sistema.append((t_llegada, t_sistema))


# =====================================================================
#  PROCESOS DE SIMULACIÓN (SimPy)
# =====================================================================
def proceso_llegada_tipo(env, tipo_usuario, cajeros, estadisticas, num_cajeros):
    """
    Genera llegadas Poisson independientes para *un* tipo de usuario.
    Cada llegada se asigna aleatoriamente a un cajero (thinning uniforme
    preserva la propiedad de Poisson en cada cajero).
    """
    params = TIPOS_USUARIO[tipo_usuario]

    while True:
        yield env.timeout(np.random.exponential(params["media_llegada"]))
        cajero_idx = random.randint(0, num_cajeros - 1)
        env.process(
            atender_usuario(env, tipo_usuario, cajeros[cajero_idx],
                            cajero_idx, estadisticas[cajero_idx], params)
        )


def atender_usuario(env, tipo, cajero, cajero_idx, stats, params):
    """Modela la estancia de un usuario en la cola + servicio del cajero."""
    t_llegada = env.now

    with cajero.request() as req:
        yield req                       # espera en cola
        t_espera = env.now - t_llegada

        t_servicio = np.random.exponential(params["tiempo_servicio"])
        yield env.timeout(t_servicio)   # servicio

        t_sistema = env.now - t_llegada
        stats.registrar(tipo, t_llegada, t_espera, t_servicio, t_sistema)


def monitorear_colas(env, cajeros, estadisticas, intervalo=1.0):
    """Muestrea la longitud de cola de cada cajero periódicamente."""
    while True:
        for i, cajero in enumerate(cajeros):
            estadisticas[i].serie_cola.append((env.now, len(cajero.queue)))
        yield env.timeout(intervalo)


# =====================================================================
#  EJECUCIÓN DE SIMULACIÓN
# =====================================================================
def ejecutar_simulacion(num_cajeros=NUM_CAJEROS_BASE,
                        sim_time=SIMULATION_TIME, seed=None):
    """Ejecuta **una** réplica de la simulación y devuelve estadísticas."""
    if seed is not None:
        np.random.seed(seed)
        random.seed(seed)

    env = simpy.Environment()
    cajeros      = [simpy.Resource(env, capacity=1) for _ in range(num_cajeros)]
    estadisticas = [EstadisticasCajero() for _ in range(num_cajeros)]

    for tipo in TIPOS_USUARIO:
        env.process(proceso_llegada_tipo(env, tipo, cajeros,
                                         estadisticas, num_cajeros))
    env.process(monitorear_colas(env, cajeros, estadisticas))
    env.run(until=sim_time)

    return estadisticas


def ejecutar_replicas(num_replicas=NUM_REPLICAS,
                      num_cajeros=NUM_CAJEROS_BASE, verbose=True):
    """Ejecuta *n* réplicas independientes."""
    todas = []
    for i in range(num_replicas):
        stats = ejecutar_simulacion(num_cajeros=num_cajeros,
                                    seed=RANDOM_SEED + i)
        todas.append(stats)
        if verbose:
            print(f"  Réplica {i+1:>2}/{num_replicas} completada")
    return todas


# =====================================================================
#  VALORES TEÓRICOS M/M/1
# =====================================================================
def calcular_valores_teoricos(num_cajeros):
    """
    Calcula los valores teóricos del modelo M/M/1 (aproximación).

    Se combinan las tasas de llegada de todos los tipos y se asume una
    distribución uniforme de usuarios hacia los cajeros.
    """
    # Tasa total de llegada al sistema (superposición Poisson)
    lambda_total = sum(1.0 / TIPOS_USUARIO[t]["media_llegada"]
                       for t in TIPOS_USUARIO)
    lambda_c = lambda_total / num_cajeros     # tasa por cajero

    # Proporciones naturales (derivadas de las tasas)
    proporciones = {}
    for t in TIPOS_USUARIO:
        proporciones[t] = (1.0 / TIPOS_USUARIO[t]["media_llegada"]) / lambda_total

    # Tiempo de servicio esperado ponderado
    E_S = sum(proporciones[t] * TIPOS_USUARIO[t]["tiempo_servicio"]
              for t in TIPOS_USUARIO)
    mu  = 1.0 / E_S
    rho = lambda_c / mu

    if rho < 1:
        Wq = rho / (mu * (1 - rho))
        Ws = Wq + E_S
        Lq = lambda_c * Wq
        Ls = lambda_c * Ws
    else:
        Wq = Ws = Lq = Ls = float("inf")

    return {
        "lambda_total": lambda_total,
        "lambda_c":     lambda_c,
        "mu":           mu,
        "rho":          rho,
        "E_S":          E_S,
        "Wq":           Wq,
        "Ws":           Ws,
        "Lq":           Lq,
        "Ls":           Ls,
        "proporciones": proporciones,
    }


# =====================================================================
#  PUNTO A – ANÁLISIS ESTADÍSTICO DEL MODELO
# =====================================================================
def punto_a_analisis_estadistico(replicas, num_cajeros):
    """
    Calcula las estadísticas necesarias para identificar el cajero con
    menor y mayor tiempo promedio de atención.
    """
    titulo = "PUNTO A: ANÁLISIS ESTADÍSTICO DEL MODELO"
    print(f"\n{'='*70}\n{titulo}\n{'='*70}")

    # Agrupar métricas por cajero (promedios de cada réplica)
    met = defaultdict(lambda: {"espera": [], "servicio": [], "sistema": [],
                               "utilizacion": [], "cola_prom": [],
                               "n_usuarios": []})

    for rep in replicas:
        for cid in range(num_cajeros):
            s = rep[cid]
            if not s.tiempos_espera:
                continue
            met[cid]["espera"].append(np.mean(s.tiempos_espera))
            met[cid]["servicio"].append(np.mean(s.tiempos_servicio))
            met[cid]["sistema"].append(np.mean(s.tiempos_sistema))
            met[cid]["utilizacion"].append(
                sum(s.tiempos_servicio) / SIMULATION_TIME)
            if s.serie_cola:
                met[cid]["cola_prom"].append(
                    np.mean([v for _, v in s.serie_cola]))
            met[cid]["n_usuarios"].append(s.total_usuarios)

    # Tabla resumen
    print(f"\nResultados promedio sobre {NUM_REPLICAS} réplicas "
          f"({SIMULATION_TIME} min cada una) — {num_cajeros} cajeros\n")
    hdr = (f"{'Cajero':<10} {'Wq(min)':<12} {'Ws(min)':<12} "
           f"{'E[S](min)':<12} {'ρ':<10} {'Lq':<10} {'#Usuarios':<10}")
    print(hdr)
    print("-" * len(hdr))

    resumen = {}
    for cid in range(num_cajeros):
        m = met[cid]
        r = {
            "wq":  np.mean(m["espera"]),
            "ws":  np.mean(m["sistema"]),
            "es":  np.mean(m["servicio"]),
            "rho": np.mean(m["utilizacion"]),
            "lq":  np.mean(m["cola_prom"]) if m["cola_prom"] else 0,
            "n":   np.mean(m["n_usuarios"]),
        }
        resumen[cid] = r
        print(f"Cajero {cid+1:<4} {r['wq']:<12.4f} {r['ws']:<12.4f} "
              f"{r['es']:<12.4f} {r['rho']:<10.4f} {r['lq']:<10.4f} "
              f"{r['n']:<10.1f}")

    # Cajero mejor / peor
    cmin = min(resumen, key=lambda x: resumen[x]["ws"])
    cmax = max(resumen, key=lambda x: resumen[x]["ws"])
    print(f"\n Cajero con MENOR tiempo promedio en sistema: "
          f"Cajero {cmin+1} (Ws = {resumen[cmin]['ws']:.4f} min)")
    print(f" Cajero con MAYOR tiempo promedio en sistema: "
          f"Cajero {cmax+1} (Ws = {resumen[cmax]['ws']:.4f} min)")

    # Intervalos de confianza al 95 %
    print(f"\nIntervalos de confianza al 95 % para Ws:")
    for cid in range(num_cajeros):
        d  = met[cid]["sistema"]
        mn = np.mean(d)
        se = sp_stats.sem(d) if len(d) > 1 else 0
        if se > 0:
            ci = sp_stats.t.interval(0.95, len(d)-1, loc=mn, scale=se)
            print(f"  Cajero {cid+1}: [{ci[0]:.4f} , {ci[1]:.4f}] min")
        else:
            print(f"  Cajero {cid+1}: {mn:.4f} min (sin variabilidad)")

    # ── Gráfica ──
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Punto A – Análisis Estadístico por Cajero",
                 fontsize=16, fontweight="bold")
    labels = [f"Cajero {i+1}" for i in range(num_cajeros)]

    def _bar(ax, key, title, ylabel):
        vals = [np.mean(met[i][key]) for i in range(num_cajeros)]
        errs = [sp_stats.sem(met[i][key]) * 1.96
                if len(met[i][key]) > 1 else 0 for i in range(num_cajeros)]
        bars = ax.bar(labels, vals, color=COLORES_CAJERO[:num_cajeros],
                      yerr=errs, capsize=5, edgecolor="black")
        ax.set_title(title)
        ax.set_ylabel(ylabel)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width()/2, b.get_height(),
                    f"{v:.2f}", ha="center", va="bottom", fontweight="bold",
                    fontsize=9)

    _bar(axes[0, 0], "espera",  "Tiempo Promedio de Espera en Cola (Wq)",
         "Tiempo (min)")
    _bar(axes[0, 1], "sistema", "Tiempo Promedio en Sistema (Ws)",
         "Tiempo (min)")

    # Utilización
    ax = axes[1, 0]
    vals = [np.mean(met[i]["utilizacion"]) for i in range(num_cajeros)]
    bars = ax.bar(labels, vals, color=COLORES_CAJERO[:num_cajeros],
                  edgecolor="black")
    ax.set_title("Utilización del Servidor (ρ)")
    ax.set_ylabel("ρ")
    ax.set_ylim(0, max(1.2, max(vals) * 1.1))
    ax.axhline(y=1.0, color="red", ls="--", lw=2, label="Capacidad máxima")
    ax.legend(fontsize=9)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.01,
                f"{v:.4f}", ha="center", va="bottom", fontweight="bold",
                fontsize=9)

    _bar(axes[1, 1], "cola_prom", "Longitud Promedio de Cola (Lq)",
         "Usuarios")

    plt.tight_layout()
    ruta = os.path.join(OUTPUT_DIR, "punto_a_analisis_estadistico.png")
    plt.savefig(ruta, bbox_inches="tight")
    plt.close()
    print(f"\n Gráfica guardada: {ruta}")

    return met, resumen


# =====================================================================
#  PUNTO B – MEDIDAS DE TENDENCIA CENTRAL
# =====================================================================
def punto_b_medidas_tendencia(replicas, num_cajeros):
    """
    Calcula el promedio de usuarios de cada tipo en la totalidad de cajeros.
    Incluye media, mediana, desviación estándar, mínimo, máximo y porcentaje.
    """
    titulo = "PUNTO B: MEDIDAS DE TENDENCIA CENTRAL DEL MODELO"
    print(f"\n{'='*70}\n{titulo}\n{'='*70}")

    conteos_tipo   = defaultdict(list)          # totales por réplica
    conteos_cajero = defaultdict(lambda: defaultdict(list))

    for rep in replicas:
        total_rep = defaultdict(int)
        for cid in range(num_cajeros):
            for tipo in TIPOS_USUARIO:
                c = rep[cid].conteo_tipos.get(tipo, 0)
                total_rep[tipo] += c
                conteos_cajero[tipo][cid].append(c)
        for tipo in TIPOS_USUARIO:
            conteos_tipo[tipo].append(total_rep[tipo])

    total_general = sum(np.mean(conteos_tipo[t]) for t in TIPOS_USUARIO)

    print(f"\nPromedio de usuarios por tipo (sobre {NUM_REPLICAS} réplicas):\n")
    hdr = (f"{'Tipo':<15} {'Media':<10} {'Mediana':<10} "
           f"{'Desv.Std':<10} {'Mín':<8} {'Máx':<8} {'%Total':<8}")
    print(hdr)
    print("-" * len(hdr))

    stats_t = {}
    for tipo in TIPOS_USUARIO:
        d = np.array(conteos_tipo[tipo])
        s = {
            "media":   np.mean(d),
            "mediana": np.median(d),
            "std":     np.std(d, ddof=1),
            "min":     int(np.min(d)),
            "max":     int(np.max(d)),
            "pct":     np.mean(d) / total_general * 100 if total_general else 0,
        }
        stats_t[tipo] = s
        print(f"{tipo:<15} {s['media']:<10.2f} {s['mediana']:<10.1f} "
              f"{s['std']:<10.2f} {s['min']:<8} {s['max']:<8} "
              f"{s['pct']:<8.1f}%")

    print(f"\n{'TOTAL':<15} {total_general:<10.2f}")

    # Distribución por cajero
    print(f"\nDistribución promedio por cajero:")
    hdr2 = f"{'Tipo':<15} " + " ".join(
        f"{'Cajero '+str(i+1):<12}" for i in range(num_cajeros))
    print(hdr2)
    print("-" * len(hdr2))
    for tipo in TIPOS_USUARIO:
        vals = " ".join(
            f"{np.mean(conteos_cajero[tipo][i]):<12.1f}"
            for i in range(num_cajeros))
        print(f"{tipo:<15} {vals}")

    # ── Gráfica ──
    fig, axes = plt.subplots(1, 3, figsize=(18, 6))
    fig.suptitle("Punto B – Medidas de Tendencia Central",
                 fontsize=16, fontweight="bold")
    tipos = list(TIPOS_USUARIO.keys())
    cols  = [COLORES_TIPO[t] for t in tipos]

    # Barras
    ax = axes[0]
    medias = [stats_t[t]["media"] for t in tipos]
    stds   = [stats_t[t]["std"]   for t in tipos]
    bars = ax.bar(tipos, medias, color=cols, yerr=stds, capsize=5,
                  edgecolor="black")
    ax.set_title("Promedio de Usuarios por Tipo")
    ax.set_ylabel("Número de usuarios")
    for b, v in zip(bars, medias):
        ax.text(b.get_x() + b.get_width()/2, b.get_height() + 1,
                f"{v:.1f}", ha="center", va="bottom", fontweight="bold")

    # Pastel
    ax = axes[1]
    pcts = [stats_t[t]["pct"] for t in tipos]
    wedges, texts, autos = ax.pie(
        pcts, labels=tipos, autopct="%1.1f%%", colors=cols, startangle=90,
        textprops={"fontsize": 11})
    for a in autos:
        a.set_fontweight("bold")
    ax.set_title("Proporción de Usuarios por Tipo")

    # Boxplot
    ax = axes[2]
    data_box = [conteos_tipo[t] for t in tipos]
    bp = ax.boxplot(data_box, labels=tipos, patch_artist=True)
    for patch, c in zip(bp["boxes"], cols):
        patch.set_facecolor(c)
        patch.set_alpha(0.7)
    ax.set_title("Distribución de Usuarios por Tipo (réplicas)")
    ax.set_ylabel("Número de usuarios")

    plt.tight_layout()
    ruta = os.path.join(OUTPUT_DIR, "punto_b_tendencia_central.png")
    plt.savefig(ruta, bbox_inches="tight")
    plt.close()
    print(f"\n Gráfica guardada: {ruta}")

    return stats_t


# =====================================================================
#  PUNTO C – ANÁLISIS DE ESCENARIOS
# =====================================================================
def punto_c_analisis_escenarios():
    """
    Compara el desempeño del sistema con 3, 4 y 5 cajeros para determinar
    si la cantidad actual es suficiente o se deben instalar más.
    """
    titulo = "PUNTO C: ANÁLISIS DE ESCENARIOS"
    print(f"\n{'='*70}\n{titulo}\n{'='*70}")

    escenarios = [3, 4, 5]
    resultados = {}

    for nc in escenarios:
        print(f"\n─── Simulando escenario con {nc} cajeros ───")
        reps = ejecutar_replicas(NUM_REPLICAS, nc, verbose=True)

        wq_l, ws_l, rho_l, lq_l = [], [], [], []
        for rep in reps:
            _wq, _ws, _rho, _lq = [], [], [], []
            for cid in range(nc):
                s = rep[cid]
                if s.tiempos_espera:
                    _wq.append(np.mean(s.tiempos_espera))
                    _ws.append(np.mean(s.tiempos_sistema))
                    _rho.append(sum(s.tiempos_servicio) / SIMULATION_TIME)
                if s.serie_cola:
                    _lq.append(np.mean([v for _, v in s.serie_cola]))
            if _wq:
                wq_l.append(np.mean(_wq))
                ws_l.append(np.mean(_ws))
                rho_l.append(np.mean(_rho))
            if _lq:
                lq_l.append(np.mean(_lq))

        teo = calcular_valores_teoricos(nc)
        resultados[nc] = {
            "wq": np.mean(wq_l),   "wq_std": np.std(wq_l),
            "ws": np.mean(ws_l),   "ws_std": np.std(ws_l),
            "rho": np.mean(rho_l), "rho_std": np.std(rho_l),
            "lq": np.mean(lq_l) if lq_l else 0,
            "teo": teo,
        }

    # Tabla comparativa
    print(f"\n{'='*70}\nCOMPARACIÓN DE ESCENARIOS\n{'='*70}\n")
    hdr = f"{'Métrica':<28} " + " ".join(f"{n} cajeros{'':>8}" for n in escenarios)
    print(hdr)
    print("-" * len(hdr))
    for label, key in [("Wq  (min)", "wq"), ("Ws  (min)", "ws"),
                       ("ρ   (utilización)", "rho"),
                       ("Lq  (cola promedio)", "lq")]:
        vals = " ".join(f"{resultados[n][key]:>15.4f}" for n in escenarios)
        print(f"{label:<28} {vals}")

    print(f"\n{'Valores teóricos M/M/1:':<28}")
    for label, key in [("ρ teórico", "rho"), ("Wq teórico", "Wq"),
                       ("Ws teórico", "Ws")]:
        vals = []
        for n in escenarios:
            v = resultados[n]["teo"][key]
            vals.append(f"{v:>15.4f}" if v != float("inf") else f"{'∞':>15}")
        print(f"{label:<28} " + " ".join(vals))

    # Recomendación
    r3, r4, r5 = (resultados[n]["rho"] for n in escenarios)
    print(f"""
{'='*70}
ANÁLISIS Y RECOMENDACIÓN
{'='*70}

Con 3 cajeros:
  · Utilización (ρ) ≈ {r3:.4f}  →  {'️  SISTEMA SATURADO / INESTABLE' if r3 > 0.95 else 'Sistema estable'}
  · Las colas crecen de forma continua; tiempos de espera excesivos.
  · 3 cajeros NO son suficientes para la demanda actual.

Con 4 cajeros:
  · Utilización (ρ) ≈ {r4:.4f}  →  {'Alta carga, pero estable' if 0.80 < r4 < 0.95 else 'Sistema aceptable'}
  · Mejora significativa en tiempos de espera.
  · Opción viable si el presupuesto es limitado.

Con 5 cajeros:
  · Utilización (ρ) ≈ {r5:.4f}  →  Carga moderada, servicio fluido.
  · Tiempos de espera razonables y buena experiencia de usuario.

RECOMENDACIÓN:
   Instalar al menos 4 cajeros; idealmente 5 para garantizar
   tiempos de espera aceptables y evitar la saturación del sistema.
""")

    # ── Gráfica ──
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Punto C – Comparación de Escenarios",
                 fontsize=16, fontweight="bold")
    ce = ["#E91E63", "#FF9800", "#4CAF50"]
    le = [f"{n} cajeros" for n in escenarios]

    def _barcmp(ax, key, title, ylabel):
        vals = [resultados[n][key] for n in escenarios]
        bars = ax.bar(le, vals, color=ce, edgecolor="black")
        ax.set_title(title); ax.set_ylabel(ylabel)
        for b, v in zip(bars, vals):
            ax.text(b.get_x() + b.get_width()/2, b.get_height(),
                    f"{v:.2f}", ha="center", va="bottom",
                    fontweight="bold", fontsize=9)

    _barcmp(axes[0, 0], "wq", "Tiempo de Espera en Cola (Wq)", "min")
    _barcmp(axes[1, 0], "ws", "Tiempo en Sistema (Ws)", "min")
    _barcmp(axes[1, 1], "lq", "Longitud Promedio de Cola (Lq)", "Usuarios")

    # Utilización con líneas de referencia
    ax = axes[0, 1]
    vals = [resultados[n]["rho"] for n in escenarios]
    bars = ax.bar(le, vals, color=ce, edgecolor="black")
    ax.set_title("Utilización del Servidor (ρ)"); ax.set_ylabel("ρ")
    ax.set_ylim(0, max(1.3, max(vals) * 1.1))
    ax.axhline(1.0, color="red",    ls="--", lw=2, label="Capacidad máxima (1.0)")
    ax.axhline(0.8, color="orange", ls="--", lw=1, label="Umbral recomendado (0.8)")
    ax.legend(fontsize=8)
    for b, v in zip(bars, vals):
        ax.text(b.get_x() + b.get_width()/2, b.get_height() + 0.02,
                f"{v:.4f}", ha="center", va="bottom", fontweight="bold",
                fontsize=9)

    plt.tight_layout()
    ruta = os.path.join(OUTPUT_DIR, "punto_c_escenarios.png")
    plt.savefig(ruta, bbox_inches="tight")
    plt.close()
    print(f"Gráfica guardada: {ruta}")

    return resultados


# =====================================================================
#  PUNTO D – VERIFICACIÓN, CALIBRACIÓN Y VALIDACIÓN
# =====================================================================
def punto_d_verificacion(replicas, num_cajeros):
    """
    Compara valores simulados con los teóricos M/M/1, muestra la
    convergencia acumulada y la distribución de métricas entre réplicas.
    """
    titulo = "PUNTO D: VERIFICACIÓN, CALIBRACIÓN Y VALIDACIÓN"
    print(f"\n{'='*70}\n{titulo}\n{'='*70}")

    teo = calcular_valores_teoricos(num_cajeros)

    # Extraer métricas promedio por réplica
    wq_sim, ws_sim, rho_sim = [], [], []
    for rep in replicas:
        _wq, _ws, _rho = [], [], []
        for cid in range(num_cajeros):
            s = rep[cid]
            if s.tiempos_espera:
                _wq.append(np.mean(s.tiempos_espera))
                _ws.append(np.mean(s.tiempos_sistema))
                _rho.append(sum(s.tiempos_servicio) / SIMULATION_TIME)
        if _wq:
            wq_sim.append(np.mean(_wq))
            ws_sim.append(np.mean(_ws))
            rho_sim.append(np.mean(_rho))

    # ─── VERIFICACIÓN ───
    print("\n── VERIFICACIÓN ──")
    print("Comparación valores simulados vs. teóricos M/M/1:\n")
    hdr = f"{'Métrica':<28} {'Simulado':<15} {'Teórico':<15} {'Error %':<12}"
    print(hdr); print("-" * len(hdr))
    for nombre, sim, t in [
        ("ρ (utilización)",     np.mean(rho_sim), teo["rho"]),
        ("Wq (espera en cola)", np.mean(wq_sim),  teo["Wq"]),
        ("Ws (tiempo sistema)", np.mean(ws_sim),   teo["Ws"]),
    ]:
        if t not in (float("inf"), 0):
            err = abs(sim - t) / abs(t) * 100
            print(f"{nombre:<28} {sim:<15.4f} {t:<15.4f} {err:<12.2f}%")
        else:
            print(f"{nombre:<28} {sim:<15.4f} {'∞':<15} {'N/A':<12}")

    # ─── CALIBRACIÓN ───
    print("\n── CALIBRACIÓN ──")
    print("Los parámetros del modelo provienen directamente del enunciado:")
    print("  · Tasas de llegada por tipo → 'Media de llegada'")
    print("  · Tiempos de servicio → 'Exponencial de uso del servicio'")
    print("  · Asignación a cajeros: aleatoria uniforme (preserva M/M/1)")

    # ─── VALIDACIÓN ───
    print("\n── VALIDACIÓN ──")
    print("Se verifica la convergencia del promedio acumulado de cada métrica")
    print("a medida que aumenta el número de réplicas.")

    # ── Gráfica ──
    fig, axes = plt.subplots(2, 2, figsize=(14, 10))
    fig.suptitle("Punto D – Verificación, Calibración y Validación",
                 fontsize=16, fontweight="bold")

    # Convergencia Wq
    ax = axes[0, 0]
    cum = np.cumsum(wq_sim) / np.arange(1, len(wq_sim)+1)
    ax.plot(range(1, len(cum)+1), cum, "b-o", ms=3, label="Simulado")
    if teo["Wq"] != float("inf"):
        ax.axhline(teo["Wq"], color="red", ls="--",
                   label=f"Teórico: {teo['Wq']:.2f}")
    ax.set_title("Convergencia de Wq"); ax.set_xlabel("Réplicas")
    ax.set_ylabel("Wq promedio (min)"); ax.legend()

    # Convergencia ρ
    ax = axes[0, 1]
    cum = np.cumsum(rho_sim) / np.arange(1, len(rho_sim)+1)
    ax.plot(range(1, len(cum)+1), cum, "g-o", ms=3, label="Simulado")
    ax.axhline(teo["rho"], color="red", ls="--",
               label=f"Teórico: {teo['rho']:.4f}")
    ax.set_title("Convergencia de ρ"); ax.set_xlabel("Réplicas")
    ax.set_ylabel("ρ promedio"); ax.legend()

    # Convergencia Ws
    ax = axes[1, 0]
    cum = np.cumsum(ws_sim) / np.arange(1, len(ws_sim)+1)
    ax.plot(range(1, len(cum)+1), cum, "m-o", ms=3, label="Simulado")
    if teo["Ws"] != float("inf"):
        ax.axhline(teo["Ws"], color="red", ls="--",
                   label=f"Teórico: {teo['Ws']:.2f}")
    ax.set_title("Convergencia de Ws"); ax.set_xlabel("Réplicas")
    ax.set_ylabel("Ws promedio (min)"); ax.legend()

    # Histograma de Wq
    ax = axes[1, 1]
    ax.hist(wq_sim, bins=15, color="#2196F3", edgecolor="black",
            alpha=0.7, density=True)
    ax.axvline(np.mean(wq_sim), color="red", ls="--", lw=2,
               label=f"Media: {np.mean(wq_sim):.2f}")
    ax.set_title("Distribución de Wq entre réplicas")
    ax.set_xlabel("Wq (min)"); ax.set_ylabel("Densidad"); ax.legend()

    plt.tight_layout()
    ruta = os.path.join(OUTPUT_DIR, "punto_d_verificacion.png")
    plt.savefig(ruta, bbox_inches="tight")
    plt.close()
    print(f"\nGráfica guardada: {ruta}")

    return teo


# =====================================================================
#  PUNTO E – ELIMINACIÓN DEL ESTADO TRANSITORIO
# =====================================================================
def punto_e_estado_transitorio(replicas, num_cajeros):
    """
    Identifica y elimina el período transitorio mediante análisis de
    medias por bloque.  Grafica los valores promedio seleccionados
    mostrando un *antes* y un *después*.
    """
    titulo = "PUNTO E: ELIMINACIÓN DEL ESTADO TRANSITORIO"
    print(f"\n{'='*70}\n{titulo}\n{'='*70}")

    # Combinar series de la primera réplica
    rep = replicas[0]
    all_espera  = []
    all_sistema = []
    for cid in range(num_cajeros):
        all_espera.extend(rep[cid].serie_espera)
        all_sistema.extend(rep[cid].serie_sistema)

    all_espera.sort(key=lambda x: x[0])
    all_sistema.sort(key=lambda x: x[0])

    if not all_espera:
        print("  Sin datos suficientes para analizar el transitorio.")
        return

    t_arr  = np.array([t for t, _ in all_espera])
    v_wq   = np.array([v for _, v in all_espera])
    v_ws   = np.array([v for _, v in all_sistema])
    n_obs  = len(v_wq)

    # Media móvil
    window = max(20, n_obs // 20)
    mm_wq  = np.convolve(v_wq, np.ones(window)/window, mode="valid")

    # Bloques para detectar transitorio
    n_bloques  = 20
    tam_bloque = n_obs // n_bloques
    medias_b   = [np.mean(v_wq[i*tam_bloque:(i+1)*tam_bloque])
                  for i in range(n_bloques)]

    # Detectar fin del transitorio: cuando las medias por bloque se estabilizan
    cambios = []
    for i in range(1, len(medias_b)):
        denom = abs(medias_b[i-1]) if medias_b[i-1] != 0 else 1e-9
        cambios.append(abs(medias_b[i] - medias_b[i-1]) / denom)

    corte_b = 0
    for i in range(len(cambios)):
        ventana = cambios[i:min(i+3, len(cambios))]
        if all(c < 0.20 for c in ventana):
            corte_b = i + 1
            break

    punto_corte = corte_b * tam_bloque
    if punto_corte == 0:
        punto_corte = n_obs // 10        # default: 10 %

    # Estadísticas antes / después
    media_wq_antes   = np.mean(v_wq)
    std_wq_antes     = np.std(v_wq)
    media_wq_despues = np.mean(v_wq[punto_corte:])
    std_wq_despues   = np.std(v_wq[punto_corte:])
    media_ws_antes   = np.mean(v_ws)
    media_ws_despues = np.mean(v_ws[punto_corte:])

    print(f"\nTotal observaciones : {n_obs}")
    print(f"Ventana media móvil: {window}")
    print(f"Punto de corte     : observación {punto_corte} "
          f"(≈ {t_arr[min(punto_corte, n_obs-1)]:.1f} min)\n")

    hdr = f"{'Métrica':<35} {'Con transitorio':<20} {'Sin transitorio':<20}"
    print(hdr); print("-" * 75)
    print(f"{'Wq promedio (min)':<35} {media_wq_antes:<20.4f} {media_wq_despues:<20.4f}")
    print(f"{'Wq desv. estándar':<35} {std_wq_antes:<20.4f} {std_wq_despues:<20.4f}")
    print(f"{'Ws promedio (min)':<35} {media_ws_antes:<20.4f} {media_ws_despues:<20.4f}")
    print(f"{'Observaciones usadas':<35} {n_obs:<20} {n_obs - punto_corte:<20}")

    # ── Gráfica ──
    fig, axes = plt.subplots(2, 2, figsize=(16, 12))
    fig.suptitle("Punto E – Eliminación del Estado Transitorio",
                 fontsize=16, fontweight="bold")

    # (0,0) Serie CON transitorio
    ax = axes[0, 0]
    ax.scatter(range(n_obs), v_wq, alpha=0.12, s=4, color="#2196F3",
               label="Observaciones")
    ax.plot(range(window-1, window-1+len(mm_wq)), mm_wq,
            color="red", lw=2, label="Media móvil")
    ax.axhline(media_wq_antes, color="green", ls="--",
               label=f"Media global: {media_wq_antes:.2f}")
    ax.axvline(punto_corte, color="orange", lw=2,
               label=f"Corte (obs {punto_corte})")
    ax.set_title("Wq – CON Estado Transitorio")
    ax.set_xlabel("Observación"); ax.set_ylabel("Wq (min)")
    ax.legend(fontsize=8)

    # (0,1) Serie SIN transitorio
    ax = axes[0, 1]
    estable = v_wq[punto_corte:]
    ax.scatter(range(len(estable)), estable, alpha=0.12, s=4,
               color="#4CAF50", label="Observaciones (estable)")
    w2 = max(10, len(estable) // 20)
    mm2 = np.convolve(estable, np.ones(w2)/w2, mode="valid")
    ax.plot(range(w2-1, w2-1+len(mm2)), mm2, color="red", lw=2,
            label="Media móvil")
    ax.axhline(media_wq_despues, color="green", ls="--",
               label=f"Media: {media_wq_despues:.2f}")
    ax.set_title("Wq – SIN Estado Transitorio")
    ax.set_xlabel("Observación"); ax.set_ylabel("Wq (min)")
    ax.legend(fontsize=8)

    # (1,0) Medias por bloque
    ax = axes[1, 0]
    colores_b = ["#E91E63" if i < corte_b else "#4CAF50"
                 for i in range(n_bloques)]
    ax.bar(range(1, n_bloques+1), medias_b, color=colores_b,
           edgecolor="black", alpha=0.8)
    ax.axhline(media_wq_despues, color="blue", ls="--", lw=2,
               label=f"Media estable: {media_wq_despues:.2f}")
    ax.axvline(corte_b + 0.5, color="orange", lw=2,
               label="Fin del transitorio")
    ax.set_title("Media de Wq por Bloque")
    ax.set_xlabel("Bloque"); ax.set_ylabel("Wq (min)")
    ax.legend(fontsize=8)

    # (1,1) Histogramas antes / después
    ax = axes[1, 1]
    ax.hist(v_wq, bins=40, alpha=0.45, color="#E91E63", density=True,
            edgecolor="black",
            label=f"Con transitorio (μ={media_wq_antes:.2f})")
    ax.hist(estable, bins=40, alpha=0.45, color="#4CAF50", density=True,
            edgecolor="black",
            label=f"Sin transitorio (μ={media_wq_despues:.2f})")
    ax.set_title("Distribución de Wq: Antes vs Después")
    ax.set_xlabel("Wq (min)"); ax.set_ylabel("Densidad")
    ax.legend(fontsize=9)

    plt.tight_layout()
    ruta = os.path.join(OUTPUT_DIR, "punto_e_transitorio.png")
    plt.savefig(ruta, bbox_inches="tight")
    plt.close()
    print(f"\nGráfica guardada: {ruta}")


# =====================================================================
#  GRÁFICA ADICIONAL – EVOLUCIÓN TEMPORAL DE COLAS
# =====================================================================
def grafica_evolucion_colas(replicas, num_cajeros):
    """Genera una gráfica con la evolución temporal de cada cola."""
    rep = replicas[0]

    fig, axes = plt.subplots(num_cajeros, 1,
                             figsize=(14, 3.5 * num_cajeros), sharex=True)
    if num_cajeros == 1:
        axes = [axes]
    fig.suptitle("Evolución Temporal de las Colas por Cajero",
                 fontsize=16, fontweight="bold")

    for cid in range(num_cajeros):
        ax = axes[cid]
        if rep[cid].serie_cola:
            ts = [t for t, _ in rep[cid].serie_cola]
            vs = [v for _, v in rep[cid].serie_cola]
            c  = COLORES_CAJERO[cid % len(COLORES_CAJERO)]
            ax.fill_between(ts, vs, alpha=0.25, color=c)
            ax.plot(ts, vs, color=c, lw=0.8)
        ax.set_title(f"Cajero {cid+1}", fontsize=12)
        ax.set_ylabel("Cola")

    axes[-1].set_xlabel("Tiempo (min)")
    plt.tight_layout()
    ruta = os.path.join(OUTPUT_DIR, "evolucion_colas.png")
    plt.savefig(ruta, bbox_inches="tight")
    plt.close()
    print(f"Gráfica guardada: {ruta}")


# =====================================================================
#  FUNCIÓN PRINCIPAL
# =====================================================================
def main():
    print("=" * 70)
    print("  SIMULACIÓN DEL PROBLEMA DE PARQUEADEROS")
    print("  Centro Comercial Supercentro – Modelo M/M/1")
    print("=" * 70)

    os.makedirs(OUTPUT_DIR, exist_ok=True)

    # Parámetros
    print(f"\nParámetros de simulación:")
    print(f"   Tiempo de simulación : {SIMULATION_TIME} min "
          f"({SIMULATION_TIME/60:.1f} h)")
    print(f"   Réplicas             : {NUM_REPLICAS}")
    print(f"   Cajeros (base)       : {NUM_CAJEROS_BASE}")
    print(f"   Semilla aleatoria    : {RANDOM_SEED}\n")

    for t, p in TIPOS_USUARIO.items():
        print(f"   {t:12s} → servicio = {p['tiempo_servicio']} min, "
              f"llegada = {p['media_llegada']} min")

    # Valores teóricos
    teo = calcular_valores_teoricos(NUM_CAJEROS_BASE)
    print(f"\nValores teóricos M/M/1 (por cajero con {NUM_CAJEROS_BASE} cajeros):")
    print(f"   λ_total = {teo['lambda_total']:.4f} usuarios/min")
    print(f"   λ_c     = {teo['lambda_c']:.4f} usuarios/min")
    print(f"   μ       = {teo['mu']:.4f} usuarios/min")
    print(f"   E[S]    = {teo['E_S']:.4f} min")
    print(f"   ρ       = {teo['rho']:.4f}")
    if teo["rho"] < 1:
        print(f"   Wq      = {teo['Wq']:.4f} min")
        print(f"   Ws      = {teo['Ws']:.4f} min")
        print(f"   Lq      = {teo['Lq']:.4f}")
        print(f"   Ls      = {teo['Ls']:.4f}")
    else:
        print("   ️  ρ ≥ 1 : sistema teóricamente inestable")

    print(f"\n   Proporciones naturales por tipo de usuario:")
    for t, p in teo["proporciones"].items():
        print(f"     {t:12s} : {p*100:.1f}%")

    # ── Ejecutar réplicas base ──
    print(f"\n{'='*70}")
    print(f"Ejecutando {NUM_REPLICAS} réplicas con {NUM_CAJEROS_BASE} cajeros…")
    print(f"{'='*70}")
    replicas_base = ejecutar_replicas(NUM_REPLICAS, NUM_CAJEROS_BASE)
    print(" Réplicas base completadas\n")

    # ── Análisis por punto ──
    punto_a_analisis_estadistico(replicas_base, NUM_CAJEROS_BASE)
    punto_b_medidas_tendencia(replicas_base, NUM_CAJEROS_BASE)
    punto_c_analisis_escenarios()
    punto_d_verificacion(replicas_base, NUM_CAJEROS_BASE)
    punto_e_estado_transitorio(replicas_base, NUM_CAJEROS_BASE)
    grafica_evolucion_colas(replicas_base, NUM_CAJEROS_BASE)

    # ── Resumen final ──
    print("\n" + "=" * 70)
    print("    SIMULACIÓN COMPLETADA EXITOSAMENTE")
    print("=" * 70)
    print(f"\n Las gráficas se guardaron en la carpeta '{OUTPUT_DIR}/':")
    for f in [
        "punto_a_analisis_estadistico.png",
        "punto_b_tendencia_central.png",
        "punto_c_escenarios.png",
        "punto_d_verificacion.png",
        "punto_e_transitorio.png",
        "evolucion_colas.png",
    ]:
        print(f"   · {f}")
    print()


if __name__ == "__main__":
    main()
