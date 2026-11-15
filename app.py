"""
Explorador de la encuesta de liderazgo y clima del grupo.
Unidad de Ingeniería y Ciencias Básicas.

Ejecutar en local:   streamlit run app.py
Datos:               carpeta datos/ (formato largo). Para un nuevo semestre,
                     agregue filas a datos/datos_largos.csv con otro valor en "periodo".
"""
import pandas as pd
import numpy as np
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st

st.set_page_config(page_title="Encuesta de liderazgo y clima", layout="wide")

# ---------- Constantes ----------
COL = ["#b8302f", "#e66767", "#bdbcb6", "#86b6ef", "#2a78d6"]  # 1 → 5, divergente apta para daltonismo
ETQ = ["1 Totalmente en desacuerdo", "2 En desacuerdo", "3 Ni de acuerdo ni en desacuerdo", "4 De acuerdo", "5 Totalmente de acuerdo"]
BLOQUES = ["Liderazgo", "Clima", "Organización y carga"]


def fmt(v, d=1):
    """Número con coma decimal (es-CO)."""
    return f"{v:,.{d}f}".replace(",", "X").replace(".", ",").replace("X", ".")


# ---------- Datos ----------
@st.cache_data
def cargar(subido=None):
    datos = pd.read_csv(subido if subido is not None else "datos/datos_largos.csv", dtype={"periodo": str})
    temas = pd.read_csv("datos/temas_abiertas.csv")
    abiertas = pd.read_csv("datos/respuestas_abiertas.csv", keep_default_na=False)  # conserva "N/A" como texto
    datos["respuesta"] = pd.to_numeric(datos["respuesta"], errors="coerce")
    return datos, temas, abiertas


with st.sidebar:
    st.header("Filtros")
    subido = st.file_uploader("Cargar otro CSV (mismas columnas)", type="csv")
    datos, temas, abiertas = cargar(subido)
    periodos = sorted(datos.periodo.unique(), reverse=True)
    periodo = st.selectbox("Periodo", periodos)
    bloques_sel = st.multiselect("Bloques", BLOQUES, default=BLOQUES)
    orden = st.radio("Orden de los ítems", ["Como en el cuestionario", "Menor acuerdo primero"])
    excluir = st.multiselect("Excluir encuestas (análisis de sensibilidad)", sorted(datos.encuesta.unique()))
    st.caption("Excluir encuestas sirve para ver cuánto pesan pocas respuestas en un grupo pequeño; no para descartar opiniones.")

d = datos[(datos.periodo == periodo) & (~datos.encuesta.isin(excluir))]
v = d.dropna(subset=["respuesta"])
n_enc = v.encuesta.nunique()

# ---------- Encabezado ----------
p5 = (v.respuesta == 5).mean() * 100
st.title(f"El {fmt(p5)} % de las respuestas es «Totalmente de acuerdo»")
st.caption(f"Encuesta de liderazgo y clima del grupo · Unidad de Ingeniería y Ciencias Básicas · Periodo {periodo} · "
           f"n = {n_enc} encuestas, {len(v)} respuestas válidas ({d.respuesta.isna().sum()} sin respuesta o NS) · Escala 1 a 5")

prev = [p for p in periodos if p < periodo]
c = st.columns(5)
c[0].metric("Encuestas (n)", n_enc)
delta = None
if prev:
    pv = datos[(datos.periodo == prev[0])].dropna(subset=["respuesta"])
    delta = f"{fmt(p5 - (pv.respuesta == 5).mean() * 100)} pp vs {prev[0]}"
c[1].metric("Respuestas con 5", f"{fmt(p5)} %", delta)
mb = v.groupby("bloque").respuesta.mean()
for i, b in enumerate(BLOQUES):
    c[2 + i].metric(f"Promedio {b}", fmt(mb.get(b, np.nan), 2))
if not prev:
    st.caption("Primera medición: no hay periodo anterior para comparar.")

# ---------- Resumen por ítem ----------
it = (v.groupby(["item", "bloque", "afirmacion"]).respuesta
      .agg(n="size", media="mean", **{f"n{k}": (lambda s, k=k: (s == k).sum()) for k in range(1, 6)}).reset_index())
it["pct_4_5"] = (it.n4 + it.n5) / it.n * 100
it = it[it.bloque.isin(bloques_sel)]
if orden == "Menor acuerdo primero":
    it = it.sort_values(["pct_4_5", "media"])

tab1, tab2, tab3, tab4 = st.tabs(["Acuerdo por ítem", "Quién respondió qué", "Por persona", "Respuestas abiertas"])

with tab1:
    pc = it[["n1", "n2", "n3", "n4", "n5"]].div(it.n, axis=0) * 100
    y = it.item + " " + it.afirmacion
    fig = go.Figure()
    for nom, x, col, real, leg in [(ETQ[2], -pc.n3 / 2, COL[2], pc.n3, False), (ETQ[1], -pc.n2, COL[1], pc.n2, True),
                                   (ETQ[0], -pc.n1, COL[0], pc.n1, True), (ETQ[2], pc.n3 / 2, COL[2], pc.n3, True),
                                   (ETQ[3], pc.n4, COL[3], pc.n4, True), (ETQ[4], pc.n5, COL[4], pc.n5, True)]:
        fig.add_bar(y=y, x=x, name=nom, orientation="h", marker_color=col, showlegend=leg, legendgroup=nom,
                    customdata=np.c_[real, it.n], hovertemplate="%{y}<br>" + nom + ": %{customdata[0]:.1f} % (n = %{customdata[1]})<extra></extra>")
    fig.update_layout(barmode="relative", height=28 * len(it) + 140, xaxis=dict(range=[-30, 100], ticksuffix=" %"),
                      yaxis=dict(autorange="reversed"), legend=dict(orientation="h", y=-0.1), separators=",.", margin=dict(l=10, r=10, t=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption("Desacuerdo a la izquierda del cero y acuerdo a la derecha; el neutro (3) se reparte a ambos lados.")
    tabla = it[["item", "afirmacion", "n", "n1", "n2", "n3", "n4", "n5", "media", "pct_4_5"]].rename(columns={"media": "promedio", "pct_4_5": "% 4-5"})
    st.dataframe(tabla.round(2), hide_index=True, use_container_width=True)
    st.download_button("Descargar resumen (CSV)", tabla.to_csv(index=False).encode("utf-8"), f"resumen_items_{periodo}.csv", "text/csv")

with tab2:
    m = d[d.bloque.isin(bloques_sel)].pivot(index="encuesta", columns="item", values="respuesta")
    fig = px.imshow(m, color_continuous_scale=[[0, COL[0]], [.25, COL[1]], [.5, COL[2]], [.75, COL[3]], [1, COL[4]]],
                    zmin=1, zmax=5, text_auto=True, aspect="auto", labels=dict(color="Respuesta", x="Ítem", y="Encuesta"))
    fig.update_traces(hovertemplate="Encuesta %{y} · %{x}<br>Respuesta: %{z}<extra></extra>")
    fig.update_layout(height=640, yaxis=dict(dtick=1), margin=dict(t=10))
    st.plotly_chart(fig, use_container_width=True)
    st.caption(f"Las respuestas de 2 y 3 se concentran en {v[v.respuesta <= 3].encuesta.nunique()} de {n_enc} encuestas. Celda vacía = sin respuesta o NS.")

with tab3:
    pe = v.groupby(["encuesta", "bloque"]).respuesta.mean().reset_index()
    fig = px.box(pe, x="bloque", y="respuesta", points="all", category_orders={"bloque": BLOQUES}, hover_data={"encuesta": True},
                 labels={"respuesta": "Promedio (1 a 5)", "bloque": ""})
    fig.update_traces(marker=dict(size=9, color=COL[4], opacity=.75), line_color="#8a8984", fillcolor="rgba(0,0,0,0)", jitter=.5, pointpos=0)
    fig.update_layout(yaxis_range=[1, 5.1], height=460, margin=dict(t=10))
    st.plotly_chart(fig, use_container_width=True)

with tab4:
    st.caption("Codificación manual por temas del periodo 2026-2; una respuesta puede tener varios temas.")
    preg = st.selectbox("Pregunta", temas.pregunta.unique())
    tc = temas[temas.pregunta == preg].groupby("tema").encuesta.nunique().sort_values().reset_index(name="encuestas")
    fig = px.bar(tc, x="encuestas", y="tema", orientation="h", text="encuestas", color_discrete_sequence=[COL[4]],
                 labels={"encuestas": "Encuestas", "tema": ""})
    fig.update_layout(height=60 * len(tc) + 80, margin=dict(t=10))
    st.plotly_chart(fig, use_container_width=True)
    tema = st.selectbox("Leer respuestas del tema", tc.sort_values("encuestas", ascending=False).tema)
    campo = "p" + preg[:2]
    encs = temas[(temas.pregunta == preg) & (temas.tema == tema)].encuesta
    for _, r in abiertas[abiertas.encuesta.isin(encs)].iterrows():
        st.markdown(f"> {r[campo] or '(sin texto)'}  \n> *Encuesta {r.encuesta}*")

with st.expander("Método y limitaciones"):
    st.markdown("""
- Datos transcritos a mano de 21 formularios en papel (15/11/2026). En la encuesta 18 las marcas son chulos; se tomó la celda donde empieza el trazo.
- Porcentajes sobre respuestas válidas de cada ítem; vacíos y NS se excluyen.
- Con n = 21 una persona mueve un ítem cerca de 5 puntos porcentuales; hay efecto techo (casi todo es 5).
- Posible sesgo de deseabilidad social: se evalúa al jefe inmediato.
""")
