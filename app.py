import streamlit as st
import pandas as pd
from weasyprint import HTML
import io

st.set_page_config(page_title="Reportes Axalta", page_icon="📊", layout="centered")

st.title("📊 Generador de Reportes - Axalta")
st.write("Sube los archivos CSV para generar tu reporte gerencial en PDF.")

col1, col2 = st.columns(2)
with col1:
    tc_file = st.file_uploader("1. Tipos de Cambio (TC.csv)", type=['csv'])
    actual_file = st.file_uploader("2. Ventas Mes Actual (CSV)", type=['csv'])
with col2:
    marzo_file = st.file_uploader("3. Histórico Mes -2 (Ej. Marzo)", type=['csv'])
    abril_file = st.file_uploader("4. Histórico Mes -1 (Ej. Abril)", type=['csv'])

def calc_growth(current, previous):
    if previous > 0: return ((current - previous) / previous) * 100
    elif current > 0: return 100.0
    return 0.0

def format_curr(val): return f"${val:,.2f}"
def format_num(val): return f"{int(val):,}"
def format_growth(val):
    color = "green" if val > 0 else "red" if val < 0 else "gray"
    sign = "+" if val > 0 else ""
    return f"<span style='color: {color}; font-weight: bold;'>{sign}{val:,.2f}%</span>"

if st.button("🚀 Generar Reporte PDF", type="primary"):
    if tc_file and actual_file and marzo_file and abril_file:
        try:
            with st.spinner('Calculando crecimientos y generando PDF...'):
                # 1. Tipos de Cambio
                df_tc = pd.read_csv(tc_file, skiprows=3).iloc[:, :2]
                df_tc.columns = ['PAÍS', 'TC USD']
                df_tc = df_tc.dropna(subset=['PAÍS'])
                df_tc['TC USD'] = pd.to_numeric(df_tc['TC USD'], errors='coerce')

                # 2. Mes Actual
                df_actual = pd.read_csv(actual_file)
                df_actual['MONTO TICKET'] = pd.to_numeric(df_actual['MONTO TICKET'].astype(str).str.replace(',', ''), errors='coerce')
                df_actual = df_actual.merge(df_tc, how='left', on='PAÍS')
                df_actual['TC USD'] = df_actual['TC USD'].fillna(1.0)
                df_actual['TOTAL USD'] = df_actual['MONTO TICKET'] / df_actual['TC USD']

                actual_pais = df_actual.groupby('PAÍS').agg(Tickets_May=('NÚMERO DE TICKET', 'count'), Monto_USD_May=('TOTAL USD', 'sum')).reset_index()
                actual_dist = df_actual.groupby(['PAÍS', 'RAZÓN SOCIAL']).agg(Tickets=('NÚMERO DE TICKET', 'count'), Monto_USD=('TOTAL USD', 'sum')).reset_index().sort_values(['PAÍS', 'Monto_USD'], ascending=[True, False])

                # 3. Históricos
                df_marzo = pd.read_csv(marzo_file)
                df_abril = pd.read_csv(abril_file)
                for df in [df_marzo, df_abril]:
                    df['TOTAL USD'] = pd.to_numeric(df['TOTAL USD'].astype(str).str.replace(',', ''), errors='coerce')
                
                marzo_pais = df_marzo.groupby('PAÍS').agg(Tickets_Mar=('NÚMERO DE TICKET', 'count'), Monto_USD_Mar=('TOTAL USD', 'sum')).reset_index()
                abril_pais = df_abril.groupby('PAÍS').agg(Tickets_Apr=('NÚMERO DE TICKET', 'count'), Monto_USD_Apr=('TOTAL USD', 'sum')).reset_index()

                # 4. Combinar
                history = marzo_pais.merge(abril_pais, on='PAÍS', how='outer').merge(actual_pais, on='PAÍS', how='outer').fillna(0)
                history['Crecimiento_Abr_vs_Mar'] = history.apply(lambda row: calc_growth(row['Monto_USD_Apr'], row['Monto_USD_Mar']), axis=1)
                history['Crecimiento_May_vs_Abr'] = history.apply(lambda row: calc_growth(row['Monto_USD_May'], row['Monto_USD_Apr']), axis=1)
                history = history.sort_values('PAÍS')

                total_tickets_may = df_actual['NÚMERO DE TICKET'].count()
                total_usd_may = df_actual['TOTAL USD'].sum()
                growth_apr_may = calc_growth(total_usd_may, df_abril['TOTAL USD'].sum())

                # 5. Generar HTML
                css = """
                @page { size: A4 landscape; margin: 15mm 20mm; background-color: #faf8f5; 
                @bottom-right { content: "Página " counter(page) " de " counter(pages); font-family: 'Segoe UI', Tahoma, sans-serif; font-size: 8pt; color: #888; } }
                body { font-family: 'Segoe UI', Tahoma, sans-serif; margin: 0; padding: 0; color: #333; background-color: transparent; }
                *, *::before, *::after { box-sizing: border-box; }
                .container { width: 100%; background: #fff; padding: 25px 25px; border-top: 8px solid #c62828; border-radius: 4px; }
                .header-table { width: 100%; border-bottom: 3px solid #212121; padding-bottom: 15px; margin-bottom: 25px; }
                .header-left { text-align: left; vertical-align: middle; }
                .header-right { text-align: right; vertical-align: middle; }
                .header-left h1 { margin: 0; color: #212121; text-transform: uppercase; letter-spacing: 1.5px; font-size: 20pt; }
                .logo { display: inline-block; background: #c62828; color: white; padding: 6px 18px; font-weight: 800; font-size: 16pt; border-radius: 4px; letter-spacing: 2px; }
                .kpi-table { width: calc(100% + 20px); margin-left: -10px; table-layout: fixed; border-spacing: 20px 0; margin-bottom: 30px; }
                .kpi-card { background: #f5f5f5; padding: 15px 20px; border-left: 6px solid #ff8f00; border-radius: 4px; vertical-align: top; }
                .kpi-value { font-size: 20pt; font-weight: bold; color: #c62828; margin-bottom: 5px; }
                .kpi-label { font-size: 9pt; color: #616161; text-transform: uppercase; font-weight: bold; }
                h2 { color: #c62828; border-bottom: 2px solid #eeeeee; padding-bottom: 8px; margin-top: 20px; font-size: 14pt; page-break-after: avoid; }
                table { width: 100%; border-collapse: collapse; margin-bottom: 25px; font-size: 9pt; table-layout: auto; }
                th, td { padding: 8px 6px; text-align: left; border-bottom: 1px solid #e0e0e0; vertical-align: middle; }
                th { background-color: #212121; color: #fff; text-transform: uppercase; font-size: 8pt; font-weight: bold; }
                tr { page-break-inside: avoid; }
                tr:nth-child(even) { background-color: #fafafa; }
                .text-right { text-align: right; white-space: nowrap; }
                .total-row { font-weight: bold; background-color: #ffe0b2 !important; border-top: 2px solid #ff9800; }
                """
                
                html = f"""<!DOCTYPE html><html lang="es"><head><meta charset="UTF-8"><style>{css}</style></head>
                <body><div class="container">
                <table class="header-table"><tr><td class="header-left"><h1>Reporte de Ventas y Tickets</h1></td>
                <td class="header-right"><div class="logo">AXALTA</div></td></tr></table>
                <table class="kpi-table"><tr>
                <td class="kpi-card"><div class="kpi-value">{format_curr(total_usd_may)}</div><div class="kpi-label">Ventas Totales Actuales (USD)</div></td>
                <td class="kpi-card"><div class="kpi-value">{format_num(total_tickets_may)}</div><div class="kpi-label">Tickets Registrados Actuales</div></td>
                <td class="kpi-card"><div class="kpi-value">{format_growth(growth_apr_may)}</div><div class="kpi-label">Crecimiento vs Mes Anterior</div></td>
                </tr></table>
                <h2>1. Histórico de Crecimiento</h2>
                <table><thead><tr><th>País</th><th class="text-right">Tickets<br>Mes -2</th><th class="text-right">Ventas Mes -2<br>(USD)</th><th class="text-right">Tickets<br>Mes -1</th><th class="text-right">Ventas Mes -1<br>(USD)</th><th class="text-right">Crecimiento<br>Mes -1</th><th class="text-right">Tickets<br>Actual</th><th class="text-right">Ventas Actual<br>(USD)</th><th class="text-right">Crecimiento<br>Actual</th></tr></thead><tbody>"""
                
                t_t_mar = t_u_mar = t_t_abr = t_u_abr = t_t_may = t_u_may = 0
                for _, row in history.iterrows():
                    t_t_mar += row['Tickets_Mar']; t_u_mar += row['Monto_USD_Mar']
                    t_t_abr += row['Tickets_Apr']; t_u_abr += row['Monto_USD_Apr']
                    t_t_may += row['Tickets_May']; t_u_may += row['Monto_USD_May']
                    html += f"<tr><td><strong>{row['PAÍS']}</strong></td><td class='text-right'>{format_num(row['Tickets_Mar'])}</td><td class='text-right'>{format_curr(row['Monto_USD_Mar'])}</td><td class='text-right'>{format_num(row['Tickets_Apr'])}</td><td class='text-right'>{format_curr(row['Monto_USD_Apr'])}</td><td class='text-right'>{format_growth(row['Crecimiento_Abr_vs_Mar'])}</td><td class='text-right'>{format_num(row['Tickets_May'])}</td><td class='text-right'>{format_curr(row['Monto_USD_May'])}</td><td class='text-right'>{format_growth(row['Crecimiento_May_vs_Abr'])}</td></tr>"
                
                html += f"<tr class='total-row'><td><strong>TOTAL GENERAL</strong></td><td class='text-right'>{format_num(t_t_mar)}</td><td class='text-right'>{format_curr(t_u_mar)}</td><td class='text-right'>{format_num(t_t_abr)}</td><td class='text-right'>{format_curr(t_u_abr)}</td><td class='text-right'>{format_growth(calc_growth(t_u_abr, t_u_mar))}</td><td class='text-right'>{format_num(t_t_may)}</td><td class='text-right'>{format_curr(t_u_may)}</td><td class='text-right'>{format_growth(calc_growth(t_u_may, t_u_abr))}</td></tr></tbody></table>"
                
                html += "<h2>2. Desempeño por País y Distribuidor (Mes Actual)</h2><table><thead><tr><th>País</th><th>Razón Social (Distribuidor)</th><th class='text-right'>Tickets</th><th class='text-right'>Ventas (USD)</th></tr></thead><tbody>"
                curr_pais = ""
                for _, row in actual_dist.iterrows():
                    p_disp = row['PAÍS'] if row['PAÍS'] != curr_pais else ""
                    curr_pais = row['PAÍS']
                    html += f"<tr><td><strong>{p_disp}</strong></td><td>{row['RAZÓN SOCIAL']}</td><td class='text-right'>{format_num(row['Tickets'])}</td><td class='text-right'>{format_curr(row['Monto_USD'])}</td></tr>"
                
                html += "</tbody></table></div></body></html>"

                # 6. Crear PDF en memoria
                pdf_buffer = io.BytesIO()
                HTML(string=html).write_pdf(pdf_buffer)
                
                st.success("¡Reporte generado exitosamente!")
                st.download_button(label="📄 Descargar Reporte PDF", data=pdf_buffer.getvalue(), file_name="Reporte_Gerencial_Axalta.pdf", mime="application/pdf")

        except Exception as e:
            st.error(f"Error al procesar: {e}. Revisa que los archivos tengan el formato correcto.")
    else:
        st.warning("Falta subir uno o más archivos.")
