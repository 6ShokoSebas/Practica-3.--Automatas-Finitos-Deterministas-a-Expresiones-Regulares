import tkinter as tk
from tkinter import ttk, filedialog, messagebox, simpledialog
import xml.etree.ElementTree as ET
import json
from collections import deque

# ─────────────────────────────────────────────
#  OPERACIONES BÁSICAS DE LENGUAJE
# ─────────────────────────────────────────────
def obtener_prefijos(w):
    return list({w[:i] if w[:i] else "λ" for i in range(len(w) + 1)})

def obtener_sufijos(w):
    return list({w[i:] if w[i:] else "λ" for i in range(len(w) + 1)})

def obtener_subcadenas(w):
    return list({w[i:j] if w[i:j] else "λ" for i in range(len(w) + 1) for j in range(i, len(w) + 1)})

def obtener_positiva(alfabeto, max_longitud):
    resultado = set(alfabeto)
    actual = set(alfabeto)
    while True:
        siguiente = {s1 + s2 for s1 in actual for s2 in alfabeto if len(s1 + s2) <= max_longitud}
        if not siguiente:
            break
        resultado.update(siguiente)
        actual = siguiente
    return list(resultado)

def obtener_kleene(alfabeto, max_longitud):
    resultado = set(obtener_positiva(alfabeto, max_longitud))
    resultado.add("λ")
    return list(resultado)


# ─────────────────────────────────────────────
#  MOTOR LÓGICO – AUTÓMATA (AFD / AFND / AFNλ)
# ─────────────────────────────────────────────
class Automata:
    """
    Representación unificada de los tres tipos de autómata.
    tipo: 'AFD' | 'AFND' | 'AFNλ'
    transiciones[estado][simbolo] → set de estados destino
    Para AFD se garantiza ≤ 1 destino; λ se codifica como 'λ'.
    """

    def __init__(self):
        self.estados   = set()
        self.alfabeto  = set()
        self.inicial   = None
        self.aceptacion = set()
        self.transiciones = {}   # dict[estado] -> dict[simbolo] -> set(estados)
        self.tipo      = "AFD"

    # ── utilidades internas ──────────────────
    def _trans_set(self, estado, simbolo):
        return self.transiciones.get(estado, {}).get(simbolo, set())

    def lambda_clausura(self, estados):
        """Calcula λ-clausura de un conjunto de estados."""
        clausura = set(estados)
        pila = list(estados)
        while pila:
            s = pila.pop()
            for t in self._trans_set(s, "λ"):
                if t not in clausura:
                    clausura.add(t)
                    pila.append(t)
        return frozenset(clausura)

    # ── carga desde archivo ──────────────────
    def cargar_jff(self, ruta):
        tree = ET.parse(ruta)
        root = tree.getroot()
        automaton = root.find('automaton')

        self.estados.clear(); self.aceptacion.clear()
        self.transiciones.clear(); self.alfabeto.clear()
        self.tipo = "AFD"

        for state in automaton.findall('state'):
            s_id = state.get('id')
            self.estados.add(s_id)
            self.transiciones[s_id] = {}
            if state.find('initial') is not None:
                self.inicial = s_id
            if state.find('final') is not None:
                self.aceptacion.add(s_id)

        for trans in automaton.findall('transition'):
            origen  = trans.find('from').text
            destino = trans.find('to').text
            sym_node = trans.find('read')
            simbolo  = sym_node.text if (sym_node is not None and sym_node.text) else "λ"

            if simbolo != "λ":
                self.alfabeto.add(simbolo)
            self.transiciones.setdefault(origen, {}).setdefault(simbolo, set()).add(destino)

        # detectar tipo
        self._detectar_tipo()

    def _detectar_tipo(self):
        tiene_lambda = any("λ" in t for t in self.transiciones.values())
        no_det = any(len(v) > 1 for t in self.transiciones.values() for v in t.values())
        if tiene_lambda:
            self.tipo = "AFNλ"
        elif no_det:
            self.tipo = "AFND"
        else:
            self.tipo = "AFD"

    # ── simulación AFD ───────────────────────
    def procesar_cadena_afd(self, cadena):
        if self.inicial is None:
            return False, []
        estado_actual = self.inicial
        traza = [estado_actual]
        for simbolo in cadena:
            destinos = self._trans_set(estado_actual, simbolo)
            if not destinos:
                return False, traza
            estado_actual = next(iter(destinos))
            traza.append(estado_actual)
        return estado_actual in self.aceptacion, traza

    # alias para compatibilidad con práctica anterior
    def procesar_cadena(self, cadena):
        aceptada, traza = self.procesar_cadena_afd(cadena)
        return aceptada, traza

    # ── simulación AFND (sin λ) ──────────────
    def procesar_cadena_afnd(self, cadena):
        """Devuelve (aceptada, lista_de_pasos)
           donde cada paso es (simbolo, conjunto_estados_activos)."""
        estados_activos = frozenset({self.inicial})
        pasos = [("INICIO", estados_activos)]
        for simbolo in cadena:
            nuevos = frozenset(
                d for s in estados_activos for d in self._trans_set(s, simbolo)
            )
            pasos.append((simbolo, nuevos))
            estados_activos = nuevos
            if not estados_activos:
                break
        aceptada = bool(estados_activos & self.aceptacion)
        return aceptada, pasos

    # ── simulación AFNλ ──────────────────────
    def procesar_cadena_afnl(self, cadena):
        """Devuelve (aceptada, lista_de_pasos_detallados)."""
        estados_activos = self.lambda_clausura({self.inicial})
        pasos = [("INICIO / λ-clausura", estados_activos)]
        for simbolo in cadena:
            # mover con símbolo
            after_sym = frozenset(
                d for s in estados_activos for d in self._trans_set(s, simbolo)
            )
            # aplicar λ-clausura
            after_lc = self.lambda_clausura(after_sym)
            pasos.append((simbolo, after_sym))
            pasos.append(("λ-clausura", after_lc))
            estados_activos = after_lc
            if not estados_activos:
                break
        aceptada = bool(estados_activos & self.aceptacion)
        return aceptada, pasos

    # ── conversión AFND → AFD (subconjuntos) ──
    def convertir_afnd_a_afd(self):
        """Retorna un nuevo objeto Automata de tipo AFD."""
        afd = Automata()
        afd.alfabeto = set(self.alfabeto)
        afd.tipo = "AFD"

        q0_set = frozenset({self.inicial})
        cola = deque([q0_set])
        visitados = {}
        contador = 0

        def nombre(fs):
            return "{" + ",".join(sorted(fs)) + "}"

        visitados[q0_set] = str(contador)
        afd.inicial = str(contador)
        afd.estados.add(str(contador))
        afd.transiciones[str(contador)] = {}
        if q0_set & self.aceptacion:
            afd.aceptacion.add(str(contador))
        contador += 1

        while cola:
            cur_set = cola.popleft()
            cur_id = visitados[cur_set]
            for sym in self.alfabeto:
                dest_set = frozenset(
                    d for s in cur_set for d in self._trans_set(s, sym)
                )
                if not dest_set:
                    continue
                if dest_set not in visitados:
                    visitados[dest_set] = str(contador)
                    afd.estados.add(str(contador))
                    afd.transiciones[str(contador)] = {}
                    if dest_set & self.aceptacion:
                        afd.aceptacion.add(str(contador))
                    cola.append(dest_set)
                    contador += 1
                dest_id = visitados[dest_set]
                afd.transiciones[cur_id][sym] = {dest_id}
        return afd, visitados

    # ── conversión AFNλ → AFND ───────────────
    def convertir_afnl_a_afnd(self):
        """Elimina transiciones λ; retorna nuevo Automata AFND."""
        afnd = Automata()
        afnd.alfabeto = set(self.alfabeto)
        afnd.tipo = "AFND"
        afnd.estados = set(self.estados)
        afnd.inicial = self.inicial
        afnd.transiciones = {s: {} for s in self.estados}

        for s in self.estados:
            lc = self.lambda_clausura({s})
            # si la clausura contiene aceptación → s es de aceptación
            if lc & self.aceptacion:
                afnd.aceptacion.add(s)
            for sym in self.alfabeto:
                destinos = frozenset(
                    d for t in lc for d in self._trans_set(t, sym)
                )
                if destinos:
                    # aplicar λ-clausura de los destinos
                    total = self.lambda_clausura(destinos)
                    afnd.transiciones[s][sym] = set(total)
        return afnd

    # ── minimización de AFD ──────────────────
    def minimizar_afd(self):
        """
        Algoritmo de Hopcroft / tabla de pares distinguibles.
        Retorna (afd_min, info_dict) donde info_dict contiene grupos, etc.
        """
        # 1. Eliminar estados inaccesibles
        accesibles = set()
        cola = deque([self.inicial])
        while cola:
            s = cola.popleft()
            if s in accesibles:
                continue
            accesibles.add(s)
            for sym in self.alfabeto:
                for d in self._trans_set(s, sym):
                    if d not in accesibles:
                        cola.append(d)

        estados_util = accesibles
        inaccesibles = self.estados - accesibles

        # 2. Tabla de pares distinguibles (Myhill-Nerode / Hopcroft simplificado)
        estados_lista = sorted(estados_util)
        n = len(estados_lista)
        idx = {s: i for i, s in enumerate(estados_lista)}

        distinguible = [[False] * n for _ in range(n)]

        # Paso base: (aceptación, no-aceptación)
        for i in range(n):
            for j in range(i + 1, n):
                si, sj = estados_lista[i], estados_lista[j]
                if (si in self.aceptacion) != (sj in self.aceptacion):
                    distinguible[i][j] = True

        # Paso inductivo
        changed = True
        while changed:
            changed = False
            for i in range(n):
                for j in range(i + 1, n):
                    if distinguible[i][j]:
                        continue
                    si, sj = estados_lista[i], estados_lista[j]
                    for sym in self.alfabeto:
                        di_set = self._trans_set(si, sym)
                        dj_set = self._trans_set(sj, sym)
                        di = next(iter(di_set)) if di_set else None
                        dj = next(iter(dj_set)) if dj_set else None
                        if di is None and dj is None:
                            continue
                        if (di is None) != (dj is None):
                            distinguible[i][j] = True
                            changed = True
                            break
                        ii, jj = (idx[di], idx[dj]) if idx[di] < idx[dj] else (idx[dj], idx[di])
                        if distinguible[ii][jj]:
                            distinguible[i][j] = True
                            changed = True
                            break

        # 3. Construir grupos equivalentes
        padre = {s: s for s in estados_lista}

        def find(x):
            while padre[x] != x:
                padre[x] = padre[padre[x]]
                x = padre[x]
            return x

        def union(x, y):
            padre[find(x)] = find(y)

        for i in range(n):
            for j in range(i + 1, n):
                if not distinguible[i][j]:
                    union(estados_lista[i], estados_lista[j])

        grupos = {}
        for s in estados_lista:
            r = find(s)
            grupos.setdefault(r, set()).add(s)

        # 4. Construir AFD mínimo
        afd_min = Automata()
        afd_min.alfabeto = set(self.alfabeto)
        afd_min.tipo = "AFD"

        repr_map = {}  # estado original → representante del grupo
        for rep, grupo in grupos.items():
            for s in grupo:
                repr_map[s] = rep
            afd_min.estados.add(rep)
            if self.inicial in grupo:
                afd_min.inicial = rep
            if grupo & self.aceptacion:
                afd_min.aceptacion.add(rep)
            afd_min.transiciones[rep] = {}

        for rep, grupo in grupos.items():
            s = next(iter(grupo))
            for sym in self.alfabeto:
                destinos = self._trans_set(s, sym)
                if destinos:
                    dest = next(iter(destinos))
                    afd_min.transiciones[rep][sym] = {repr_map[dest]}

        info = {
            "inaccesibles": inaccesibles,
            "grupos": grupos,
            "repr_map": repr_map,
            "estados_antes": len(estados_util) + len(inaccesibles),
            "estados_despues": len(afd_min.estados),
            "estados_util": len(estados_util),
        }
        return afd_min, info


# ─────────────────────────────────────────────
#  INTERFAZ GRÁFICA
# ─────────────────────────────────────────────
class SimuladorApp:
    COLOR_AFD  = "#d4edda"
    COLOR_AFND = "#d1ecf1"
    COLOR_AFNL = "#fff3cd"
    COLOR_BTN  = "#6c757d"

    def __init__(self, root):
        self.root = root
        self.root.title("Simulador de Autómatas Finitos – Práctica 3 · ESCOM")
        self.root.geometry("820x680")
        self.root.resizable(True, True)
        self.automata = Automata()
        self._build_ui()

    # ── construcción de la UI ────────────────
    def _build_ui(self):
        # Título
        tk.Label(self.root, text="Simulador de Autómatas Finitos (AFD / AFND / AFN-λ)",
                 font=("Arial", 14, "bold"), pady=8).pack()

        # ── indicador de tipo ──
        self.lbl_tipo = tk.Label(self.root, text="Tipo: —", font=("Arial", 11, "bold"),
                                 bg="#eeeeee", relief="groove", padx=10, pady=4)
        self.lbl_tipo.pack(fill=tk.X, padx=20, pady=(0, 4))

        # ── fila: archivo / edición ──
        frm_arch = tk.Frame(self.root)
        frm_arch.pack(pady=3)
        tk.Button(frm_arch, text="✏️ Crear Manual",
                  command=self.editor_manual, bg="#fffacd",
                  font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=4)
        tk.Button(frm_arch, text="📂 Cargar Archivo",
                  command=self.cargar_archivo, bg="lightblue",
                  font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=4)
        tk.Button(frm_arch, text="💾 Exportar",
                  command=self.exportar_automata, bg="plum",
                  font=("Arial", 10, "bold")).pack(side=tk.LEFT, padx=4)

        # ── info autómata cargado ──
        self.lbl_info = tk.Label(self.root, text="Ningún autómata cargado.",
                                  fg="red", justify=tk.CENTER, font=("Arial", 9))
        self.lbl_info.pack(pady=3)

        # ── notebook con pestañas ──
        nb = ttk.Notebook(self.root)
        nb.pack(expand=True, fill=tk.BOTH, padx=10, pady=5)

        # Pestaña 1 – Simulación
        tab_sim = tk.Frame(nb)
        nb.add(tab_sim, text="  Simulación  ")
        self._build_tab_simulacion(tab_sim)

        # Pestaña 2 – Conversiones
        tab_conv = tk.Frame(nb)
        nb.add(tab_conv, text="  Conversiones  ")
        self._build_tab_conversiones(tab_conv)

        # Pestaña 3 – Minimización
        tab_min = tk.Frame(nb)
        nb.add(tab_min, text="  Minimización AFD  ")
        self._build_tab_minimizacion(tab_min)

        # Pestaña 4 – λ-clausura
        tab_lc = tk.Frame(nb)
        nb.add(tab_lc, text="  λ-clausura  ")
        self._build_tab_lambda(tab_lc)

        # Pestaña 5 – Visualización
        tab_vis = tk.Frame(nb)
        nb.add(tab_vis, text="  Visualización  ")
        self._build_tab_visualizacion(tab_vis)

        # Pestaña 6 – Extras / Lenguaje
        tab_ext = tk.Frame(nb)
        nb.add(tab_ext, text="  Operaciones  ")
        self._build_tab_extras(tab_ext)

    # ── pestaña simulación ───────────────────
    def _build_tab_simulacion(self, parent):
        tk.Label(parent, text="Cadena a evaluar:", font=("Arial", 10, "bold")).pack(pady=(12, 2))
        self.txt_cadena = tk.Entry(parent, width=50, font=("Arial", 12))
        self.txt_cadena.pack()

        frm = tk.Frame(parent); frm.pack(pady=8)
        tk.Button(frm, text="Validar Rápido",        command=self.validar_cadena, bg="#e2e3e5").pack(side=tk.LEFT, padx=5)
        tk.Button(frm, text="Paso a Paso",           command=self.paso_a_paso,   bg="lightgreen").pack(side=tk.LEFT, padx=5)
        tk.Button(frm, text="Múltiples Cadenas",     command=self.pruebas_multiples, bg="#ffc107").pack(side=tk.LEFT, padx=5)

        tk.Label(parent, text="Resultado:", font=("Arial", 10, "bold")).pack(pady=(10, 2))
        self.txt_resultado = tk.Text(parent, height=12, width=80, font=("Consolas", 10),
                                     state=tk.DISABLED, bg="#f8f9fa")
        self.txt_resultado.pack(expand=True, fill=tk.BOTH, padx=10, pady=4)

    # ── pestaña conversiones ─────────────────
    def _build_tab_conversiones(self, parent):
        tk.Label(parent, text="Conversiones entre tipos de autómatas",
                 font=("Arial", 11, "bold")).pack(pady=12)
        frm = tk.Frame(parent); frm.pack(pady=6)
        tk.Button(frm, text="AFNλ → AFND  (Eliminar λ)",
                  command=self.convertir_afnl_afnd,
                  bg=self.COLOR_AFNL, width=30, font=("Arial", 10, "bold")).pack(pady=4)
        tk.Button(frm, text="AFND → AFD  (Subconjuntos)",
                  command=self.convertir_afnd_afd,
                  bg=self.COLOR_AFND, width=30, font=("Arial", 10, "bold")).pack(pady=4)

        self.txt_conv = tk.Text(parent, height=18, width=80, font=("Consolas", 9),
                                state=tk.DISABLED, bg="#f8f9fa")
        self.txt_conv.pack(expand=True, fill=tk.BOTH, padx=10, pady=6)

    # ── pestaña minimización ─────────────────
    def _build_tab_minimizacion(self, parent):
        tk.Label(parent, text="Minimización de AFD (Algoritmo de Hopcroft)",
                 font=("Arial", 11, "bold")).pack(pady=12)
        tk.Button(parent, text="▶  Minimizar AFD actual",
                  command=self.minimizar_afd,
                  bg="#d4edda", font=("Arial", 10, "bold"), width=30).pack()
        self.txt_min = tk.Text(parent, height=22, width=80, font=("Consolas", 9),
                               state=tk.DISABLED, bg="#f8f9fa")
        self.txt_min.pack(expand=True, fill=tk.BOTH, padx=10, pady=8)

    # ── pestaña λ-clausura ───────────────────
    def _build_tab_lambda(self, parent):
        tk.Label(parent, text="Cálculo de λ-clausura",
                 font=("Arial", 11, "bold")).pack(pady=12)
        frm = tk.Frame(parent); frm.pack()
        tk.Label(frm, text="Estado(s) separados por coma:").pack(side=tk.LEFT)
        self.entry_lc = tk.Entry(frm, width=20); self.entry_lc.pack(side=tk.LEFT, padx=5)
        tk.Button(frm, text="Calcular", command=self.calcular_lambda_clausura,
                  bg=self.COLOR_AFNL).pack(side=tk.LEFT)

        self.txt_lc = tk.Text(parent, height=20, width=80, font=("Consolas", 10),
                              state=tk.DISABLED, bg="#f8f9fa")
        self.txt_lc.pack(expand=True, fill=tk.BOTH, padx=10, pady=8)

    # ── pestaña visualización ────────────────
    def _build_tab_visualizacion(self, parent):
        tk.Label(parent, text="Visualización del Autómata",
                 font=("Arial", 11, "bold")).pack(pady=12)
        frm = tk.Frame(parent); frm.pack(pady=4)
        tk.Button(frm, text="Ver Tabla de Transiciones", command=self.mostrar_tabla,
                  bg="#f0e68c").pack(side=tk.LEFT, padx=6)
        tk.Button(frm, text="Ver Grafo Visual", command=self.mostrar_grafo,
                  bg="#ffb6c1").pack(side=tk.LEFT, padx=6)

    # ── pestaña extras ───────────────────────
    def _build_tab_extras(self, parent):
        tk.Label(parent, text="Operaciones de Lenguaje Formal",
                 font=("Arial", 11, "bold")).pack(pady=12)
        frm = tk.Frame(parent); frm.pack()
        tk.Button(frm, text="Prefijos / Sufijos / Subcadenas",
                  command=self.mostrar_partes_cadena).pack(side=tk.LEFT, padx=5)
        tk.Button(frm, text="Cerradura Kleene (*) y Positiva (+)",
                  command=self.mostrar_kleene).pack(side=tk.LEFT, padx=5)

    # ─────────────────────────────────────────
    #  HELPERS UI
    # ─────────────────────────────────────────
    def _write_text(self, widget, texto):
        widget.config(state=tk.NORMAL)
        widget.delete("1.0", tk.END)
        widget.insert(tk.END, texto)
        widget.config(state=tk.DISABLED)

    def actualizar_info(self):
        a = self.automata
        tipos_color = {"AFD": self.COLOR_AFD, "AFND": self.COLOR_AFND, "AFNλ": self.COLOR_AFNL}
        color = tipos_color.get(a.tipo, "#eeeeee")
        self.lbl_tipo.config(text=f"Tipo actual: {a.tipo}", bg=color)
        info = (f"Estados: {sorted(a.estados)}  |  Alfabeto: {sorted(a.alfabeto)}\n"
                f"Inicial: q{a.inicial}  |  Aceptación: {sorted(a.aceptacion)}")
        self.lbl_info.config(text=info, fg="green")

    # ─────────────────────────────────────────
    #  CARGA / EXPORTACIÓN
    # ─────────────────────────────────────────
    def cargar_archivo(self):
        fp = filedialog.askopenfilename(
            filetypes=[("Soportados", "*.jff *.json *.xml"), ("JFLAP", "*.jff"),
                       ("JSON", "*.json"), ("XML", "*.xml")])
        if not fp:
            return
        try:
            if fp.endswith('.json'):
                with open(fp, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                self.automata.alfabeto   = set(data["alfabeto"])
                self.automata.estados    = set(data["estados"])
                self.automata.inicial    = data["inicial"]
                self.automata.aceptacion = set(data["aceptacion"])
                # convertir listas/strings a sets
                self.automata.transiciones = {}
                for est, trans in data["transiciones"].items():
                    self.automata.transiciones[est] = {}
                    for sym, dest in trans.items():
                        if isinstance(dest, list):
                            self.automata.transiciones[est][sym] = set(dest)
                        elif isinstance(dest, str):
                            self.automata.transiciones[est][sym] = {dest}
                        else:
                            self.automata.transiciones[est][sym] = set(dest)
                self.automata._detectar_tipo()
            else:
                self.automata.cargar_jff(fp)
            self.actualizar_info()
            messagebox.showinfo("Éxito", f"Autómata ({self.automata.tipo}) cargado correctamente.")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    def exportar_automata(self):
        fp = filedialog.asksaveasfilename(
            defaultextension=".json",
            filetypes=[("JSON", "*.json"), ("JFLAP/XML", "*.jff *.xml")])
        if not fp:
            return
        try:
            if fp.endswith('.json'):
                data = {
                    "tipo": self.automata.tipo,
                    "alfabeto": list(self.automata.alfabeto),
                    "estados": list(self.automata.estados),
                    "inicial": self.automata.inicial,
                    "aceptacion": list(self.automata.aceptacion),
                    "transiciones": {e: {s: list(d) for s, d in t.items()}
                                     for e, t in self.automata.transiciones.items()}
                }
                with open(fp, 'w', encoding='utf-8') as f:
                    json.dump(data, f, indent=4, ensure_ascii=False)
            else:
                root_el = ET.Element("structure")
                ET.SubElement(root_el, "type").text = "fa"
                auto_el = ET.SubElement(root_el, "automaton")
                for est in self.automata.estados:
                    s_el = ET.SubElement(auto_el, "state", id=str(est), name=f"q{est}")
                    if str(est) == str(self.automata.inicial):
                        ET.SubElement(s_el, "initial")
                    if str(est) in self.automata.aceptacion:
                        ET.SubElement(s_el, "final")
                for orig, trans in self.automata.transiciones.items():
                    for sym, dests in trans.items():
                        for dest in dests:
                            t_el = ET.SubElement(auto_el, "transition")
                            ET.SubElement(t_el, "from").text = str(orig)
                            ET.SubElement(t_el, "to").text = str(dest)
                            ET.SubElement(t_el, "read").text = "" if sym == "λ" else sym
                tree = ET.ElementTree(root_el)
                tree.write(fp, encoding="utf-8", xml_declaration=True)
            messagebox.showinfo("Éxito", f"Exportado a:\n{fp}")
        except Exception as e:
            messagebox.showerror("Error", str(e))

    # ─────────────────────────────────────────
    #  EDITOR MANUAL
    # ─────────────────────────────────────────
    def editor_manual(self):
        dlg = tk.Toplevel(self.root)
        dlg.title("Crear Autómata Manual")
        dlg.geometry("500x540")
        dlg.grab_set()

        tk.Label(dlg, text="Crear Autómata Manual",
                 font=("Arial", 12, "bold")).pack(pady=10)

        # Tipo
        frm_tipo = tk.Frame(dlg); frm_tipo.pack(pady=4)
        tk.Label(frm_tipo, text="Tipo de autómata:").pack(side=tk.LEFT)
        tipo_var = tk.StringVar(value="AFD")
        for t in ("AFD", "AFND", "AFNλ"):
            tk.Radiobutton(frm_tipo, text=t, variable=tipo_var, value=t).pack(side=tk.LEFT, padx=3)

        def campo(parent, etiqueta):
            tk.Label(parent, text=etiqueta, font=("Arial", 9)).pack(anchor=tk.W, padx=20)
            e = tk.Entry(parent, width=60, font=("Arial", 10))
            e.pack(padx=20, pady=2)
            return e

        e_alf  = campo(dlg, "Alfabeto (separado por comas, ej: 0,1):")
        e_est  = campo(dlg, "Estados (separado por comas, ej: q0,q1,q2):")
        e_ini  = campo(dlg, "Estado inicial:")
        e_acep = campo(dlg, "Estados de aceptación (separado por comas):")

        tk.Label(dlg, text="Transiciones (una por línea: origen,símbolo,destino):",
                 font=("Arial", 9)).pack(anchor=tk.W, padx=20, pady=(8, 0))
        tk.Label(dlg, text="  Para λ escribe: origen,λ,destino  |  AFND: origen,a,dest1,dest2,...",
                 font=("Arial", 8), fg="gray").pack(anchor=tk.W, padx=20)
        txt_trans = tk.Text(dlg, height=8, width=60, font=("Consolas", 9))
        txt_trans.pack(padx=20, pady=4)

        def guardar():
            a = self.automata
            a.tipo = tipo_var.get()
            a.alfabeto   = {x.strip() for x in e_alf.get().split(",") if x.strip()}
            a.estados    = {x.strip() for x in e_est.get().split(",") if x.strip()}
            a.inicial    = e_ini.get().strip()
            a.aceptacion = {x.strip() for x in e_acep.get().split(",") if x.strip() and x.strip() in a.estados}
            a.transiciones = {s: {} for s in a.estados}

            if a.inicial not in a.estados:
                messagebox.showerror("Error", "El estado inicial no está en el conjunto de estados.", parent=dlg)
                return

            lineas = txt_trans.get("1.0", tk.END).strip().splitlines()
            for ln in lineas:
                partes = [p.strip() for p in ln.split(",")]
                if len(partes) < 3:
                    continue
                orig, sym = partes[0], partes[1]
                dests = set(partes[2:])
                if orig not in a.estados:
                    continue
                if sym == "λ" or sym in a.alfabeto or a.tipo in ("AFND", "AFNλ"):
                    a.transiciones.setdefault(orig, {}).setdefault(sym, set()).update(dests)

            a._detectar_tipo()
            self.actualizar_info()
            dlg.destroy()

        tk.Button(dlg, text="Guardar Autómata", command=guardar,
                  bg="#d4edda", font=("Arial", 10, "bold")).pack(pady=10)

    # ─────────────────────────────────────────
    #  SIMULACIÓN
    # ─────────────────────────────────────────
    def validar_cadena(self):
        cadena = self.txt_cadena.get()
        if not self.automata.estados:
            messagebox.showwarning("Aviso", "No hay autómata cargado.")
            return
        a = self.automata
        if a.tipo == "AFD":
            aceptada, traza = a.procesar_cadena_afd(cadena)
            txt = f"Tipo: AFD\nCadena: '{cadena}'\nResultado: {'✅ ACEPTADA' if aceptada else '❌ RECHAZADA'}\n"
            txt += "Traza: " + " → ".join(f"q{s}" for s in traza)
        elif a.tipo == "AFND":
            aceptada, pasos = a.procesar_cadena_afnd(cadena)
            txt = f"Tipo: AFND\nCadena: '{cadena}'\nResultado: {'✅ ACEPTADA' if aceptada else '❌ RECHAZADA'}\n\n"
            for sym, conj in pasos:
                txt += f"  [{sym}]  →  {{{', '.join(sorted(conj))}}}\n"
        else:  # AFNλ
            aceptada, pasos = a.procesar_cadena_afnl(cadena)
            txt = f"Tipo: AFN-λ\nCadena: '{cadena}'\nResultado: {'✅ ACEPTADA' if aceptada else '❌ RECHAZADA'}\n\n"
            for sym, conj in pasos:
                txt += f"  [{sym}]  →  {{{', '.join(sorted(conj))}}}\n"
        self._write_text(self.txt_resultado, txt)

    def paso_a_paso(self):
        cadena = self.txt_cadena.get()
        if not self.automata.estados:
            return
        a = self.automata
        lineas = [f"━━━ Simulación Paso a Paso ({a.tipo}) ━━━",
                  f"Cadena: '{cadena}'\n"]

        if a.tipo == "AFD":
            aceptada, traza = a.procesar_cadena_afd(cadena)
            lineas.append(f"Estado inicial: q{a.inicial}")
            for i, sym in enumerate(cadena):
                if i + 1 < len(traza):
                    lineas.append(f"Paso {i+1}: δ(q{traza[i]}, '{sym}') = q{traza[i+1]}")
                else:
                    lineas.append(f"Paso {i+1}: ✗ Sin transición desde q{traza[i]} con '{sym}'")
                    break
            lineas.append(f"\nEstado final: q{traza[-1]}")
            lineas.append("Resultado: " + ("✅ ACEPTADA" if aceptada else "❌ RECHAZADA"))

        elif a.tipo == "AFND":
            aceptada, pasos = a.procesar_cadena_afnd(cadena)
            for sym, conj in pasos:
                lineas.append(f"  [{sym:^8}]  Estados activos: {{{', '.join(sorted(conj))}}}")
            lineas.append("\nResultado: " + ("✅ ACEPTADA" if aceptada else "❌ RECHAZADA"))

        else:  # AFNλ
            aceptada, pasos = a.procesar_cadena_afnl(cadena)
            for sym, conj in pasos:
                if sym.startswith("λ"):
                    lineas.append(f"  [λ-clausura]  {{{', '.join(sorted(conj))}}}")
                else:
                    lineas.append(f"  [símbolo '{sym}']  →  {{{', '.join(sorted(conj))}}}")
            lineas.append("\nResultado: " + ("✅ ACEPTADA" if aceptada else "❌ RECHAZADA"))

        self._write_text(self.txt_resultado, "\n".join(lineas))

    def pruebas_multiples(self):
        """Permite cargar un .txt con cadenas (una por línea) y genera informe."""
        if not self.automata.estados:
            messagebox.showwarning("Aviso", "Carga un autómata primero.")
            return
        fp = filedialog.askopenfilename(title="Seleccionar archivo de cadenas",
                                         filetypes=[("Texto", "*.txt"), ("Todos", "*.*")])
        if not fp:
            return
        with open(fp, 'r', encoding='utf-8') as f:
            cadenas = [ln.strip() for ln in f if ln.strip()]

        a = self.automata
        lineas = [f"Informe de Pruebas Múltiples ({a.tipo})", "=" * 50]
        aceptadas = rechazadas = 0
        for cad in cadenas:
            if a.tipo == "AFD":
                ok, _ = a.procesar_cadena_afd(cad)
            elif a.tipo == "AFND":
                ok, _ = a.procesar_cadena_afnd(cad)
            else:
                ok, _ = a.procesar_cadena_afnl(cad)
            estado = "✅ ACEPTADA" if ok else "❌ RECHAZADA"
            if ok:
                aceptadas += 1
            else:
                rechazadas += 1
            lineas.append(f"  '{cad}'  →  {estado}")

        lineas += ["", f"Total: {len(cadenas)}  |  Aceptadas: {aceptadas}  |  Rechazadas: {rechazadas}"]
        self._write_text(self.txt_resultado, "\n".join(lineas))

    # ─────────────────────────────────────────
    #  CONVERSIONES
    # ─────────────────────────────────────────
    def convertir_afnl_afnd(self):
        if self.automata.tipo != "AFNλ":
            messagebox.showwarning("Aviso", "El autómata actual no es AFN-λ.\nCarga o crea uno de tipo AFN-λ.")
            return
        afnd = self.automata.convertir_afnl_a_afnd()
        lineas = ["━━━ Conversión: AFN-λ → AFND (Eliminación de λ) ━━━",
                  f"Estados: {sorted(afnd.estados)}",
                  f"Alfabeto: {sorted(afnd.alfabeto)}",
                  f"Estado inicial: q{afnd.inicial}",
                  f"Estados de aceptación: {sorted(afnd.aceptacion)}",
                  "", "Tabla de transiciones:"]
        sims = sorted(afnd.alfabeto)
        enc = "Estado".ljust(12) + "  ".join(s.ljust(20) for s in sims)
        lineas.append(enc)
        lineas.append("-" * len(enc))
        for est in sorted(afnd.estados):
            fila = est.ljust(12)
            for sym in sims:
                dests = afnd.transiciones.get(est, {}).get(sym, set())
                fila += ("{" + ",".join(sorted(dests)) + "}").ljust(22) if dests else "-".ljust(22)
            lineas.append(fila)

        self._write_text(self.txt_conv, "\n".join(lineas))
        if messagebox.askyesno("Cargar", "¿Deseas cargar el AFND resultante como autómata activo?"):
            self.automata = afnd
            self.actualizar_info()

    def convertir_afnd_afd(self):
        if self.automata.tipo not in ("AFND", "AFNλ"):
            messagebox.showwarning("Aviso", "El autómata actual ya es un AFD.")
            return
        afd, visitados = self.automata.convertir_afnd_a_afd()
        lineas = ["━━━ Conversión: AFND → AFD (Construcción de Subconjuntos) ━━━",
                  "", "Mapeo de conjuntos de estados → nuevo estado:"]
        for fs, nid in sorted(visitados.items(), key=lambda x: int(x[1])):
            marca = " [INICIAL]" if nid == afd.inicial else ""
            marca += " [ACEPTACIÓN]" if nid in afd.aceptacion else ""
            lineas.append(f"  Estado {nid}: {{{', '.join(sorted(fs))}}}{marca}")

        lineas += ["", "Tabla de transiciones del AFD resultante:"]
        sims = sorted(afd.alfabeto)
        enc = "Estado".ljust(10) + "  ".join(s.ljust(10) for s in sims)
        lineas.append(enc)
        lineas.append("-" * len(enc))
        for est in sorted(afd.estados, key=lambda x: int(x)):
            fila = est.ljust(10)
            for sym in sims:
                dests = afd.transiciones.get(est, {}).get(sym, set())
                fila += (next(iter(dests)) if dests else "-").ljust(12)
            lineas.append(fila)

        self._write_text(self.txt_conv, "\n".join(lineas))
        if messagebox.askyesno("Cargar", "¿Deseas cargar el AFD resultante como autómata activo?"):
            self.automata = afd
            self.actualizar_info()

    # ─────────────────────────────────────────
    #  MINIMIZACIÓN
    # ─────────────────────────────────────────
    def minimizar_afd(self):
        a = self.automata
        if a.tipo != "AFD":
            messagebox.showwarning("Aviso", "La minimización sólo aplica a AFD.\nConvierte primero si es necesario.")
            return
        if not a.estados:
            messagebox.showwarning("Aviso", "No hay autómata cargado.")
            return

        afd_min, info = a.minimizar_afd()
        lineas = ["━━━ Minimización de AFD (Algoritmo de Hopcroft) ━━━"]
        lineas.append(f"\nEstados originales (total): {info['estados_antes']}")
        lineas.append(f"  ├─ Accesibles:    {info['estados_util']}")
        lineas.append(f"  └─ Inaccesibles:  {len(info['inaccesibles'])} → {sorted(info['inaccesibles'])}")
        lineas.append(f"\nEstados del AFD mínimo: {info['estados_despues']}")
        eliminados = info['estados_antes'] - info['estados_despues']
        if eliminados == 0:
            lineas.append("  ✅ El AFD ya es mínimo. No se pueden eliminar más estados.")
        else:
            lineas.append(f"  ✂️  Se eliminaron {eliminados} estado(s).")

        lineas.append("\nGrupos de estados equivalentes (clases de equivalencia):")
        for i, (rep, grupo) in enumerate(sorted(info['grupos'].items())):
            lineas.append(f"  Clase {i+1}: {{{', '.join(sorted(grupo))}}} → representante: {rep}")

        lineas.append("\nTabla de transiciones del AFD mínimo:")
        sims = sorted(afd_min.alfabeto)
        enc = "Estado".ljust(12) + "  ".join(s.ljust(10) for s in sims)
        lineas.append(enc)
        lineas.append("-" * len(enc))
        for est in sorted(afd_min.estados):
            ini_mark = "→ " if est == afd_min.inicial else "  "
            acep_mark = "*" if est in afd_min.aceptacion else " "
            fila = f"{ini_mark}{acep_mark}{est}".ljust(12)
            for sym in sims:
                dests = afd_min.transiciones.get(est, {}).get(sym, set())
                fila += (next(iter(dests)) if dests else "-").ljust(12)
            lineas.append(fila)

        lineas += ["", "Leyenda: → estado inicial  |  * estado de aceptación"]

        self._write_text(self.txt_min, "\n".join(lineas))
        if messagebox.askyesno("Cargar", "¿Cargar el AFD mínimo como autómata activo?"):
            self.automata = afd_min
            self.actualizar_info()

    # ─────────────────────────────────────────
    #  λ-CLAUSURA
    # ─────────────────────────────────────────
    def calcular_lambda_clausura(self):
        a = self.automata
        if not a.estados:
            messagebox.showwarning("Aviso", "No hay autómata cargado.")
            return
        raw = self.entry_lc.get().strip()
        estados_entrada = {s.strip() for s in raw.split(",") if s.strip() in a.estados}
        if not estados_entrada:
            messagebox.showwarning("Aviso", f"Estado(s) '{raw}' no encontrados.")
            return
        clausura = a.lambda_clausura(estados_entrada)
        lineas = [f"λ-clausura({{{', '.join(sorted(estados_entrada))}}})",
                  "=" * 40,
                  f"Resultado: {{{', '.join(sorted(clausura))}}}",
                  "",
                  "Detalle de alcanzabilidad por λ:"]
        for s in sorted(estados_entrada):
            directos = a._trans_set(s, "λ")
            lineas.append(f"  δ(q{s}, λ) = {{{', '.join(sorted(directos))} }}" if directos
                          else f"  δ(q{s}, λ) = ∅")
        self._write_text(self.txt_lc, "\n".join(lineas))

    # ─────────────────────────────────────────
    #  TABLA Y GRAFO
    # ─────────────────────────────────────────
    def mostrar_tabla(self):
        if not self.automata.estados:
            messagebox.showwarning("Aviso", "No hay autómata cargado.")
            return
        a = self.automata
        top = tk.Toplevel(self.root)
        top.title(f"Tabla de Transiciones ({a.tipo})")
        top.geometry("560x360")

        sims = sorted(a.alfabeto) + (["λ"] if a.tipo == "AFNλ" else [])
        cols = ["Estado"] + sims
        tree = ttk.Treeview(top, columns=cols, show="headings")
        for c in cols:
            tree.heading(c, text=c)
            tree.column(c, anchor=tk.CENTER, width=90)

        for est in sorted(a.estados):
            pref = "→ " if str(est) == str(a.inicial) else "  "
            pref += "* " if str(est) in a.aceptacion else "  "
            fila = [f"{pref}q{est}"]
            for sym in sims:
                dests = a.transiciones.get(str(est), {}).get(sym, set())
                if dests:
                    fila.append("{" + ",".join(f"q{d}" for d in sorted(dests)) + "}")
                else:
                    fila.append("-")
            tree.insert("", tk.END, values=fila)

        sb = ttk.Scrollbar(top, orient=tk.VERTICAL, command=tree.yview)
        tree.configure(yscrollcommand=sb.set)
        tree.pack(side=tk.LEFT, expand=True, fill=tk.BOTH, padx=6, pady=6)
        sb.pack(side=tk.RIGHT, fill=tk.Y)

    def mostrar_grafo(self):
        if not self.automata.estados:
            messagebox.showwarning("Aviso", "No hay autómata cargado.")
            return
        try:
            import networkx as nx
            import matplotlib.pyplot as plt
            import matplotlib.patches as mpatches

            a = self.automata
            G = nx.MultiDiGraph()

            for orig, trans in a.transiciones.items():
                for sym, dests in trans.items():
                    for dest in dests:
                        if G.has_edge(f"q{orig}", f"q{dest}"):
                            for _, d in G[f"q{orig}"][f"q{dest}"].items():
                                d['label'] += f", {sym}"
                                break
                        else:
                            style = 'dashed' if sym == "λ" else 'solid'
                            G.add_edge(f"q{orig}", f"q{dest}", label=sym, style=style)

            pos = nx.spring_layout(G, seed=42)
            fig, ax = plt.subplots(figsize=(8, 6))

            colors = []
            for n in G.nodes():
                raw = n.replace("q", "")
                if raw == str(a.inicial):
                    colors.append("#90EE90")
                elif raw in a.aceptacion:
                    colors.append("#FFD700")
                else:
                    colors.append("#ADD8E6")

            nx.draw_networkx_nodes(G, pos, node_color=colors, node_size=2000, ax=ax)
            nx.draw_networkx_labels(G, pos, font_size=10, font_weight="bold", ax=ax)

            # dibujar aristas (λ con línea punteada)
            solid_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('style') != 'dashed']
            dashed_edges = [(u, v) for u, v, d in G.edges(data=True) if d.get('style') == 'dashed']
            nx.draw_networkx_edges(G, pos, edgelist=solid_edges, arrows=True,
                                   arrowsize=20, ax=ax, connectionstyle='arc3,rad=0.1')
            nx.draw_networkx_edges(G, pos, edgelist=dashed_edges, arrows=True,
                                   arrowsize=20, ax=ax, style='dashed',
                                   connectionstyle='arc3,rad=0.1', edge_color='purple')

            edge_labels = {(u, v): d['label'] for u, v, d in G.edges(data=True)}
            nx.draw_networkx_edge_labels(G, pos, edge_labels=edge_labels,
                                          font_color="red", font_size=8, ax=ax)

            # doble círculo en estados de aceptación
            for n in G.nodes():
                if n.replace("q", "") in a.aceptacion:
                    x, y = pos[n]
                    circle = plt.Circle((x, y), 0.08, color='gold', fill=False, linewidth=2)
                    ax.add_patch(circle)

            legend = [
                mpatches.Patch(color="#90EE90", label="Estado inicial"),
                mpatches.Patch(color="#FFD700", label="Estado de aceptación"),
                mpatches.Patch(color="#ADD8E6", label="Estado regular"),
            ]
            ax.legend(handles=legend, loc="lower right")
            ax.set_title(f"Grafo del Autómata ({a.tipo})")
            ax.axis('off')
            plt.tight_layout()
            plt.show()

        except ImportError:
            messagebox.showerror("Librería faltante",
                                  "Instala las librerías necesarias:\npip install networkx matplotlib")

    # ─────────────────────────────────────────
    #  EXTRAS
    # ─────────────────────────────────────────
    def mostrar_partes_cadena(self):
        cadena = self.txt_cadena.get() if hasattr(self, 'txt_cadena') else ""
        if not cadena:
            cadena = simpledialog.askstring("Cadena", "Ingresa una cadena:") or ""
        if not cadena:
            return
        pref = sorted(obtener_prefijos(cadena), key=len)
        suf  = sorted(obtener_sufijos(cadena), key=len)
        sub  = sorted(obtener_subcadenas(cadena), key=len)
        msg  = f"Cadena: '{cadena}'\n\nPREFIJOS:\n{pref}\n\nSUFIJOS:\n{suf}\n\nSUBCADENAS:\n{sub}"
        self._crear_ventana_resultados("Subcadenas, Prefijos y Sufijos", msg)

    def mostrar_kleene(self):
        if not self.automata.alfabeto:
            messagebox.showwarning("Aviso", "Carga un autómata primero.")
            return
        n = simpledialog.askinteger("Cerradura", "Longitud máxima (n):", minvalue=1, maxvalue=8)
        if n:
            pos = sorted(obtener_positiva(self.automata.alfabeto, n), key=len)
            kle = sorted(obtener_kleene(self.automata.alfabeto, n), key=len)
            msg = (f"Alfabeto: {sorted(self.automata.alfabeto)}\n\n"
                   f"CERRADURA POSITIVA (+):\n{pos}\n\n"
                   f"CERRADURA DE KLEENE (*):\n{kle}")
            self._crear_ventana_resultados("Cerraduras", msg)

    def _crear_ventana_resultados(self, titulo, contenido):
        top = tk.Toplevel(self.root)
        top.title(titulo)
        top.geometry("520x420")
        txt = tk.Text(top, wrap=tk.WORD, font=("Consolas", 10))
        txt.insert(tk.END, contenido)
        txt.pack(expand=True, fill=tk.BOTH, padx=10, pady=10)
        tk.Button(top, text="Guardar en .txt",
                  command=lambda: self._guardar_txt(contenido),
                  bg="lightgray").pack(pady=5)

    def _guardar_txt(self, contenido):
        fp = filedialog.asksaveasfilename(defaultextension=".txt",
                                           filetypes=[("Texto", "*.txt")])
        if fp:
            with open(fp, 'w', encoding='utf-8') as f:
                f.write(contenido)
            messagebox.showinfo("Éxito", "Archivo guardado.")


# ─────────────────────────────────────────────
#  PUNTO DE ENTRADA
# ─────────────────────────────────────────────
if __name__ == "__main__":
    root = tk.Tk()
    app = SimuladorApp(root)
    root.mainloop()
