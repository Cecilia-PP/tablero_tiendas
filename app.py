import streamlit as st
import pandas as pd

# Configuración de pantalla ancha y nuevo título
st.set_page_config(page_title="Conformidad de entregas", layout="wide")
st.title("📦 Conformidad de entregas")

# Carga de datos
@st.cache_data
def cargar_datos():
    df = pd.read_parquet("movimientos_tiendas.parquet")
    
    # Limpieza de espacios en blanco en los nombres de las columnas
    df.columns = df.columns.str.strip()
    
    # Procesamiento y creación de campos de Fecha
    if "Fecha del Movimiento" in df.columns:
        df["Fecha_DT"] = pd.to_datetime(df["Fecha del Movimiento"].astype(str), format="%Y%m%d", errors="coerce")
        df["Fecha Formateada"] = df["Fecha_DT"].dt.strftime("%d/%m/%Y")
        df["Año"] = df["Fecha_DT"].dt.year.fillna(0).astype(int)
        df["Mes"] = df["Fecha_DT"].dt.month.fillna(0).astype(int)
        df["Día"] = df["Fecha_DT"].dt.day.fillna(0).astype(int)
    
    # Mapeo del campo: Estado Rectificación
    if "Estado" in df.columns:
        mapa_estados = {
            "M": "Confirmada",
            "R": "Rechazada",
            "P": "Pendiente"
        }
        df["Estado Rectificación"] = df["Estado"].astype(str).str.upper().map(mapa_estados).fillna(df["Estado"])
    
    # Asegurar tipos numéricos para métricas
    for col in ["Total Unidades", "Precio medio de coste", "Total formatos del mvto", "Unid/Kgs grabados"]:
        if col in df.columns:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)
            
    return df

try:
    df = cargar_datos()

    # Sidebar: Filtros de Búsqueda
    st.sidebar.header("🔍 Filtros de Búsqueda")
    
    # 1. Filtro por Año
    if "Año" in df.columns and df["Año"].max() > 0:
        anios = sorted([int(x) for x in df["Año"].unique() if x > 0], reverse=True)
        anio_sel = st.sidebar.multiselect("Año:", anios, default=anios)
        df = df[df["Año"].isin(anio_sel)]

    # 2. Filtro por Mes
    if "Mes" in df.columns and df["Mes"].max() > 0:
        meses = sorted([int(x) for x in df["Mes"].unique() if x > 0])
        mes_sel = st.sidebar.multiselect("Mes:", meses, default=meses)
        df = df[df["Mes"].isin(mes_sel)]

    # 3. Filtro por Estado Rectificación
    if "Estado Rectificación" in df.columns:
        estados = sorted([str(x) for x in df["Estado Rectificación"].dropna().unique()])
        estado_sel = st.sidebar.multiselect("Estado Rectificación:", estados, default=estados)
        df = df[df["Estado Rectificación"].astype(str).isin(estado_sel)]

    # 4. Filtro por Almacén
    if "Almacen" in df.columns:
        almacenes = sorted([str(x) for x in df["Almacen"].dropna().unique()])
        almacen_sel = st.sidebar.multiselect("Almacén:", almacenes, default=almacenes)
        df = df[df["Almacen"].astype(str).isin(almacen_sel)]

    # 5. Filtro por Tienda Destino
    if "Tienda" in df.columns:
        tiendas = sorted([str(x) for x in df["Tienda"].dropna().unique()])
        tienda_sel = st.sidebar.multiselect("Tienda Destino:", tiendas, default=tiendas)
        df = df[df["Tienda"].astype(str).isin(tienda_sel)]

    # Tarjetas de Métricas Principales (KPIs)
    col1, col2, col3, col4, col5 = st.columns(5)
    
    col1.metric("Total Registros", f"{len(df):,}")
    
    if "Total Unidades" in df.columns:
        col2.metric("Total Unidades", f"{int(df['Total Unidades'].sum()):,}")
        
    if "Estado Rectificación" in df.columns:
        confirmadas = len(df[df["Estado Rectificación"] == "Confirmada"])
        col3.metric("Confirmadas (M)", f"{confirmadas:,}")
        
        pendientes = len(df[df["Estado Rectificación"] == "Pendiente"])
        col4.metric("Pendientes (P)", f"{pendientes:,}")
        
    if "Precio medio de coste" in df.columns:
        col5.metric("Costo Total Est.", f"")

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
