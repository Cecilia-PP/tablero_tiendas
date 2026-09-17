import streamlit as st
import pandas as pd

# Configuración de pantalla ancha
st.set_page_config(page_title="Tablero Movimientos 220", layout="wide")
st.title("📦 Monitoreo de Preparación y Movimientos (Mov. 220)")

# Carga de datos
@st.cache_data
def cargar_datos():
    df = pd.read_parquet("movimientos_tiendas.parquet")
    
    # Limpieza de espacios en blanco en los nombres de las columnas
    df.columns = df.columns.str.strip()
    
    # Convertir 'Fecha del Movimiento' (Formato YYYYMMDD ej: 20260901) a fecha legible
    if "Fecha del Movimiento" in df.columns:
        df["Fecha_DT"] = pd.to_datetime(df["Fecha del Movimiento"].astype(str), format="%Y%m%d", errors="coerce")
    
    # Asegurar que los valores numéricos se interpreten correctamente
    for col in ["Total Unidades", "Precio medio de coste", "Total formatos del mvto", "Unid/Kgs grabados"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            
    return df

try:
    df = cargar_datos()

    # Sidebar: Filtros de Búsqueda
    st.sidebar.header("🔍 Filtros de Búsqueda")
    
    # 1. Filtro por Almacén
    if "Almacen" in df.columns:
        almacenes = sorted([str(x) for x in df["Almacen"].dropna().unique()])
        almacen_sel = st.sidebar.multiselect("Almacén:", almacenes, default=almacenes)
        df = df[df["Almacen"].astype(str).isin(almacen_sel)]

    # 2. Filtro por Tienda
    if "Tienda" in df.columns:
        tiendas = sorted([str(x) for x in df["Tienda"].dropna().unique()])
        tienda_sel = st.sidebar.multiselect("Tienda:", tiendas, default=tiendas)
        df = df[df["Tienda"].astype(str).isin(tienda_sel)]

    # 3. Filtro por Área
    if "AREA" in df.columns:
        areas = sorted([str(x) for x in df["AREA"].dropna().unique()])
        area_sel = st.sidebar.multiselect("Área:", areas, default=areas)
        df = df[df["AREA"].astype(str).isin(area_sel)]

    # Tarjetas de Métricas Principales (KPIs)
    col1, col2, col3, col4 = st.columns(4)
    
    col1.metric("Total Registros", f"{len(df):,}")
    
    if "Total Unidades" in df.columns:
        col2.metric("Total Unidades Moviéndose", f"{int(df['Total Unidades'].sum()):,}")
        
    if "Tienda" in df.columns:
        col3.metric("Tiendas Impactadas", f"{df['Tienda'].nunique():,}")
        
    if "Precio medio de coste" in df.columns:
        col4.metric("Costo Total Est.", f"")

    st.markdown("---")

    # Gráficos
    c1, c2 = st.columns(2)
    with c1:
        if "Tienda" in df.columns and "Total Unidades" in df.columns:
            st.subheader("Top 10 Tiendas por Unidades")
            top_tiendas = df.groupby("Tienda")["Total Unidades"].sum().nlargest(10)
            st.bar_chart(top_tiendas)

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
