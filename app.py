import streamlit as st
import pandas as pd

st.set_page_config(page_title="Tablero de Movimientos", layout="wide")
st.title("📦 Monitoreo de Preparación y Movimientos (Mov. 220)")

@st.cache_data
def cargar_datos():
    # Parquet carga de forma instantánea y pesa una fracción del CSV
    return pd.read_parquet("movimientos_tiendas.parquet")

try:
    df = cargar_datos()

    st.sidebar.header("🔍 Filtros de Búsqueda")
    
    if "BDALM" in df.columns:
        almacenes = sorted(df["BDALM"].dropna().unique())
        almacen_sel = st.sidebar.multiselect("Almacén (BDALM):", almacenes, default=almacenes)
        df = df[df["BDALM"].isin(almacen_sel)]

    col_tienda = "TIENDA_CALCULADA" if "TIENDA_CALCULADA" in df.columns else ("TIEND" if "TIEND" in df.columns else None)
    if col_tienda and col_tienda in df.columns:
        tiendas = sorted(df[col_tienda].dropna().unique())
        tienda_sel = st.sidebar.multiselect("Tienda:", tiendas, default=tiendas)
        df = df[df[col_tienda].isin(tienda_sel)]

    col1, col2, col3 = st.columns(3)
    col1.metric("Total Registros", f"{len(df):,}")
    
    col_unidades = "BDTUS" if "BDTUS" in df.columns else ("PDCAN" if "PDCAN" in df.columns else None)
    if col_unidades:
        col2.metric("Total Unidades", f"{int(df[col_unidades].sum()):,}")
    
    if "BDCOS" in df.columns:
        col3.metric("Costo Total", f"")

    st.markdown("---")

    c1, c2 = st.columns(2)
    with c1:
        if "BDALM" in df.columns and col_unidades:
            st.subheader("Unidades por Almacén")
            st.bar_chart(df.groupby("BDALM")[col_unidades].sum())

    with c2:
        if "BDART" in df.columns and col_unidades:
            st.subheader("Top 10 Artículos")
            st.bar_chart(df.groupby("BDART")[col_unidades].sum().nlargest(10))

    st.subheader("📋 Registros Filtrados")
    st.dataframe(df, use_container_width=True)

except FileNotFoundError:
    st.error("⚠️ No se encontró el archivo 'movimientos_tiendas.parquet'.")
except Exception as e:
    st.error(f"Error procesando los datos: {e}")
