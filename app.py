import streamlit as st
import geopandas as gpd
import pandas as pd
import os
import zipfile
import tempfile
import fiona
import folium
from streamlit_folium import st_folium  # Necesitarás instalar la librería streamlit_folium

# Funciones
def listar_capas(gdb_path):
    capas = []
    try:
        with fiona.drivers():
            for layer in fiona.listlayers(gdb_path):
                capas.append(layer)
    except Exception as e:
        st.error(f"Error al leer las capas: {e}")
    return capas

def listar_campos(gdb_path, capa):
    try:
        gdf = gpd.read_file(gdb_path, layer=capa)
        return gdf.columns.tolist(), gdf
    except Exception as e:
        st.error(f"Error al leer los campos de la capa {capa}: {e}")
        return [], None

def exportar_a_excel(gdb_path, capa, output_file):
    gdf = gpd.read_file(gdb_path, layer=capa)
    df = pd.DataFrame(gdf)  # Convertir el GeoDataFrame a DataFrame
    df.to_excel(output_file, index=False)

def exportar_capas_a_excel(capas, gdb_path, output_file):
    with pd.ExcelWriter(output_file, engine='xlsxwriter') as writer:
        for capa in capas:
            gdf = gpd.read_file(gdb_path, layer=capa)
            df = pd.DataFrame(gdf)
            df.to_excel(writer, sheet_name=capa, index=False)

# Interfaz de Streamlit
st.title("Gestión de Geodatabases Online (GDB)")
st.subheader("Raul Bossa")
# Subir archivo GDB comprimido
uploaded_file = st.file_uploader("Cargue un archivo .zip que contenga la GDB", type=["zip"])

if uploaded_file is not None:
    # Crear un directorio temporal
    with tempfile.TemporaryDirectory() as tmpdir:
        zip_path = os.path.join(tmpdir, "gdb.zip")

        # Guardar el archivo subido como .zip
        with open(zip_path, "wb") as f:
            f.write(uploaded_file.getvalue())

        # Descomprimir el archivo .zip
        with zipfile.ZipFile(zip_path, "r") as zip_ref:
            zip_ref.extractall(tmpdir)

        # Buscar la carpeta GDB en el directorio temporal
        gdb_path = next(
            (os.path.join(tmpdir, d) for d in os.listdir(tmpdir) if d.endswith(".gdb")),
            None,
        )

        if gdb_path and os.path.isdir(gdb_path):
            st.success(f"GDB cargada correctamente: {gdb_path}")

            # Listar capas
            try:
                capas = listar_capas(gdb_path)
                if capas:
                    # Mostrar las capas disponibles
                    st.write("Capas disponibles en la GDB:")
                    st.write(capas)

                    # Opción para descargar la lista de capas en Excel
                    if st.button("Descargar lista de capas en Excel"):
                        output_file = "listado_de_capas.xlsx"
                        exportar_capas_a_excel(capas, gdb_path, output_file)

                        # Crear un botón de descarga
                        with open(output_file, "rb") as f:
                            st.download_button(
                                label="Descargar Excel",
                                data=f,
                                file_name=output_file,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )

                    # Seleccionar una capa
                    capa_seleccionada = st.selectbox("Seleccione una capa", capas)

                    if capa_seleccionada:
                        # Listar campos de la capa seleccionada y mostrar la tabla de atributos
                        campos, gdf = listar_campos(gdb_path, capa_seleccionada)
                        
                        if gdf is not None:
                            st.write(f"Campos en la capa '{capa_seleccionada}':")
                            st.write(campos)
                            
                            st.write(f"Tabla de atributos de la capa '{capa_seleccionada}':")
                            st.write(gdf)  # Mostrar la tabla de atributos completa (DataFrame)

                            # Selección del tipo de geometría para visualizar en el mapa
                            tipo_geometria = st.radio(
                                "Seleccione el tipo de geometría para visualizar en el mapa",
                                ("Punto", "Línea", "Polígono"),
                            )

                            # Botón para visualizar el mapa
                            mostrar_mapa = st.button("Mostrar Mapa")

                            if mostrar_mapa:
                                st.write(f"Mapa de la capa '{capa_seleccionada}':")
                                
                                # Crear un mapa con folium
                                map_center = [gdf.geometry.y.mean(), gdf.geometry.x.mean()] if tipo_geometria == 'Punto' else [gdf.geometry.centroid.y.mean(), gdf.geometry.centroid.x.mean()]
                                m = folium.Map(location=map_center, zoom_start=12)

                                # Verificar que las geometrías no están vacías
                                if gdf.geometry.isnull().all():
                                    st.error("La capa seleccionada no contiene geometrías válidas para mostrar en el mapa.")
                                else:
                                    # Agregar las geometrías de la capa al mapa según el tipo seleccionado
                                    if tipo_geometria == 'Punto':  # Si la geometría es de tipo Point
                                        st.write("Geometría tipo: Punto")
                                        for _, row in gdf.iterrows():
                                            folium.Marker([row['geometry'].y, row['geometry'].x]).add_to(m)
                                    elif tipo_geometria == 'Polígono':  # Para geometrías de tipo Polygon
                                        st.write("Geometría tipo: Polígono")
                                        folium.GeoJson(gdf).add_to(m)
                                    elif tipo_geometria == 'Línea':  # Para geometrías de tipo LineString
                                        st.write("Geometría tipo: Línea")
                                        folium.GeoJson(gdf).add_to(m)

                                    # Mostrar el mapa en Streamlit
                                    map_obj = st_folium(m, width=700)

                        # Exportar a Excel
                        if st.button("Exportar datos de la capa a Excel"):
                            output_file = "datos_exportados.xlsx"
                            exportar_a_excel(gdb_path, capa_seleccionada, output_file)
                            st.success(f"Datos exportados a {output_file}.")
                    
                    # Opción para descargar todas las tablas de atributos en un solo Excel
                    if st.button("Descargar todas las tablas de atributos en un solo Excel"):
                        output_file_all = "todas_las_tablas.xlsx"
                        exportar_capas_a_excel(capas, gdb_path, output_file_all)

                        # Crear un botón de descarga
                        with open(output_file_all, "rb") as f:
                            st.download_button(
                                label="Descargar todas las tablas en Excel",
                                data=f,
                                file_name=output_file_all,
                                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            )

                else:
                    st.error("No se encontraron capas en la GDB.")
            except Exception as e:
                st.error(f"Error al procesar la GDB: {e}")
        else:
            st.error("No se encontró una carpeta .gdb válida en el archivo .zip.")
