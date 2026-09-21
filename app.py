import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

# Configuración de pantalla ancha y título
st.set_page_config(page_title="Conformidad de entregas", layout="wide")

# Etiqueta para bloquear la traducción automática del navegador y evitar el error removeChild
st.markdown('<meta name="google" content="notranslate">', unsafe_allow_html=True)

st.title("📦 Conformidad de entregas")

# Carga de datos sin perder ningún registro
@st.cache_data
def cargar_datos():
    df = pd.read_parquet("movimientos_tiendas.parquet")
    
    # Limpieza básica de espacios en nombres de columnas
    df.columns = df.columns.str.strip()
    
    # 1. Identificación de columnas base
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

    # 2. Creación de Aux art-mov
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

    # 4. Mapeo del Estado de Rectificación
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

    # Respaldo por estado si resulta vacío
    if df["Aux Art-Nota-tienda"].dropna().empty:
        es_rectificado = df["Estado Rectificación"] != "N - Nulo"
        artik_s = df[col_artik].fillna("SIN_ART").astype(str).str.strip().str.replace(r"\.0$", "", regex=True) if col_artik else df["Aux art-mov"]
        
        df.loc[es_rectificado, "Aux Art-Nota-tienda"] = (
            artik_s[es_rectificado] + "-" + 
            df.loc[es_rectificado, "Estado Rectificación"] + "-" + 
            df.loc[es_rectificado, "Tienda que Grabo_Limpia"]
        )

    # 6. Campos de Fecha manteniendo nulos
    col_fecha = "Fecha del Movimiento" if "Fecha del Movimiento" in df.columns else [c for c in df.columns if "FEC" in c.upper()][0]
    df["Fecha_DT"] = pd.to_datetime(df[col_fecha].astype(str), format="%Y%m%d", errors="coerce")
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
    
    m1.metric("Líneas Despachadas", f"{len(df):,}")
        
    if "Total Unidades" in df.columns:
        m2.metric("Total Unidades", f"{int(df['Total Unidades'].sum(skipna=True)):,}")
        
    costo_total = df["Costo_Linea"].sum(skipna=True) if "Costo_Linea" in df.columns else 0
    m3.metric("Costo Total Est.", f"")

    st.markdown("---")

    # FILA 2: Recuento por Estado
    st.subheader("📊 Desglose por Estado de Rectificación")
    e1, e2, e3, e4, e5 = st.columns(5)
    
    if "Estado Rectificación" in df.columns:
        confirmadas = len(df[df["Estado Rectificación"] == "Confirmada"])
        e1.metric("Confirmadas (M)", f"{confirmadas:,}")

        rechazadas = len(df[df["Estado Rectificación"] == "Anuladas"])
        e2.metric("Anuladas (R)", f"{rechazadas:,}")

        pendientes = len(df[df["Estado Rectificación"] == "Pendientes"])
        e3.metric("Pendientes (P)", f"{pendientes:,}")

        automaticas = len(df[df["Estado Rectificación"] == "Automática"])
        e4.metric("Automáticas (A)", f"{automaticas:,}")

        nulas = len(df[df["Estado Rectificación"] == "N - Nulo"])
        e5.metric("Nulas / Vacías (N)", f"{nulas:,}")

    st.markdown("---")

    # CONTROLES ÚNICOS DE NIVEL DE AGRUPACIÓN PARA EL EJE X
    st.subheader("📈 Visualización Temporal")
    
    opciones_eje_x = {
        "Año": "Año",
        "Mes": "Mes",
        "Semana": "N° Semana",
        "Fecha": "Fecha Formateada"
    }
    
    nivel_seleccionado = st.selectbox(
        "Nivel de detalle para el Eje X de los gráficos:",
        options=list(opciones_eje_x.keys()),
        index=2,
        key="select_nivel_eje_x"
    )
    
    col_eje_x = opciones_eje_x[nivel_seleccionado]

    # SECCIÓN DE GRÁFICOS
    c1, c2 = st.columns(2)

    if col_eje_x in df.columns:
        df_graf = df[df[col_eje_x].notna()].copy()
        
        # Agrupación asegurando orden temporal según la fecha datetime real
        if nivel_seleccionado == "Fecha":
            grouped = df_graf.groupby(["Fecha_DT", col_eje_x], as_index=False).agg(
                lineas_despachadas=(col_eje_x, "size"),
                notas_art=("Aux Art-Nota-tienda", lambda x: x.dropna().nunique())
            )
            grouped = grouped.sort_values(by="Fecha_DT").reset_index(drop=True)
        else:
            grouped = df_graf.groupby(col_eje_x, as_index=False).agg(
                lineas_despachadas=(col_eje_x, "size"),
                notas_art=("Aux Art-Nota-tienda", lambda x: x.dropna().nunique())
            )
            grouped = grouped.sort_values(by=col_eje_x).reset_index(drop=True)

        grouped["pct_rectificadas"] = (grouped["notas_art"] / grouped["lineas_despachadas"]) * 100
        eje_x_labels = grouped[col_eje_x].astype(str)

        with c1:
            st.markdown(f"**Líneas despachadas vs rectificadas**")
            fig1 = go.Figure()

            # Barras Rosas
            fig1.add_trace(go.Bar(
                x=eje_x_labels,
                y=grouped["lineas_despachadas"],
                name="Líneas despachadas",
                marker_color="#E06666"
            ))

            # Línea Azul
            fig1.add_trace(go.Scatter(
                x=eje_x_labels,
                y=grouped["pct_rectificadas"],
                name="% líneas rectificadas",
                mode="lines+markers+text",
                text=[f"{v:.2f} %" if pd.notna(v) else "0.00 %" for v in grouped["pct_rectificadas"]],
                textposition="top center",
                textfont=dict(size=11),
                line=dict(color="#1155CC", width=3),
                marker=dict(color="#1155CC", size=7),
                yaxis="y2"
            ))

            fig1.update_layout(
                template="streamlit",
                xaxis=dict(
                    title=nivel_seleccionado, 
                    type="category",
                    categoryorder="array",
                    categoryarray=list(eje_x_labels),
                    tickangle=-45, 
                    tickfont=dict(size=10)
                ),
                yaxis=dict(title="", showgrid=True),
                yaxis2=dict(title="", overlaying="y", side="right", ticksuffix=" %", showgrid=False),
                legend=dict(
                    orientation="h", 
                    yanchor="bottom", 
                    y=1.02, 
                    xanchor="left", 
                    x=0,
                    font=dict(size=12)
                ),
                margin=dict(l=20, r=20, t=40, b=30),
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)"
            )
            st.plotly_chart(fig1, width="stretch", key="grafico_lineas_despachadas")

        # GRÁFICO 2: Resolución líneas rectificadas
        if "Estado Rectificación" in df_graf.columns:
            df_rect = df_graf[df_graf["Estado Rectificación"].isin(["Anuladas", "Confirmada", "Pendientes"])].copy()
            
            if not df_rect.empty:
                if nivel_seleccionado == "Fecha":
                    pivot_rect = df_rect.groupby(["Fecha_DT", col_eje_x, "Estado Rectificación"]).size().unstack(fill_value=0)
                    pivot_rect = pivot_rect.reset_index().sort_values(by="Fecha_DT").set_index(col_eje_x).drop(columns=["Fecha_DT"])
                else:
                    pivot_rect = df_rect.groupby([col_eje_x, "Estado Rectificación"]).size().unstack(fill_value=0)
                    pivot_rect = pivot_rect.sort_index()

                pivot_pct = pivot_rect.div(pivot_rect.sum(axis=1), axis=0) * 100
                eje_x_rect_labels = pivot_pct.index.astype(str)

                with c2:
                    st.markdown(f"**Resolución líneas rectificadas**")
                    fig2 = go.Figure()

                    colors = {
                        "Anuladas": "#E69138",
                        "Confirmada": "#4A90E2",
                        "Pendientes": "#F1C232"
                    }

                    for estado in ["Anuladas", "Confirmada", "Pendientes"]:
                        if estado in pivot_pct.columns:
                            fig2.add_trace(go.Bar(
                                x=eje_x_rect_labels,
                                y=pivot_pct[estado],
                                name=estado,
                                marker_color=colors.get(estado, "#CCCCCC"),
                                text=[f"{v:.2f}%" if v > 0 else "" for v in pivot_pct[estado]],
                                textposition="inside",
                                textfont=dict(color="#000000", size=10)
                            ))

                    fig2.update_layout(
                        template="streamlit",
                        barmode="stack",
                        xaxis=dict(
                            title=nivel_seleccionado, 
                            type="category",
                            categoryorder="array",
                            categoryarray=list(eje_x_rect_labels),
                            tickangle=-45, 
                            tickfont=dict(size=10)
                        ),
                        yaxis=dict(ticksuffix="%", range=[0, 100], showgrid=True),
                        legend=dict(
                            orientation="h", 
                            yanchor="bottom", 
                            y=1.02, 
                            xanchor="left", 
                            x=0,
                            font=dict(size=12)
                        ),
                        margin=dict(l=20, r=20, t=40, b=30),
                        paper_bgcolor="rgba(0,0,0,0)",
                        plot_bgcolor="rgba(0,0,0,0)"
                    )
                    st.plotly_chart(fig2, width="stretch", key="grafico_resolucion_rectificadas")
            else:
                with c2:
                    st.markdown(f"**Resolución líneas rectificadas**")
                    st.info("No hay rectificaciones registradas para el nivel de filtro seleccionado.")

    st.markdown("---")

    # TABLA DE RECTIFICACIONES POR TIENDA DETALLADA
    st.subheader("🏪 Detalle de Rectificaciones por Tienda")
    
    if "Tienda que Grabo_Limpia" in df.columns and "Aux Art-Nota-tienda" in df.columns and "Estado Rectificación" in df.columns:
        base_tiendas = df.groupby("Tienda que Grabo_Limpia", as_index=False).agg(
            lineas_despachadas=("Tienda que Grabo_Limpia", "size"),
            lineas_rectificadas=("Aux Art-Nota-tienda", lambda x: x.dropna().nunique())
        )

        df_rect_notas = df[df["Aux Art-Nota-tienda"].notna() & (df["Estado Rectificación"] != "N - Nulo")].copy()

        pivot_estados = df_rect_notas.groupby(["Tienda que Grabo_Limpia", "Estado Rectificación"])["Aux Art-Nota-tienda"].nunique().unstack(fill_value=0)

        tabla_tiendas = base_tiendas.merge(pivot_estados, on="Tienda que Grabo_Limpia", how="left").fillna(0)

        for est_col in ["Confirmada", "Pendientes", "Anuladas", "Automática"]:
            if est_col not in tabla_tiendas.columns:
                tabla_tiendas[est_col] = 0

        tabla_tiendas["pct_rectificadas_num"] = (tabla_tiendas["lineas_rectificadas"] / tabla_tiendas["lineas_despachadas"]) * 100
        tabla_tiendas = tabla_tiendas.sort_values(by="lineas_rectificadas", ascending=False).reset_index(drop=True)

        tot_despachadas = len(df)
        tot_rectificadas = df["Aux Art-Nota-tienda"].dropna().nunique()
        
        tot_confirmadas = df_rect_notas[df_rect_notas["Estado Rectificación"] == "Confirmada"]["Aux Art-Nota-tienda"].nunique()
        tot_pendientes = df_rect_notas[df_rect_notas["Estado Rectificación"] == "Pendientes"]["Aux Art-Nota-tienda"].nunique()
        tot_anuladas = df_rect_notas[df_rect_notas["Estado Rectificación"] == "Anuladas"]["Aux Art-Nota-tienda"].nunique()
        tot_automaticas = df_rect_notas[df_rect_notas["Estado Rectificación"] == "Automática"]["Aux Art-Nota-tienda"].nunique()
        
        tot_pct = (tot_rectificadas / tot_despachadas * 100) if tot_despachadas > 0 else 0

        cols_select = [
            "Tienda que Grabo_Limpia", "lineas_rectificadas", 
            "Confirmada", "Pendientes", "Anuladas", "Automática", "pct_rectificadas_num"
        ]

        df_tiendas_disp = tabla_tiendas[cols_select].copy()
        df_tiendas_disp.columns = [
            "Tienda", "Líneas rectificadas", "Confirmadas (M)", 
            "Pendientes (P)", "Anuladas (R)", "Automáticas (A)", "% líneas rectificadas"
        ]

        fila_total = pd.DataFrame([{
            "Tienda": "Total",
            "Líneas rectificadas": tot_rectificadas,
            "Confirmadas (M)": tot_confirmadas,
            "Pendientes (P)": tot_pendientes,
            "Anuladas (R)": tot_anuladas,
            "Automáticas (A)": tot_automaticas,
            "% líneas rectificadas": tot_pct
        }])

        df_final_tiendas = pd.concat([df_tiendas_disp, fila_total], ignore_index=True)
        df_final_tiendas["% líneas rectificadas"] = df_final_tiendas["% líneas rectificadas"].apply(lambda x: f"{x:.2f} %".replace(".", ","))

        st.dataframe(df_final_tiendas, width="stretch", hide_index=True, key="tabla_resumen_tiendas")

except FileNotFoundError:
    st.error("⚠️ No se encontró el archivo 'movimientos_tiendas.parquet'.")
except Exception as e:
    st.error(f"Error procesando los datos: {e}")
