import streamlit as st
import pandas as pd

# Configuración de pantalla ancha y título
st.set_page_config(page_title="Conformidad de entregas", layout="wide")
st.title("📦 Conformidad de entregas")

# Carga de datos sin perder ningún registro
@st.cache_data
def cargar_datos():
    df = pd.read_parquet("movimientos_tiendas.parquet")
    
    # Limpieza básica de espacios en nombres de columnas
    df.columns = df.columns.str.strip()
    
    # 1. Creación de la clave Art-Mov
    col_art = "Artículo" if "Artículo" in df.columns else ("BDART" if "BDART" in df.columns else None)
    col_num = "Num Mov" if "Num Mov" in df.columns else ("BDNUM" if "BDNUM" in df.columns else None)
    
    if col_art and col_num:
        art_s = df[col_art].fillna("SIN_ART").astype(str).str.strip()
        num_s = df[col_num].fillna("0").astype(str).str.strip()
        df["Art-Mov"] = art_s + "-" + num_s
    
    # 2. Tratamiento de Tiendas (preservando nulos como 'Sin Registro')
    for col_t in ["Tienda", "Tienda que Grabo"]:
        if col_t in df.columns:
            df[col_t] = df[col_t].fillna("Sin Registro").astype(str).str.replace(r"\.0$", "", regex=True)
    
    # 3. Campos de Fecha manteniendo nulos
    if "Fecha del Movimiento" in df.columns:
        df["Fecha_DT"] = pd.to_datetime(df["Fecha del Movimiento"].astype(str), format="%Y%m%d", errors="coerce")
        df["Fecha Formateada"] = df["Fecha_DT"].dt.strftime("%d/%m/%Y").fillna("Sin Fecha")
        df["Año"] = df["Fecha_DT"].dt.year
        df["Mes"] = df["Fecha_DT"].dt.month
        df["N° Semana"] = df["Fecha_DT"].dt.isocalendar().week
        df["Día"] = df["Fecha_DT"].dt.day
    
    # 4. Mapeo del Estado de Rectificación: Llenado explícito de NULOS
    if "Estado" in df.columns:
        estado_limpio = df["Estado"].fillna("N").astype(str).str.strip().str.upper()
        estado_limpio = estado_limpio.replace({"NAN": "N", "": "N", "NONE": "N"})
        
        mapa_estados = {
            "M": "Confirmada",
            "R": "Rechazada",
            "P": "Pendiente",
            "A": "Automática",
            "N": "N - Nulo"
        }
        df["Estado Rectificación"] = estado_limpio.map(mapa_estados).fillna("N - Nulo")
    
    # 5. Métricas numéricas
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
    
    # Filtro por Tienda Destino
    if "Tienda" in df.columns:
        tiendas = sorted([str(x) for x in df["Tienda"].unique()])
        tienda_sel = st.sidebar.multiselect("Tienda:", tiendas, default=tiendas)
        df = df[df["Tienda"].isin(tienda_sel)]

    # Filtro por Tienda que Grabó
    if "Tienda que Grabo" in df.columns:
        tiendas_grabo = sorted([str(x) for x in df["Tienda que Grabo"].unique()])
        tienda_grabo_sel = st.sidebar.multiselect("Tienda que Grabó:", tiendas_grabo, default=tiendas_grabo)
        df = df[df["Tienda que Grabo"].isin(tienda_grabo_sel)]

    # Filtro por Estado Rectificación (Incluye N - Nulo)
    if "Estado Rectificación" in df.columns:
        estados = sorted([str(x) for x in df["Estado Rectificación"].unique()])
        estado_sel = st.sidebar.multiselect("Estado Rectificación:", estados, default=estados)
        df = df[df["Estado Rectificación"].isin(estado_sel)]

    # Filtro por Almacén
    if "Almacen" in df.columns:
        almacenes = sorted([str(x) for x in df["Almacen"].fillna("Sin Almacén").astype(str).unique()])
        almacen_sel = st.sidebar.multiselect("Almacén:", almacenes, default=almacenes)
        df = df[df["Almacen"].fillna("Sin Almacén").astype(str).isin(almacen_sel)]

    # Filtros de Tiempo
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

    # FILA 1: Métricas Generales del Negocio
    m1, m2, m3 = st.columns(3)
    m1.metric("Líneas Despachadas (Total)", f"{len(df):,}")
    
    if "Total Unidades" in df.columns:
        m2.metric("Total Unidades", f"{int(df['Total Unidades'].sum(skipna=True)):,}")
        
    costo_total = df["Costo_Linea"].sum(skipna=True) if "Costo_Linea" in df.columns else 0
    m3.metric("Costo Total Est.", f"")

    st.markdown("---")

    # FILA 2: Recuento Individual por Cada Estado
    st.subheader("📊 Desglose por Estado de Rectificación")
    e1, e2, e3, e4, e5 = st.columns(5)
    
    if "Estado Rectificación" in df.columns:
        confirmadas = len(df[df["Estado Rectificación"] == "Confirmada"])
        e1.metric("Confirmadas (M)", f"{confirmadas:,}")

        rechazadas = len(df[df["Estado Rectificación"] == "Rechazada"])
        e2.metric("Rechazadas (R)", f"{rechazadas:,}")

        pendientes = len(df[df["Estado Rectificación"] == "Pendiente"])
        e3.metric("Pendientes (P)", f"{pendientes:,}")

        automaticas = len(df[df["Estado Rectificación"] == "Automática"])
        e4.metric("Automáticas (A)", f"{automaticas:,}")

        nulas = len(df[df["Estado Rectificación"] == "N - Nulo"])
        e5.metric("Nulas / Vacías (N)", f"{nulas:,}")

    st.markdown("---")

    # Gráficos
    c1, c2 = st.columns(2)
    with c1:
        if "Fecha Formateada" in df.columns and "Total Unidades" in df.columns:
            st.subheader("Evolución de Unidades por Fecha")
            unidades_fecha = df.groupby("Fecha Formateada")["Total Unidades"].sum()
            st.line_chart(unidades_fecha)

    with c2:
        if "Descripción" in df.columns and "Total Unidades" in df.columns:
            st.subheader("Top 10 Artículos por Unidades")
            top_articulos = df.groupby("Descripción")["Total Unidades"].sum().nlargest(10)
            st.bar_chart(top_articulos)

    # Tabla con Datos
    st.subheader("📋 Registros Filtrados")
    st.dataframe(df, use_container_width=True)

except FileNotFoundError:
    st.error("⚠️ No se encontró el archivo 'movimientos_tiendas.parquet'.")
except Exception as e:
    st.error(f"Error procesando los datos: {e}")
