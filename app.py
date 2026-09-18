import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# Configuración de pantalla ancha y título
st.set_page_config(page_title="Conformidad de entregas", layout="wide")
st.title("📦 Conformidad de entregas")

# Carga de datos sin perder ningún registro
@st.cache_data
def cargar_datos():
    df = pd.read_parquet("movimientos_tiendas.parquet")
    
    # Limpieza básica de espacios en nombres de columnas
    df.columns = df.columns.str.strip()
    
    # 1. Identificación de columnas base según esquema
    col_art = "BDART" if "BDART" in df.columns else ("Artículo" if "Artículo" in df.columns else None)
    col_num = "BDNUM" if "BDNUM" in df.columns else ("Num Mov" if "Num Mov" in df.columns else None)
    col_artik = "ARTIK" if "ARTIK" in df.columns else col_art
    
    col_tienda_grabo = None
    for c in ["TIEND que grabo", "Tienda que Grabo", "Tienda que grabo", "BDTIEN"]:
        if c in df.columns:
            col_tienda_grabo = c
            break

    col_nudvre = None
    for c in ["NUDVRE", "Num Dev", "Nota", "Num Nota", "NUM_DEV", "BDNDV"]:
        if c in df.columns:
            col_nudvre = c
            break

    # 2. Creación de Aux art-mov = BDMVTAL[BDART] & "-" & BDMVTAL[BDNUM]
    if col_art and col_num:
        art_s = df[col_art].fillna("SIN_ART").astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
        num_s = df[col_num].fillna("0").astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
        df["Aux art-mov"] = art_s + "-" + num_s
        df["Art-Mov"] = df["Aux art-mov"]
    else:
        df["Aux art-mov"] = "SIN_KEY"
        df["Art-Mov"] = df["Aux art-mov"]

    # 3. Tratamiento de Tiendas
    if col_tienda_grabo:
        df["Tienda que Grabo_Limpia"] = df[col_tienda_grabo].fillna("Sin Registro").astype(str).str.replace(r"\.0$", "", regex=True)
    else:
        df["Tienda que Grabo_Limpia"] = "Sin Registro"

    # 4. Mapeo del Estado de Rectificación primero
    if "Estado" in df.columns:
        estado_limpio = df["Estado"].fillna("N").astype(str).str.strip().str.upper()
        estado_limpio = estado_limpio.replace({"NAN": "N", "": "N", "NONE": "N"})
        
        mapa_estados = {
            "M": "Confirmada",
            "R": "Anuladas",
            "P": "Pendientes",
            "A": "Automática",
            "N": "N - Nulo"
        }
        df["Estado Rectificación"] = estado_limpio.map(mapa_estados).fillna("N - Nulo")
    else:
        df["Estado Rectificación"] = "N - Nulo"

    # 5. Creación de Aux Art-Nota-tienda
    df["Aux Art-Nota-tienda"] = None
    
    if col_nudvre and col_artik:
        nudvre_s = df[col_nudvre].fillna("").astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
        es_valido = (~nudvre_s.isin(["", "nan", "None", "0", "NAN"]))
        
        artik_s = df[col_artik].fillna("SIN_ART").astype(str).str.strip().str.replace(r"\.0$", "", regex=True)
        
        df.loc[es_valido, "Aux Art-Nota-tienda"] = (
            artik_s[es_valido] + "-" + 
            nudvre_s[es_valido] + "-" + 
            df.loc[es_valido, "Tienda que Grabo_Limpia"]
        )

    # Respaldo inteligente por estado si Aux Art-Nota-tienda resulta vacío
    if df["Aux Art-Nota-tienda"].dropna().empty:
        es_rectificado = df["Estado Rectificación"] != "N - Nulo"
        artik_s = df[col_artik].fillna("SIN_ART").astype(str).str.strip().str.replace(r"\.0$", "", regex=True) if col_artik else df["Aux art-mov"]
        
        df.loc[es_rectificado, "Aux Art-Nota-tienda"] = (
            artik_s[es_rectificado] + "-" + 
            df.loc[es_rectificado, "Estado Rectificación"] + "-" + 
            df.loc[es_rectificado, "Tienda que Grabo_Limpia"]
        )

    # 6. Campos de Fecha manteniendo nulos
    if "Fecha del Movimiento" in df.columns:
        df["Fecha_DT"] = pd.to_datetime(df["Fecha del Movimiento"].astype(str), format="%Y%m%d", errors="coerce")
        df["Fecha Formateada"] = df["Fecha_DT"].dt.strftime("%d/%m/%Y").fillna("Sin Fecha")
        df["Año"] = df["Fecha_DT"].dt.year
        df["Mes"] = df["Fecha_DT"].dt.month
        df["N° Semana"] = df["Fecha_DT"].dt.isocalendar().week
        df["Día"] = df["Fecha_DT"].dt.day

    # 7. Tratamiento de Área
    col_area = "AREA" if "AREA" in df.columns else ("Area" if "Area" in df.columns else None)
    if col_area:
        df["AREA_Limpia"] = df[col_area].fillna("Sin Área").astype(str).str.replace(r"\.0$", "", regex=True)

    # 8. Métricas numéricas
    for col in ["Total Unidades", "Precio medio de coste"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            
    if "Precio medio de coste" in df.columns and "Total Unidades" in df.columns:
        df["Costo_Linea"] = df["Precio medio de coste"] * df["Total Unidades"]
    else:
        df["Costo_Linea"] = 0
            
    return df

try:
    df = cargar_datos()

    # Sidebar: Filtros de Búsqueda
    st.sidebar.header("🔍 Filtros de Búsqueda")

    if "Tienda que Grabo_Limpia" in df.columns:
        tiendas_grabo = sorted([str(x) for x in df["Tienda que Grabo_Limpia"].unique()])
        tienda_grabo_sel = st.sidebar.multiselect("Tienda que Grabó:", tiendas_grabo, default=tiendas_grabo)
        df = df[df["Tienda que Grabo_Limpia"].isin(tienda_grabo_sel)]

    if "AREA_Limpia" in df.columns:
        areas = sorted([str(x) for x in df["AREA_Limpia"].unique()])
        area_sel = st.sidebar.multiselect("Área:", areas, default=areas)
        df = df[df["AREA_Limpia"].isin(area_sel)]

    if "Estado Rectificación" in df.columns:
        estados = sorted([str(x) for x in df["Estado Rectificación"].unique()])
        estado_sel = st.sidebar.multiselect("Estado Rectificación:", estados, default=estados)
        df = df[df["Estado Rectificación"].isin(estado_sel)]

    if "Almacen" in df.columns:
        almacenes = sorted([str(x) for x in df["Almacen"].fillna("Sin Almacén").astype(str).unique()])
        almacen_sel = st.sidebar.multiselect("Almacén:", almacenes, default=almacenes)
        df = df[df["Almacen"].fillna("Sin Almacén").astype(str).isin(almacen_sel)]

    if "Año" in df.columns and df["Año"].notna().any():
        anios = sorted([int(x) for x in df["Año"].dropna().unique()], reverse=True)
        if anios:
            anio_sel = st.sidebar.multiselect("Año:", anios, default=anios)
            df = df[df["Año"].isin(anio_sel) | df["Año"].isna()]

    if "Mes" in df.columns and df["Mes"].notna().any():
        meses = sorted([int(x) for x in df["Mes"].dropna().unique()])
        if meses:
            mes_sel = st.sidebar.multiselect("Mes:", meses, default=meses)
            df = df[df["Mes"].isin(mes_sel) | df["Mes"].isna()]

    if "N° Semana" in df.columns and df["N° Semana"].notna().any():
        semanas = sorted([int(x) for x in df["N° Semana"].dropna().unique()])
        if semanas:
            semana_sel = st.sidebar.multiselect("N° Semana:", semanas, default=semanas)
            df = df[df["N° Semana"].isin(semana_sel) | df["N° Semana"].isna()]

    if "Día" in df.columns and df["Día"].notna().any():
        dias = sorted([int(x) for x in df["Día"].dropna().unique()])
        if dias:
            dia_sel = st.sidebar.multiselect("Día del Mes:", dias, default=dias)
            df = df[df["Día"].isin(dia_sel) | df["Día"].isna()]

    # FILA 1: Métricas Generales
    m1, m2, m3 = st.columns(3)
    
    if "Aux art-mov" in df.columns:
        art_mov_unicos = df["Aux art-mov"].nunique()
        m1.metric("Líneas Despachadas (Aux art-mov Únicos)", f"{art_mov_unicos:,}")
    else:
        m1.metric("Líneas Despachadas", f"{len(df):,}")
        
    if "Total Unidades" in df.columns:
        m2.metric("Total Unidades", f"{int(df['Total Unidades'].sum(skipna=True)):,}")
        
    costo_total = df["Costo_Linea"].sum(skipna=True) if "Costo_Linea" in df.columns else 0
    m3.metric("Costo Total Est.", f"")

    st.markdown("---")

    # FILA 2: Recuento por Estado
    st.subheader("📊 Desglose por Estado de Rectificación (Aux art-mov Únicos)")
    e1, e2, e3, e4, e5 = st.columns(5)
    
    if "Estado Rectificación" in df.columns and "Aux art-mov" in df.columns:
        confirmadas = df[df["Estado Rectificación"] == "Confirmada"]["Aux art-mov"].nunique()
        e1.metric("Confirmadas (M)", f"{confirmadas:,}")

        rechazadas = df[df["Estado Rectificación"] == "Anuladas"]["Aux art-mov"].nunique()
        e2.metric("Anuladas (R)", f"{rechazadas:,}")

        pendientes = df[df["Estado Rectificación"] == "Pendientes"]["Aux art-mov"].nunique()
        e3.metric("Pendientes (P)", f"{pendientes:,}")

        automaticas = df[df["Estado Rectificación"] == "Automática"]["Aux art-mov"].nunique()
        e4.metric("Automáticas (A)", f"{automaticas:,}")

        nulas = df[df["Estado Rectificación"] == "N - Nulo"]["Aux art-mov"].nunique()
        e5.metric("Nulas / Vacías (N)", f"{nulas:,}")

    st.markdown("---")

    # SECCIÓN DE GRÁFICOS AGRUPADOS POR N° SEMANA
    c1, c2 = st.columns(2)

    if "N° Semana" in df.columns and "Aux art-mov" in df.columns:
        df_sem = df[df["N° Semana"] > 0].copy()
        
        grouped = df_sem.groupby("N° Semana").agg(
            lineas_despachadas=("Aux art-mov", "nunique"),
            notas_art=("Aux Art-Nota-tienda", lambda x: x.dropna().nunique())
        ).reset_index()

        grouped["pct_rectificadas"] = (grouped["notas_art"] / grouped["lineas_despachadas"]) * 100

        with c1:
            st.subheader("Líneas despachadas vs líneas rectificadas")
            fig1 = go.Figure()

            # Barras Rosas
            fig1.add_trace(go.Bar(
                x=grouped["N° Semana"],
                y=grouped["lineas_despachadas"],
                name="Líneas despachadas",
                marker_color="#F3C6E5"
            ))

            # Línea Gris Oscuro
            fig1.add_trace(go.Scatter(
                x=grouped["N° Semana"],
                y=grouped["pct_rectificadas"],
                name="% líneas rectificadas",
                mode="lines+markers+text",
                text=[f"{v:.2f} %" if pd.notna(v) else "0.00 %" for v in grouped["pct_rectificadas"]],
                textposition="top center",
                textfont=dict(color="#222222", size=12),
                line=dict(color="#555555", width=3),
                marker=dict(color="#555555", size=6),
                yaxis="y2"
            ))

            fig1.update_layout(
                font=dict(color="#333333"),
                xaxis=dict(title="Semana", dtick=1, tickfont=dict(color="#333333")),
                yaxis=dict(title="", showgrid=True, tickfont=dict(color="#333333")),
                yaxis2=dict(title="", overlaying="y", side="right", ticksuffix=" %", showgrid=False, tickfont=dict(color="#333333")),
                legend=dict(
                    orientation="h", 
                    yanchor="bottom", 
                    y=1.02, 
                    xanchor="left", 
                    x=0,
                    font=dict(color="#222222", size=13)
                ),
                margin=dict(l=20, r=20, t=40, b=20),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig1, width="stretch")

        # GRÁFICO 2: Resolución líneas rectificadas
        if "Estado Rectificación" in df_sem.columns:
            df_rect = df_sem[df_sem["Estado Rectificación"].isin(["Anuladas", "Confirmada", "Pendientes"])].copy()
            pivot_rect = df_rect.groupby(["N° Semana", "Estado Rectificación"])["Aux art-mov"].nunique().unstack(fill_value=0)

            pivot_pct = pivot_rect.div(pivot_rect.sum(axis=1), axis=0) * 100

            with c2:
                st.subheader("Resolución líneas rectificadas")
                fig2 = go.Figure()

                colors = {
                    "Anuladas": "#F5B79B",
                    "Confirmada": "#9CD0FF",
                    "Pendientes": "#FBE683"
                }

                for estado in ["Anuladas", "Confirmada", "Pendientes"]:
                    if estado in pivot_pct.columns:
                        fig2.add_trace(go.Bar(
                            x=pivot_pct.index,
                            y=pivot_pct[estado],
                            name=estado,
                            marker_color=colors.get(estado, "#CCCCCC"),
                            text=[f"{v:.2f}%" if v > 0 else "" for v in pivot_pct[estado]],
                            textposition="inside",
                            textfont=dict(color="#222222", size=11)
                        ))

                fig2.update_layout(
                    barmode="stack",
                    font=dict(color="#333333"),
                    xaxis=dict(title="Semana", dtick=1, tickfont=dict(color="#333333")),
                    yaxis=dict(ticksuffix="%", range=[0, 100], showgrid=True, tickfont=dict(color="#333333")),
                    legend=dict(
                        orientation="h", 
                        yanchor="bottom", 
                        y=1.02, 
                        xanchor="left", 
                        x=0,
                        font=dict(color="#222222", size=13)
                    ),
                    margin=dict(l=20, r=20, t=40, b=20),
                    paper_bgcolor="rgba(0,0,0,0)",
                    plot_bgcolor="rgba(0,0,0,0)"
                )
                st.plotly_chart(fig2, width="stretch")

    # Tabla con Datos
    st.subheader("📋 Registros Filtrados")
    st.dataframe(df, width="stretch")

except FileNotFoundError:
    st.error("⚠️ No se encontró el archivo 'movimientos_tiendas.parquet'.")
except Exception as e:
    st.error(f"Error procesando los datos: {e}")
