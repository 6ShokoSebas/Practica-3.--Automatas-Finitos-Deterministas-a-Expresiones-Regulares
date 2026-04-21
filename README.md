# 🧠 Simulador de Autómatas Finitos  
### 📘 Práctica 3 – Teoría de la Computación (ESCOM - IPN)

---

## 📖 Descripción

Este proyecto consiste en el desarrollo y extensión de un **simulador de autómatas finitos** implementado en Python.  

Incluye soporte completo para:

- ✅ Autómatas Finitos Deterministas (AFD)  
- ✅ Autómatas Finitos No Deterministas (AFND)  
- ✅ Autómatas Finitos con transiciones λ (AFN-λ)  
- ✅ Conversión entre modelos  
- ✅ Minimización de AFD (Algoritmo de Hopcroft)  

Además, se complementa con el uso de **JFLAP** para la conversión de autómatas a expresiones regulares.

---

## 👥 Autores

- **Gustavo Sebastián Bonilla Ojeda** — 2025630175  
- **Ximena Velázquez Mendoza** — 2024630176  
- **Yoltic Isaí Velázquez Ramos** — 2025230228  

📍 *ESCOM - Instituto Politécnico Nacional*  
📅 *Fecha: 13 de abril de 2026*  

---

## 🎯 Objetivos

### 🔹 Parte 1 – JFLAP
- Convertir AFD → Expresiones Regulares mediante:
  - Eliminación de estados  
  - Ecuaciones  
  - Método de Arden  

### 🔹 Parte 2 – Simulador
- Implementar un simulador base de AFD  

### 🔹 Parte 3 – Extensión
- Soporte para AFND y AFN-λ  
- Conversiones entre modelos  
- Minimización de AFD  

---

## 🚀 Características

### 🔍 Simulación
- Validación rápida de cadenas  
- Simulación paso a paso  
- Procesamiento de múltiples cadenas desde archivo  

### 🔁 Conversión de Autómatas
- AFN-λ → AFND  
- AFND → AFD  

### ⚡ Minimización
- Eliminación de estados inaccesibles  
- Tabla de pares distinguibles  
- Fusión de estados equivalentes  

### 📊 Visualización
- Grafo del autómata  
- Tabla de transiciones dinámica  

### 🧩 Funcionalidades extra
- Cálculo de λ-clausura  
- Operaciones de lenguaje:
  - Prefijos  
  - Sufijos  
  - Subcadenas  
  - Cerradura de Kleene  

---

## 🛠️ Tecnologías utilizadas

- **Python 3**
- **Tkinter** (Interfaz gráfica)
- **NetworkX** *(opcional, visualización)*
- **Matplotlib** *(opcional, visualización)*
- **JFLAP** (herramienta externa)

---

## ⚙️ Instalación

### 🔹 Requisitos

- Python 3.x instalado y en PATH  
- Tkinter  

### 🔹 Dependencias opcionales

```bash
pip install networkx matplotlib
````

---

## ▶️ Uso

### 1. Clonar repositorio

```bash
git clone https://github.com/tu-usuario/tu-repo.git
cd tu-repo
```

### 2. Ejecutar el programa

```bash
python simulador_practica3.py
```

---

## 📂 Formatos soportados

* `.jff` (JFLAP)
* `.xml`
* `.json`

✔ Detección automática del tipo de autómata

---

## 🧪 Ejemplos de uso

### 🔹 Simulación

1. Cargar o crear un autómata
2. Ingresar cadena
3. Seleccionar modo:

   * Validación rápida
   * Paso a paso

---

### 🔹 λ-clausura

* Calcular clausura de cualquier estado en tiempo real

---

### 🔹 Pruebas múltiples

* Cargar archivo `.txt`
* Una cadena por línea
* Generación automática de resultados

---

## 🧠 Implementación

### 📌 Representación interna

```python
dict[estado][símbolo] → set(estados)
```

Esto permite unificar:

* AFD (caso particular)
* AFND
* AFN-λ

---

### 🔁 Algoritmos implementados

#### ✔ λ-clausura

* BFS sobre transiciones λ

#### ✔ Conversión AFND → AFD

* Construcción por subconjuntos (powerset)

#### ✔ Minimización (Hopcroft)

1. Eliminación de estados inaccesibles
2. Refinamiento de particiones
3. Unión de estados equivalentes

---

## 📊 Resultados

* Correcta simulación de los tres modelos
* Conversión funcional entre autómatas
* Reducción óptima de estados en AFD

---

## 📚 Conclusiones

* Los modelos:

  * AFD
  * AFND
  * AFN-λ

son **equivalentes en capacidad expresiva**.

✔ Todos reconocen **lenguajes regulares**

* La minimización requiere:

  * Eliminación de estados inaccesibles
  * Refinamiento correcto de equivalencias

* La implementación unificada facilita la extensión del sistema

---

## 📌 Notas

* El uso de `networkx` y `matplotlib` es opcional
* Compatible con múltiples formatos de entrada
* Interfaz amigable para pruebas académicas

---
