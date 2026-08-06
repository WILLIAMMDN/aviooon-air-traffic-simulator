# ✈ AVIOOON — Simulador de Tráfico Aéreo 3D

Simulador interactivo de trayectorias aéreas en 3D. Define aeronaves con
funciones paramétricas `x(t)`, `y(t)`, `z(t)` y observa su vuelo animado,
con **detección de colisiones**, **alertas sonoras** y **métricas de vuelo**.

Proyecto de Cálculo Vectorial — Python + CustomTkinter + Matplotlib + SymPy.

---

## ✨ Características

- 🛫 **Trayectorias paramétricas**: cada avión se define con expresiones
  matemáticas (`10*cos(t)`, `sin(t)`, …) evaluadas simbólicamente con SymPy.
- 🚨 **Detección de colisiones**: distancia mínima entre cada par de
  aeronaves; si bajan del umbral se marca el punto de conflicto en rojo y
  se registra la alerta.
- 🔊 **Alertas sonoras**: secuencia de beeps (winsound) al producirse una
  colisión y pitido corto en alertas preventivas. Se puede silenciar.
- 🎨 **Gestión de vuelos**: agregar, **editar, eliminar y duplicar** aviones,
  elegir color, cargar presets y **guardar/cargar escenarios** en JSON.
- 📊 **Métricas de vuelo**: distancia recorrida, altitud máxima y velocidad
  media por aeronave.
- ⏯ **Controles de reproducción**: pausar, reanudar, reiniciar y velocidad
  ajustable (0.25x – 2x).
- 🖥 **Interfaz moderna** con CustomTkinter (tema oscuro).

---

## 📦 Requisitos

- Python **3.10+** (desarrollado con 3.11)
- Windows (las alertas sonoras usan `winsound`; en otros sistemas se desactivan)

## 🚀 Instalación

```bash
cd AVIOOON
pip install -r requirements.txt
python main.py
```

## 🎮 Uso

1. Agrega un avión indicando su nombre, funciones `x(t)`, `y(t)`, `z(t)`,
   tiempo de simulación y color.
2. (Opcional) aplica un **preset** de ejemplo o carga un escenario JSON.
3. Pulsa **🚀 Iniciar simulación**.
4. En el visor 3D: pausa, ajusta velocidad y observa el **registro de
   alertas** cuando dos aviones se acerquen.

### Ejemplo rápido

| Avión | x(t) | y(t) | z(t) |
|---|---|---|---|
| OR-001 | `10*cos(t)` | `10*sin(t)` | `t` |
| OR-002 | `10*cos(t+0.2)` | `10*sin(t+0.2)` | `t` |

→ Ambos orbitan muy cerca: se detecta una **colisión** en la animación.

---

## 🗂 Estructura del proyecto

```
AVIOOON/
├── main.py                     # Punto de entrada
├── requirements.txt
├── README.md
├── aviooon/                    # Paquete principal
│   ├── config.py               # Constantes y umbrales
│   ├── core/                   # Lógica pura (sin UI)
│   │   ├── aircraft.py         # Modelo de aeronave
│   │   ├── trajectory.py       # Evaluación y muestreo de trayectorias
│   │   ├── collision.py        # Detección de colisiones
│   │   └── simulation.py       # Motor: trayectorias + colisiones + métricas
│   ├── data/
│   │   └── scenario_manager.py # Presets, guardar y cargar JSON
│   ├── gui/
│   │   ├── main_window.py      # Ventana de configuración
│   │   └── simulation_window.py# Visor 3D animado con alertas
│   └── utils/
│       └── sound.py            # Alarmas sonoras (winsound)
├── scenarios/
│   └── ejemplo.json            # Escenario de ejemplo
└── tests/
    └── test_collision.py       # Pruebas unitarias
```

## 🧪 Tests

```bash
python -m unittest discover -s tests -v
```

---

## 🛠 Tecnologías

- [CustomTkinter](https://github.com/TomSchimansky/CustomTkinter) — interfaz
- [Matplotlib](https://matplotlib.org/) — visualización 3D
- [SymPy](https://www.sympy.org/) — evaluación simbólica de trayectorias
- [NumPy](https://numpy.org/) — cálculo numérico

## 👤 Autor

**William Medina Castro** — Proyecto de Cálculo Vectorial · EPIS · 2025
