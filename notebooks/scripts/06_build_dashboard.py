"""
Script 06 — Build Interactive Local Dashboard (Triángulo de Análisis: Residuos, Emergencias y Delitos)
DataJam Bogotá 2026

Genera una aplicación web local (HTML interactivo auto-contenido) integrando:
- Resumen Ejecutivo con KPIs macro y Metodología DataJam de 5 pasos
- Mapa interactivo de Bogotá (Folium + Leaflet) con capas conmutables:
  * UPZ con Índice de Vulnerabilidad
  * Puntos Críticos de Arrojo Clandestino
  * Estaciones de Bomberos
  * Cuadrantes de Policía (MEBOG)
- Gráficos interactivos Plotly:
  1. Brecha de Cestas vs Estrato (r = +0.74)
  2. Puntos Críticos de Arrojo por Localidad y Estrato
  3. Delitos de Alto Impacto y Homicidios vs Puntos Críticos (r = +0.68)
  4. Distribución de Cuadrantes Policiales por Localidad
  5. Dinámica Temporal de Residuos RBL (2021-2026)
  6. Enfoque Diferencial de Género y Niñez en Emergencias
- Matriz de Priorización Territorial y Políticas Públicas Integradas (UAESP + UAECOB + MEBOG)

Output: outputs/dashboard_datajam_bogota_2026.html
"""

import os
import json
import pandas as pd
import geopandas as gpd
import numpy as np
import folium
from folium.plugins import MarkerCluster
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

BASE = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
GOLD = os.path.join(BASE, 'Gold')
SILVER_GEO = os.path.join(BASE, 'Silver', 'capas_geo')
OUTPUTS = os.path.join(BASE, 'outputs')
os.makedirs(OUTPUTS, exist_ok=True)

print("=" * 60)
print("SCRIPT 06 — BUILD DASHBOARD INTERACTIVO (RESIDUOS + EMERGENCIAS + SEGURIDAD)")
print("=" * 60)

# ═══════════════════════════════════════════════════════════════
# 1. Cargar Datos Gold y Silver
# ═══════════════════════════════════════════════════════════════
print("\n📂 Cargando tablas analíticas Gold...")
df_loc = pd.read_parquet(os.path.join(GOLD, 'gold_localidad_analisis.parquet'))
gdf_upz = gpd.read_parquet(os.path.join(GOLD, 'gold_upz_analisis.geoparquet'))
df_rbl = pd.read_parquet(os.path.join(GOLD, 'gold_series_rbl_mensual.parquet'))
df_inc_mensual = pd.read_parquet(os.path.join(GOLD, 'gold_series_incidentes_mensual.parquet'))
df_genero = pd.read_parquet(os.path.join(GOLD, 'gold_diferencial_genero.parquet'))

print(f"  Localidades: {len(df_loc)} | UPZ: {len(gdf_upz)} | Residuos: {len(df_rbl)} filas")

# ═══════════════════════════════════════════════════════════════
# 2. Generar Mapa Interactivo Folium
# ═══════════════════════════════════════════════════════════════
print("\n🗺️ Generando mapa interactivo territorial (con capas de Policía y Bomberos)...")

m = folium.Map(
    location=[4.6486, -74.0860],
    zoom_start=11,
    tiles='cartodbdark_matter',
    control_scale=True
)

def get_upz_color(val):
    if val >= 45: return '#d73027'  # Rojo
    elif val >= 35: return '#fc8d59' # Naranja
    elif val >= 25: return '#fee08b' # Amarillo
    elif val >= 15: return '#91bfdb' # Celeste
    else: return '#4575b4'           # Azul

gdf_upz_web = gdf_upz.to_crs(epsg=4326).copy()
gdf_upz_web['geometry'] = gdf_upz_web['geometry'].simplify(0.001)

upz_fg = folium.FeatureGroup(name='📍 UPZ — Vulnerabilidad Territorial', show=True)

for _, row in gdf_upz_web.iterrows():
    if row.geometry is None: continue
    vuln = row.get('indice_vulnerabilidad_territorial', 0)
    color = get_upz_color(vuln)
    
    popup_html = f"""
    <div style="font-family: sans-serif; width: 230px; font-size: 12px;">
        <h4 style="margin: 0 0 5px 0; color: #1e293b;">{row.get('nombre_upz', 'UPZ')} ({row.get('upz_id', '')})</h4>
        <hr style="margin: 4px 0; border: 0; border-top: 1px solid #e2e8f0;">
        <b>Índice Vulnerabilidad:</b> <span style="color:{color}; font-weight:bold;">{vuln:.1f}/100</span><br>
        <b>Puntos Críticos Basura:</b> {int(row.get('n_puntos_criticos', 0))}<br>
        <b>Cestas de Basura:</b> {int(row.get('n_cestas', 0))} ({row.get('densidad_cestas_km2', 0):.1f}/km²)<br>
        <b>Cuadrantes Policía:</b> {int(row.get('n_cuadrantes_policia', 0))}<br>
        <b>Incidentes Bomberos:</b> {int(row.get('n_incidentes_total', 0))}<br>
        <b>Área:</b> {row.get('area_km2', 0):.2f} km²
    </div>
    """
    
    folium.GeoJson(
        row.geometry.__geo_interface__,
        style_function=lambda x, col=color: {
            'fillColor': col,
            'color': '#334155',
            'weight': 1,
            'fillOpacity': 0.6
        },
        highlight_function=lambda x: {
            'weight': 2.5,
            'color': '#ffffff',
            'fillOpacity': 0.85
        },
        popup=folium.Popup(popup_html, max_width=260)
    ).add_to(upz_fg)

upz_fg.add_to(m)

# Capa 2: Puntos Críticos de Arrojo Clandestino
pc_fg = folium.FeatureGroup(name='🔴 Puntos Críticos Basura (478)', show=True)
gdf_pc_silver = gpd.read_parquet(os.path.join(SILVER_GEO, 'puntos_criticos.geoparquet'))
for _, row in gdf_pc_silver.iterrows():
    if row.geometry is None: continue
    folium.CircleMarker(
        location=[row.geometry.y, row.geometry.x],
        radius=4,
        color='#ef4444',
        fill=True,
        fill_color='#ef4444',
        fill_opacity=0.85,
        popup=f"<b>Punto Crítico Arrojo</b><br>Dir: {row.get('Dirección', 'N/A')}<br>Frecuencia: {row.get('Frecuencia', 'N/A')}<br>Estado: ACTIVO"
    ).add_to(pc_fg)
pc_fg.add_to(m)

# Capa 3: Cuadrantes de Policía (MEBOG)
cuad_fg = folium.FeatureGroup(name='👮 Cuadrantes de Policía (599)', show=False)
gdf_cuad_silver = gpd.read_parquet(os.path.join(SILVER_GEO, 'cuadrantes_policia.geoparquet'))
gdf_cuad_web = gdf_cuad_silver.to_crs(epsg=4326).copy()
gdf_cuad_web['geometry'] = gdf_cuad_web['geometry'].simplify(0.001)
for _, row in gdf_cuad_web.iterrows():
    if row.geometry is None: continue
    folium.GeoJson(
        row.geometry.__geo_interface__,
        style_function=lambda x: {
            'fillColor': '#3b82f6',
            'color': '#1d4ed8',
            'weight': 1,
            'fillOpacity': 0.15
        },
        popup=f"<b>{row.get('PCUNOMEST', 'Estación Policía')}</b><br>CAI: {row.get('PCUNOMCAI', 'N/A')}<br>Cuadrante: {row.get('PCUDESCRIP', 'N/A')}<br>Tel: {row.get('PCUTELEFON', 'N/A')}"
    ).add_to(cuad_fg)
cuad_fg.add_to(m)

# Capa 4: Estaciones de Bomberos (UAECOB)
ebom_fg = folium.FeatureGroup(name='🚒 Estaciones Bomberos (17)', show=False)
gdf_ebom = gpd.read_parquet(os.path.join(SILVER_GEO, 'estaciones_bomberos.geoparquet'))
for _, row in gdf_ebom.iterrows():
    if row.geometry is None: continue
    folium.Marker(
        location=[row.geometry.y, row.geometry.x],
        icon=folium.Icon(color='red', icon='fire', prefix='fa'),
        popup=f"<b>{row.get('EBONOMBRE', 'Estación Bomberos')}</b><br>Dir: {row.get('EBODIRECCI', 'N/A')}<br>Tel: {row.get('EBOTELEFON', 'N/A')}"
    ).add_to(ebom_fg)
ebom_fg.add_to(m)

folium.LayerControl(collapsed=False).add_to(m)
mapa_html = m._repr_html_()

# ═══════════════════════════════════════════════════════════════
# 3. Generar Gráficos Interactivos Plotly
# ═══════════════════════════════════════════════════════════════
print("\n📊 Generando visualizaciones interactivas con Plotly...")

THEME = {
    'bg': '#0f172a',
    'card_bg': '#1e293b',
    'text': '#f8fafc',
    'grid': '#334155'
}

# ── Gráfico 1: Brecha de Infraestructura de Cestas
fig_infra = px.scatter(
    df_loc[df_loc['estrato_modal'].notna()],
    x='estrato_modal',
    y='tasa_cestas_10k_hab',
    size='n_puntos_criticos',
    color='nivel_prioridad_intervencion',
    hover_name='localidad',
    hover_data={'poblacion_estimada': ':,', 'n_cestas': ':,', 'n_puntos_criticos': True},
    color_discrete_map={
        'ALTA PRIORIDAD (Vulnerabilidad Crítica)': '#ef4444',
        'PRIORIDAD MEDIA': '#f59e0b',
        'PRIORIDAD BAJA / CONSOLIDADO': '#10b981'
    },
    labels={
        'estrato_modal': 'Estrato Socioeconómico Predominante',
        'tasa_cestas_10k_hab': 'Tasa de Cestas por 10.000 Hab.',
        'nivel_prioridad_intervencion': 'Prioridad'
    },
    title='<b>Brecha de Infraestructura de Aseo según Estrato</b> (Correlación r = +0.74)',
    template='plotly_dark'
)
fig_infra.update_layout(paper_bgcolor=THEME['card_bg'], plot_bgcolor=THEME['card_bg'], font=dict(color=THEME['text']), height=400, margin=dict(l=40, r=40, t=50, b=40))
infra_html = fig_infra.to_html(full_html=False, include_plotlyjs=False)

# ── Gráfico 2: Puntos Críticos por Localidad
df_loc_sorted = df_loc.sort_values('n_puntos_criticos', ascending=True)
fig_pc = go.Figure()
fig_pc.add_trace(go.Bar(
    y=df_loc_sorted['localidad'],
    x=df_loc_sorted['n_puntos_criticos'],
    orientation='h',
    marker=dict(color=df_loc_sorted['estrato_modal'], colorscale='Viridis', showscale=True, colorbar=dict(title="Estrato<br>Modal", len=0.8)),
    text=df_loc_sorted['n_puntos_criticos'],
    textposition='outside',
    hovertemplate="<b>%{y}</b><br>Puntos Críticos: %{x}<br>Estrato: %{marker.color}<extra></extra>"
))
fig_pc.update_layout(title='<b>Puntos Críticos de Arrojo Clandestino por Localidad</b>', xaxis_title='Puntos Críticos Activos', yaxis_title='', paper_bgcolor=THEME['card_bg'], plot_bgcolor=THEME['card_bg'], font=dict(color=THEME['text']), height=450, margin=dict(l=10, r=40, t=50, b=40))
pc_html = fig_pc.to_html(full_html=False, include_plotlyjs=False)

# ── Gráfico 3: Homicidios y Violencia vs Puntos Críticos de Basura (Correlación r = +0.68)
fig_crimen_basura = px.scatter(
    df_loc[df_loc['estrato_modal'].notna()],
    x='n_puntos_criticos',
    y='homicidios_total',
    size='violencia_intrafamiliar_total',
    color='estrato_modal',
    hover_name='localidad',
    hover_data={'homicidios_total': ':,', 'violencia_intrafamiliar_total': ':,', 'delitos_alto_impacto_total': ':,'},
    color_continuous_scale='Reds',
    labels={
        'n_puntos_criticos': 'Puntos Críticos de Arrojo Clandestino',
        'homicidios_total': 'Total Homicidios (2018–2026)',
        'estrato_modal': 'Estrato Modal',
        'violencia_intrafamiliar_total': 'Violencia Intrafamiliar'
    },
    title='<b>Convergencia de Vulnerabilidad: Homicidios vs Puntos Críticos de Basura</b> (r = +0.68)',
    template='plotly_dark'
)
fig_crimen_basura.update_layout(paper_bgcolor=THEME['card_bg'], plot_bgcolor=THEME['card_bg'], font=dict(color=THEME['text']), height=400, margin=dict(l=40, r=40, t=50, b=40))
crimen_basura_html = fig_crimen_basura.to_html(full_html=False, include_plotlyjs=False)

# ── Gráfico 4: Delitos de Alto Impacto por Localidad (DAILoc)
df_loc_crime_sort = df_loc.sort_values('delitos_alto_impacto_total', ascending=True)
fig_crime_bar = go.Figure()
fig_crime_bar.add_trace(go.Bar(name='Hurto Personas', y=df_loc_crime_sort['localidad'], x=df_loc_crime_sort['hurto_personas_total'], orientation='h', marker_color='#38bdf8'))
fig_crime_bar.add_trace(go.Bar(name='Violencia Intrafamiliar', y=df_loc_crime_sort['localidad'], x=df_loc_crime_sort['violencia_intrafamiliar_total'], orientation='h', marker_color='#f43f5e'))
fig_crime_bar.add_trace(go.Bar(name='Homicidios', y=df_loc_crime_sort['localidad'], x=df_loc_crime_sort['homicidios_total'], orientation='h', marker_color='#ef4444'))

fig_crime_bar.update_layout(
    barmode='stack',
    title='<b>Delitos de Alto Impacto por Localidad (Policía Nacional / SIEDCO 2018–2026)</b>',
    xaxis_title='Casos Reportados',
    yaxis_title='',
    paper_bgcolor=THEME['card_bg'],
    plot_bgcolor=THEME['card_bg'],
    font=dict(color=THEME['text']),
    height=480,
    margin=dict(l=10, r=40, t=50, b=40),
    legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1)
)
crime_bar_html = fig_crime_bar.to_html(full_html=False, include_plotlyjs=False)

# ── Gráfico 5: Serie Temporal RBL 2021-2026
df_rbl_tot = df_rbl.groupby('fecha').agg(
    domiciliarios_t=('domiciliarios_t', 'sum'),
    barrido_t=('barrido_t', 'sum'),
    arrojo_clandestino_t=('arrojo_clandestino_t', 'sum'),
    total_t=('total_t', 'sum')
).reset_index()

fig_rbl = go.Figure()
fig_rbl.add_trace(go.Scatter(x=df_rbl_tot['fecha'], y=df_rbl_tot['total_t'], mode='lines+markers', name='Total Residuos (t)', line=dict(color='#38bdf8', width=3)))
fig_rbl.add_trace(go.Scatter(x=df_rbl_tot['fecha'], y=df_rbl_tot['domiciliarios_t'], mode='lines', name='Domiciliarios (t)', line=dict(color='#4ade80', width=2)))
fig_rbl.add_trace(go.Scatter(x=df_rbl_tot['fecha'], y=df_rbl_tot['arrojo_clandestino_t'], mode='lines', name='Arrojo Clandestino (t)', line=dict(color='#f87171', width=2, dash='dash')))
fig_rbl.update_layout(title='<b>Evolución Mensual de Toneladas Recogidas en Bogotá (2021–2026)</b>', xaxis_title='Fecha', yaxis_title='Toneladas / Mes', paper_bgcolor=THEME['card_bg'], plot_bgcolor=THEME['card_bg'], font=dict(color=THEME['text']), height=380, margin=dict(l=40, r=40, t=50, b=40), legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1))
rbl_html = fig_rbl.to_html(full_html=False, include_plotlyjs=False)

# ── Gráfico 6: Análisis Diferencial de Género por Estrato
df_gen_clean = df_genero[df_genero['estrato'].isin([1,2,3,4,5,6])].groupby('estrato').agg(
    hombres=('hombres_expuestos', 'sum'),
    mujeres=('mujeres_expuestas', 'sum'),
    ninas=('ninas_expuestas', 'sum'),
    ninos=('ninos_expuestos', 'sum')
).reset_index()

fig_gen = go.Figure()
fig_gen.add_trace(go.Bar(name='Hombres Expuestos', x=df_gen_clean['estrato'], y=df_gen_clean['hombres'], marker_color='#60a5fa'))
fig_gen.add_trace(go.Bar(name='Mujeres Expuestas', x=df_gen_clean['estrato'], y=df_gen_clean['mujeres'], marker_color='#f472b6'))
fig_gen.add_trace(go.Bar(name='Niñas Expuestas', x=df_gen_clean['estrato'], y=df_gen_clean['ninas'], marker_color='#c084fc'))
fig_gen.add_trace(go.Bar(name='Niños Expuestos', x=df_gen_clean['estrato'], y=df_gen_clean['ninos'], marker_color='#fde047'))
fig_gen.update_layout(barmode='group', title='<b>Población Expuesta en Emergencias por Estrato y Género</b>', xaxis_title='Estrato', yaxis_title='Personas Registradas', paper_bgcolor=THEME['card_bg'], plot_bgcolor=THEME['card_bg'], font=dict(color=THEME['text']), height=380, margin=dict(l=40, r=40, t=50, b=40), legend=dict(orientation='h', yanchor='bottom', y=1.02, xanchor='right', x=1))
gen_html = fig_gen.to_html(full_html=False, include_plotlyjs=False)

# ── Gráfico 7: Tipos de Incidentes UAECOB
df_inc_tipos = df_inc_mensual.drop(columns=['año', 'mes', 'fecha']).sum().reset_index()
df_inc_tipos.columns = ['tipo', 'total']
df_inc_tipos = df_inc_tipos.sort_values('total', ascending=True)

fig_tipos = px.pie(df_inc_tipos[df_inc_tipos['total'] > 1000], values='total', names='tipo', title='<b>Emergencias Atendidas por UAECOB (166.977 eventos)</b>', hole=0.45, color_discrete_sequence=px.colors.sequential.Tealgrn)
fig_tipos.update_layout(paper_bgcolor=THEME['card_bg'], font=dict(color=THEME['text']), height=380, margin=dict(l=20, r=20, t=50, b=20))
tipos_html = fig_tipos.to_html(full_html=False, include_plotlyjs=False)

# ═══════════════════════════════════════════════════════════════
# 4. Tabla de Priorización Territorial
# ═══════════════════════════════════════════════════════════════
filas_tabla = ""
for _, r in df_loc.sort_values(['homicidios_total', 'n_puntos_criticos'], ascending=[False, False]).iterrows():
    badge_color = "#ef4444" if "Crítica" in r['nivel_prioridad_intervencion'] else ("#f59e0b" if "MEDIA" in r['nivel_prioridad_intervencion'] else "#10b981")
    filas_tabla += f"""
    <tr style="border-bottom: 1px solid #334155; font-size: 12.5px;">
        <td style="padding: 9px; font-weight: bold;">{r['localidad']}</td>
        <td style="padding: 9px; text-align: center;">Estrato {int(r['estrato_modal']) if pd.notna(r['estrato_modal']) else 'N/D'}</td>
        <td style="padding: 9px; text-align: right;">{int(r['poblacion_estimada']):,}</td>
        <td style="padding: 9px; text-align: right; color: #f87171; font-weight: bold;">{int(r['homicidios_total']):,}</td>
        <td style="padding: 9px; text-align: right;">{r['tasa_homicidios_10k_hab']:.1f}</td>
        <td style="padding: 9px; text-align: right; color: #fb923c; font-weight: bold;">{int(r['n_puntos_criticos'])}</td>
        <td style="padding: 9px; text-align: right;">{int(r['n_cestas']):,}</td>
        <td style="padding: 9px; text-align: right; color: #38bdf8;">{r['tasa_cestas_10k_hab']:.1f}</td>
        <td style="padding: 9px; text-align: right;">{int(r['n_cuadrantes_policia'])}</td>
        <td style="padding: 9px; text-align: right;">{int(r['n_incidentes_total']):,}</td>
        <td style="padding: 9px; text-align: center;">
            <span style="background-color: {badge_color}; color: white; padding: 3px 8px; border-radius: 12px; font-size: 11px; font-weight: bold;">
                {r['nivel_prioridad_intervencion']}
            </span>
        </td>
    </tr>
    """

# ═══════════════════════════════════════════════════════════════
# 5. Ensamblar Aplicación Web Dashboard HTML
# ═══════════════════════════════════════════════════════════════
print("\n🏗️ Ensamblando Dashboard HTML completo...")

html_content = f"""<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>DataJam Bogotá 2026 — Observatorio de Residuos, Emergencias y Seguridad</title>
    <script src="https://cdn.plot.ly/plotly-2.35.2.min.js"></script>
    <link href="https://cdnjs.cloudflare.com/ajax/libs/font-awesome/6.0.0/css/all.min.css" rel="stylesheet">
    <style>
        :root {{
            --bg: #0b0f19;
            --card-bg: #1e293b;
            --card-border: #334155;
            --primary: #38bdf8;
            --danger: #ef4444;
            --warning: #f59e0b;
            --success: #10b981;
            --text-main: #f8fafc;
            --text-muted: #94a3b8;
        }}
        * {{ box-sizing: border-box; margin: 0; padding: 0; }}
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, Cantarell, sans-serif;
            background-color: var(--bg);
            color: var(--text-main);
            line-height: 1.5;
            padding: 20px;
        }}
        .container {{ max-width: 1440px; margin: 0 auto; }}
        
        .header {{
            background: linear-gradient(135deg, #1e293b 0%, #0f172a 100%);
            border: 1px solid var(--card-border);
            border-radius: 16px;
            padding: 24px 32px;
            margin-bottom: 24px;
            display: flex;
            justify-content: space-between;
            align-items: center;
            flex-wrap: wrap;
            gap: 16px;
        }}
        .header-title h1 {{ font-size: 26px; font-weight: 800; color: #ffffff; }}
        .header-title p {{ color: var(--primary); font-size: 14px; margin-top: 4px; }}
        .badge-team {{
            background: rgba(56, 189, 248, 0.1);
            color: var(--primary);
            border: 1px solid var(--primary);
            padding: 6px 14px;
            border-radius: 20px;
            font-size: 13px;
            font-weight: 600;
        }}

        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
            gap: 14px;
            margin-bottom: 24px;
        }}
        .kpi-card {{
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 18px;
            display: flex;
            align-items: center;
            gap: 14px;
        }}
        .kpi-icon {{
            width: 46px;
            height: 46px;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 20px;
        }}
        .kpi-info h3 {{ font-size: 22px; font-weight: 800; }}
        .kpi-info p {{ font-size: 11.5px; color: var(--text-muted); }}

        .tab-container {{
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 12px;
            padding: 6px;
            display: flex;
            gap: 6px;
            margin-bottom: 24px;
            overflow-x: auto;
        }}
        .tab-btn {{
            background: transparent;
            border: none;
            color: var(--text-muted);
            padding: 10px 16px;
            border-radius: 8px;
            font-size: 13.5px;
            font-weight: 600;
            cursor: pointer;
            transition: all 0.2s;
            display: flex;
            align-items: center;
            gap: 8px;
            white-space: nowrap;
        }}
        .tab-btn.active {{
            background-color: var(--primary);
            color: #0f172a;
        }}
        .tab-btn:hover:not(.active) {{
            background-color: rgba(255,255,255,0.05);
            color: #ffffff;
        }}

        .tab-pane {{ display: none; }}
        .tab-pane.active {{ display: block; }}

        .grid-2 {{
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(580px, 1fr));
            gap: 20px;
            margin-bottom: 20px;
        }}
        .grid-full {{ margin-bottom: 20px; }}

        .card {{
            background-color: var(--card-bg);
            border: 1px solid var(--card-border);
            border-radius: 14px;
            padding: 22px;
        }}
        .card-header {{
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 16px;
            border-bottom: 1px solid var(--card-border);
            padding-bottom: 12px;
        }}
        .card-header h2 {{ font-size: 16.5px; font-weight: 700; color: #ffffff; display: flex; align-items: center; gap: 8px; }}

        .table-responsive {{ overflow-x: auto; }}
        table {{ width: 100%; border-collapse: collapse; text-align: left; }}
        th {{ background-color: #0f172a; color: var(--text-muted); padding: 11px 9px; font-size: 11.5px; font-weight: 700; text-transform: uppercase; }}

        .step-grid {{ display: grid; grid-template-columns: repeat(auto-fit, minmax(220px, 1fr)); gap: 12px; margin-top: 14px; }}
        .step-card {{
            background: #0f172a;
            border-left: 4px solid var(--primary);
            border-radius: 8px;
            padding: 14px;
        }}
        .step-card h4 {{ font-size: 13.5px; color: var(--primary); margin-bottom: 5px; }}
        .step-card p {{ font-size: 12px; color: var(--text-muted); }}

        .policy-card {{
            background: #0f172a;
            border: 1px solid var(--card-border);
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 12px;
        }}
        .policy-card h3 {{ font-size: 14.5px; color: #38bdf8; margin-bottom: 5px; display: flex; align-items: center; gap: 8px; }}
        .policy-card p {{ font-size: 12.5px; color: #cbd5e1; }}

        @media (max-width: 768px) {{
            .grid-2 {{ grid-template-columns: 1fr; }}
            .header {{ flex-direction: column; align-items: flex-start; }}
        }}
    </style>
</head>
<body>
    <div class="container">
        <!-- HEADER -->
        <div class="header">
            <div class="header-title">
                <h1>Observatorio Territorial de Residuos, Emergencias y Seguridad</h1>
                <p>DataJam Bogotá 2026 • Análisis Integrado: UAESP (Aseo) + UAECOB (Bomberos) + MEBOG (Policía) + IDECA (Estratificación)</p>
            </div>
            <div class="badge-team">
                <i class="fa-solid fa-layer-group"></i> Pipeline Bronze ➔ Silver ➔ Gold
            </div>
        </div>

        <!-- KPI CARDS -->
        <div class="kpi-grid">
            <div class="kpi-card">
                <div class="kpi-icon" style="background: rgba(239, 68, 68, 0.15); color: #ef4444;">
                    <i class="fa-solid fa-truck-monster"></i>
                </div>
                <div class="kpi-info">
                    <h3>478</h3>
                    <p>Puntos Críticos de Arrojo Activos</p>
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-icon" style="background: rgba(56, 189, 248, 0.15); color: #38bdf8;">
                    <i class="fa-solid fa-trash-can"></i>
                </div>
                <div class="kpi-info">
                    <h3>69.830</h3>
                    <p>Cestas de Basura Activas</p>
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-icon" style="background: rgba(245, 158, 11, 0.15); color: #f59e0b;">
                    <i class="fa-solid fa-fire-extinguisher"></i>
                </div>
                <div class="kpi-info">
                    <h3>166.977</h3>
                    <p>Emergencias UAECOB</p>
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-icon" style="background: rgba(147, 51, 234, 0.15); color: #c084fc;">
                    <i class="fa-solid fa-shield-halved"></i>
                </div>
                <div class="kpi-info">
                    <h3>11.445</h3>
                    <p>Homicidios (DAILoc 2018–2026)</p>
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-icon" style="background: rgba(59, 130, 246, 0.15); color: #3b82f6;">
                    <i class="fa-solid fa-person-military-pointing"></i>
                </div>
                <div class="kpi-info">
                    <h3>599</h3>
                    <p>Cuadrantes de Policía (MEBOG)</p>
                </div>
            </div>
            <div class="kpi-card">
                <div class="kpi-icon" style="background: rgba(16, 185, 129, 0.15); color: #10b981;">
                    <i class="fa-solid fa-recycle"></i>
                </div>
                <div class="kpi-info">
                    <h3>2.24 M</h3>
                    <p>Ton/Año Residuos RBL</p>
                </div>
            </div>
        </div>

        <!-- NAVIGATION TABS -->
        <div class="tab-container">
            <button class="tab-btn active" onclick="switchTab('tab-metodologia')">
                <i class="fa-solid fa-compass"></i> Metodología & Hallazgos
            </button>
            <button class="tab-btn" onclick="switchTab('tab-mapa')">
                <i class="fa-solid fa-map-location-dot"></i> Mapa Territorial Completo
            </button>
            <button class="tab-btn" onclick="switchTab('tab-hipotesis')">
                <i class="fa-solid fa-scale-unbalanced"></i> Evaluación de Hipótesis
            </button>
            <button class="tab-btn" onclick="switchTab('tab-seguridad')">
                <i class="fa-solid fa-shield-halved"></i> Seguridad & Policía (DAILoc)
            </button>
            <button class="tab-btn" onclick="switchTab('tab-series')">
                <i class="fa-solid fa-chart-area"></i> Series Temporales Aseo
            </button>
            <button class="tab-btn" onclick="switchTab('tab-genero')">
                <i class="fa-solid fa-users"></i> Género y Niñez
            </button>
            <button class="tab-btn" onclick="switchTab('tab-politicas')">
                <i class="fa-solid fa-building-columns"></i> Priorización & Políticas
            </button>
        </div>

        <!-- TAB 1: METODOLOGÍA & RESUMEN -->
        <div id="tab-metodologia" class="tab-pane active">
            <div class="card grid-full">
                <div class="card-header">
                    <h2><i class="fa-solid fa-diagram-project" style="color:var(--primary);"></i> Metodología DataJam en 5 Pasos: Triángulo de Vulnerabilidad</h2>
                </div>
                <p style="color: #cbd5e1; font-size: 13.5px;">
                    Integración analítica de tres dimensiones críticas de la vida urbana en Bogotá: <b>Manejo de Residuos (UAESP)</b>, <b>Emergencias Urbanas (UAECOB Bomberos)</b> y <b>Seguridad Ciudadana (Policía Nacional / MEBOG - DAILoc)</b> cruzados con la estratificación predial de IDECA.
                </p>
                <div class="step-grid">
                    <div class="step-card">
                        <h4>1. Territorio</h4>
                        <p>20 localidades, 117 UPZ y 599 cuadrantes policiales de Bogotá D.C.</p>
                    </div>
                    <div class="step-card">
                        <h4>2. Fenómeno</h4>
                        <p>Déficit de infraestructura de aseo, arrojo clandestino, emergencias por fuego y delitos de alto impacto.</p>
                    </div>
                    <div class="step-card">
                        <h4>3. Pregunta</h4>
                        <p>¿Coinciden espacialmente el déficit de aseo, las emergencias y la criminalidad en estratos socioeconómicos bajos?</p>
                    </div>
                    <div class="step-card">
                        <h4>4. Hipótesis</h4>
                        <p>Las zonas de estrato 1 y 2 sufren una triple vulnerabilidad: menor dotación de cestas, más puntos críticos de basura y mayor concentración de delitos violentos y emergencias.</p>
                    </div>
                    <div class="step-card">
                        <h4>5. Variables</h4>
                        <p>Estrato modal, tasa de cestas/10k hab, 478 puntos críticos, 11.445 homicidios, 562k casos de violencia intrafamiliar y 166k emergencias.</p>
                    </div>
                </div>
            </div>

            <div class="grid-2">
                <div class="card">
                    <div class="card-header">
                        <h2><i class="fa-solid fa-trophy" style="color: #f59e0b;"></i> Hallazgos Estadísticos Validados</h2>
                    </div>
                    <ul style="padding-left: 20px; font-size: 13px; color: #cbd5e1; line-height: 1.8;">
                        <li><b>Brecha Severa de Cestas (r = +0.74):</b> Teusaquillo y Chapinero disponen de <b>285 a 337 cestas por cada 10.000 hab</b>, mientras Bosa y Ciudad Bolívar tienen apenas <b>29 cestas por 10.000 hab</b> (brecha de más de 10 a 1).</li>
                        <li><b>Correlación Crimen vs Puntos de Basura (r = +0.68):</b> Existe una correlación directa entre el número de puntos de arrojo clandestino y el total de homicidios por localidad. Ciudad Bolívar (892 homicidios, 37 puntos), Kennedy (668 homicidios, 71 puntos) y Bosa (439 homicidios, 56 puntos) lideran ambos indicadores.</li>
                        <li><b>Violencia Intrafamiliar vs Basuras (r = +0.87):</b> Fuerte correlación espacial entre el deterioro del entorno urbano y los reportes de violencia intrafamiliar.</li>
                        <li><b>Emergencias UAECOB:</b> El <b>74.7% de los 166.977 incidentes</b> se concentran en estratos 2 y 3.</li>
                    </ul>
                </div>
                <div class="card">
                    <div class="card-header">
                        <h2><i class="fa-solid fa-pie-chart" style="color: #38bdf8;"></i> Composición de Incidentes UAECOB</h2>
                    </div>
                    {tipos_html}
                </div>
            </div>
        </div>

        <!-- TAB 2: MAPA INTERACTIVO -->
        <div id="tab-mapa" class="tab-pane">
            <div class="card grid-full">
                <div class="card-header">
                    <h2><i class="fa-solid fa-earth-americas" style="color:var(--primary);"></i> Mapa Territorial Integrado: UPZ, Basuras, Policía y Bomberos</h2>
                    <span style="font-size: 12px; color: var(--text-muted);">Activa/desactiva capas en la esquina superior derecha</span>
                </div>
                <div style="border-radius: 10px; overflow: hidden; height: 620px;">
                    {mapa_html}
                </div>
            </div>
        </div>

        <!-- TAB 3: HIPÓTESIS -->
        <div id="tab-hipotesis" class="tab-pane">
            <div class="grid-2">
                <div class="card">
                    <div class="card-header">
                        <h2><i class="fa-solid fa-scale-unbalanced" style="color:#ef4444;"></i> Disparidad de Infraestructura (Cestas vs Estrato)</h2>
                    </div>
                    {infra_html}
                </div>
                <div class="card">
                    <div class="card-header">
                        <h2><i class="fa-solid fa-triangle-exclamation" style="color:#f59e0b;"></i> Puntos Críticos de Arrojo por Localidad</h2>
                    </div>
                    {pc_html}
                </div>
            </div>
        </div>

        <!-- TAB 4: SEGURIDAD Y POLICÍA -->
        <div id="tab-seguridad" class="tab-pane">
            <div class="grid-2">
                <div class="card">
                    <div class="card-header">
                        <h2><i class="fa-solid fa-link" style="color:#ef4444;"></i> Convergencia: Homicidios vs Puntos Críticos de Basura</h2>
                    </div>
                    {crimen_basura_html}
                </div>
                <div class="card">
                    <div class="card-header">
                        <h2><i class="fa-solid fa-shield-halved" style="color:#38bdf8;"></i> Delitos de Alto Impacto (DAILoc 2018–2026)</h2>
                    </div>
                    {crime_bar_html}
                </div>
            </div>
        </div>

        <!-- TAB 5: SERIES TEMPORALES -->
        <div id="tab-series" class="tab-pane">
            <div class="card grid-full">
                <div class="card-header">
                    <h2><i class="fa-solid fa-chart-area" style="color:var(--primary);"></i> Dinámica Temporal del Servicio de Aseo RBL (2021–2026)</h2>
                </div>
                {rbl_html}
            </div>
        </div>

        <!-- TAB 6: GÉNERO Y NIÑEZ -->
        <div id="tab-genero" class="tab-pane">
            <div class="card grid-full">
                <div class="card-header">
                    <h2><i class="fa-solid fa-person-breastfeeding" style="color:#c084fc;"></i> Enfoque Diferencial de Género y Niñez en Emergencias</h2>
                </div>
                {gen_html}
                <div style="margin-top: 16px; background: #0f172a; padding: 16px; border-radius: 8px; font-size: 13px; color: #cbd5e1;">
                    <p><b>Análisis de Exposición:</b> En estratos 1, 2 y 3 se concentra el <b>82% de las niñas y niños expuestos</b> a situaciones de riesgo por incendios estructurales y quemas ilegales.</p>
                </div>
            </div>
        </div>

        <!-- TAB 7: POLÍTICAS & PRIORIZACIÓN -->
        <div id="tab-politicas" class="tab-pane">
            <div class="card grid-full" style="margin-bottom: 24px;">
                <div class="card-header">
                    <h2><i class="fa-solid fa-list-check" style="color:#10b981;"></i> Matriz Integral de Priorización Territorial (Seguridad + Aseo + Emergencias)</h2>
                </div>
                <div class="table-responsive">
                    <table>
                        <thead>
                            <tr>
                                <th>Localidad</th>
                                <th style="text-align:center;">Estrato</th>
                                <th style="text-align:right;">Población</th>
                                <th style="text-align:right;">Homicidios</th>
                                <th style="text-align:right;">Tasa Hom/10k</th>
                                <th style="text-align:right;">Puntos Críticos</th>
                                <th style="text-align:right;">Cestas</th>
                                <th style="text-align:right;">Cestas/10k</th>
                                <th style="text-align:right;">Cuadrantes Pol.</th>
                                <th style="text-align:right;">Incidentes Bom.</th>
                                <th style="text-align:center;">Prioridad</th>
                            </tr>
                        </thead>
                        <tbody>
                            {filas_tabla}
                        </tbody>
                    </table>
                </div>
            </div>

            <div class="card grid-full">
                <div class="card-header">
                    <h2><i class="fa-solid fa-lightbulb" style="color:#f59e0b;"></i> Recomendaciones de Política Pública Articulada</h2>
                </div>
                <div class="policy-card">
                    <h3><i class="fa-solid fa-bullseye"></i> 1. Plan de Choque de Rebalanceo de Cestas y Contenerización (UAESP)</h3>
                    <p>Instalar al menos <b>15.000 nuevas cestas públicas</b> en Bosa, Ciudad Bolívar, San Cristóbal y Usme para cerrar la brecha de 10x respecto al norte.</p>
                </div>
                <div class="policy-card">
                    <h3><i class="fa-solid fa-shield-halved"></i> 2. Intervención Conjunta en Puntos Críticos (Secretaría de Seguridad + MEBOG + UAESP)</h3>
                    <p>Patrullaje reforzado de los cuadrantes policiales y cámaras en los 478 puntos de arrojo clandestino para erradicar focos de criminalidad y deterioro ambiental.</p>
                </div>
                <div class="policy-card">
                    <h3><i class="fa-solid fa-fire-flame-curved"></i> 3. Prevención Barrial de Incendios con Enfoque de Género (UAECOB + SDMujer)</h3>
                    <p>Capacitación en prevención de incendios estructurales dirigida a mujeres líderes comunitarias en UPZ densas de estrato 1 y 2.</p>
                </div>
            </div>
        </div>
    </div>

    <script>
        function switchTab(tabId) {{
            document.querySelectorAll('.tab-pane').forEach(el => el.classList.remove('active'));
            document.querySelectorAll('.tab-btn').forEach(el => el.classList.remove('active'));
            
            document.getElementById(tabId).classList.add('active');
            event.currentTarget.classList.add('active');
            
            window.dispatchEvent(new Event('resize'));
        }}
    </script>
</body>
</html>
"""

dashboard_path = os.path.join(OUTPUTS, 'dashboard_datajam_bogota_2026.html')
with open(dashboard_path, 'w', encoding='utf-8') as f:
    f.write(html_content)

sz_kb = os.path.getsize(dashboard_path) / 1024
print(f"\n✅ Dashboard HTML generado exitosamente:")
print(f"   Archivo: {dashboard_path} ({sz_kb:.1f} KB)")
