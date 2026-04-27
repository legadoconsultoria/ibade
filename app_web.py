import streamlit as st
import pandas as pd
from supabase import create_client, Client
import plotly.express as px
import os
import base64
import json

# --- CONEXÃO ---
URL = "https://mtjqwikzotfvqlkspbtm.supabase.co"
KEY = "sb_publishable_-IuFm5vzE3e0bdzvgkajFg_LGwZtvYm"
supabase = create_client(URL, KEY)

st.set_page_config(page_title="Gestão PCM", layout="wide")

# Função para carregar imagem local em Base64
def get_base64_image(image_path):
    if os.path.exists(image_path):
        with open(image_path, "rb") as img_file:
            return base64.b64encode(img_file.read()).decode()
    return ""

def carregar_dados():
    try:
        r_v = supabase.table("votos_nuvem").select("*").execute()
        r_c = supabase.table("cidades").select("*").execute()
        return pd.DataFrame(r_v.data) if r_v.data else pd.DataFrame(), r_c.data if r_c.data else []
    except:
        return pd.DataFrame(), []

df_votos, lista_cidades = carregar_dados()

aba1, aba2 = st.tabs(["🏗️ Criador de Pesquisas", "📊 Análise de Dados"])

# --- ABA 1: CRIADOR ---
with aba1:
    st.header("🏗️ Painel de Controle")
    col_cad1, col_cad2 = st.columns(2)
    with col_cad1:
        st.subheader("1. Cadastrar Local")
        n_unid = st.text_input("Formato: PROJETO-LOCAL-DATA", key="n_unid")
        v_eleit = st.number_input("Eleitorado", min_value=1, value=1000)
        if st.button("Salvar Unidade"):
            if n_unid:
                supabase.table("cidades").insert({"nome": n_unid.strip(), "eleitorado": v_eleit}).execute()
                st.success("Unidade salva!")
                st.rerun()
    with col_cad2:
        st.subheader("2. Adicionar Pergunta")
        unidades = {u['nome']: u['id'] for u in lista_cidades}
        sel_u = st.selectbox("Unidade alvo:", list(unidades.keys()))
        n_perg = st.text_input("Pergunta")
        alts_txt = st.text_area("Alternativas (vírgula)")
        if st.button("Publicar Pergunta"):
            if sel_u and n_perg and alts_txt:
                resp_p = supabase.table("perguntas").insert({"cidade_id": unidades[sel_u], "texto_pergunta": n_perg}).execute()
                p_id = resp_p.data[0]['id']
                for a in [x.strip() for x in alts_txt.split(",")]:
                    supabase.table("alternativas").insert({"pergunta_id": p_id, "texto_alternativa": a, "votos": 0}).execute()
                st.success("Publicado!")

# --- ABA 2: RELATÓRIO ---
# --- ABA 2: RELATÓRIO ---
# --- ABA 2: RELATÓRIO ---
# --- ABA 2: RELATÓRIO ---
# --- ABA 2: RELATÓRIO ---
with aba2:
    if not df_votos.empty:
        dict_eleit = {str(c['nome']).strip(): (c['eleitorado'] if c['eleitorado'] else 1000) for c in lista_cidades}
        df_votos['cidade'] = df_votos['cidade'].astype(str).str.strip()
        
        # FORMA CORRIGIDA PARA O STREAMLIT CLOUD (Split nativo)
        df_meta = df_votos['cidade'].str.split('-', expand=True)
        df_votos['Proj'] = df_meta[0].fillna('?')
        df_votos['Loc'] = df_meta[1].fillna('?')
        df_votos['Data'] = df_meta[2].fillna('?')

        col1, col2, col3 = st.columns(3)
        with col1: p_sel = st.selectbox("Projeto", sorted(df_votos['Proj'].unique()))
        df_p = df_votos[df_votos['Proj'] == p_sel]
        with col2: d_sel = st.selectbox("Data", sorted(df_p['Data'].unique(), reverse=True))
        df_d = df_p[df_p['Data'] == d_sel]
        with col3: q_sel = st.selectbox("Questão", sorted(df_d['pergunta'].unique()))

        df_f = df_d[df_d['pergunta'] == q_sel]
        if not df_f.empty:
            st.divider()
            
            ct = df_f.groupby(['Loc', 'cidade', 'resposta']).size().reset_index(name='v')
            tt = df_f.groupby(['Loc', 'cidade']).size().reset_index(name='t')
            df_m = pd.merge(ct, tt, on=['Loc', 'cidade'])
            df_m['%'] = (df_m['v'] / df_m['t']) * 100
            tabela = df_m.pivot(index='Loc', columns='resposta', values='%').fillna(0)
            
            cidades_ativas = df_f['cidade'].unique()
            total_e = sum(int(dict_eleit.get(cid, 1000)) for cid in cidades_ativas)
            ponderada = {}
            for col in tabela.columns:
                soma_p = sum(tabela.loc[loc, col] * int(dict_eleit.get(df_f[df_f['Loc'] == loc]['cidade'].iloc[0], 1000)) for loc in tabela.index)
                ponderada[col] = (soma_p / total_e) if total_e > 0 else 0
            
            tab_final = pd.concat([tabela, pd.DataFrame([ponderada], index=['TOTAL PONDERADO'])])
            
            # EXIBIÇÃO NA TELA
            if os.path.exists("logo.png"): st.image("logo.png")
            st.write(f"### QUESTÃO: {q_sel}")
            st.table(tab_final.style.format("{:.1f}%"))
            
            df_graf = pd.DataFrame(list(ponderada.items()), columns=['Opção', 'Votos %'])
            fig = px.bar(df_graf, x='Opção', y='Votos %', text=df_graf['Votos %'].apply(lambda x: f'{x:.1f}%'))
            fig.update_layout(yaxis=dict(range=[0, 110]), template="plotly_white")
            st.plotly_chart(fig, use_container_width=True)

            # --- EXPORTAÇÃO HTML CORRIGIDA (SEM QUEBRA DE LINHA) ---
            logo_base64 = get_base64_image("logo.png")
            chart_data = pd.DataFrame(list(ponderada.items()), columns=['label', 'value'])
            chart_json = json.dumps(chart_data.to_dict(orient='records'))
            
            # Gera o HTML e ajusta o cabeçalho "REGIÃO" de forma limpa
            tabela_html = tab_final.style.format("{:.1f}%").to_html(classes="table")
            tabela_html = tabela_html.replace('<th class="blank level0" >&nbsp;</th>', '<th style="text-align:center">REGIÃO</th>')

            html_relatorio = f"""
            <html>
            <head>
                <meta charset="UTF-8">
                <script src="https://cdn.plot.ly/plotly-latest.min.js"></script>
                <style>
                    body {{ font-family: sans-serif; padding: 30px; color: black; background: white; }}
                    .logo-container {{ text-align: center; margin-bottom: 20px; }}
                    .logo-container img {{ max-width: 450px; }}
                    .pergunta-header {{ font-size: 18px; font-weight: bold; text-align: left; margin: 25px 0 15px 0; border-bottom: 1px solid #333; padding-bottom: 5px; }}
                    table {{ width: 100%; border-collapse: collapse; margin-bottom: 30px; font-size: 14px; }}
                    th, td {{ border: 1px solid #000; padding: 8px; text-align: center; }}
                    th {{ background: #eeeeee; font-weight: bold; }}
                    .footer-legal {{ margin-top: 40px; font-size: 12px; color: #333; border-top: 1px solid #ccc; padding-top: 15px; text-align: justify; line-height: 1.5; }}
                </style>
            </head>
            <body>
                <div class="logo-container"><img src="data:image/png;base64,{logo_base64}"></div>
                <div class="pergunta-header">QUESTÃO: {q_sel}</div>
                {tabela_html}
                <div id="grafico" style="width:100%; height:400px; margin-top:30px;"></div>
                <div class="footer-legal">
                    <b>ATENÇÃO:</b> ATENÇÃO : De acordo com o Artigo 33 da Resolução n. 20.101 do Código Eleitoral, o resultado desta Pesquisa só poderá ser divulgado com autorização prévia do TRE.<br>
                    <b>Eleitorado total base: {total_e} pessoas.</b>
                </div>
                <script>
                    var data = {chart_json};
                    var labels = data.map(d => d.label);
                    var values = data.map(d => d.value);
                    var trace = {{ x: labels, y: values, type: 'bar', text: values.map(v => v.toFixed(1) + '%'), textposition: 'outside', marker: {{ color: '#0078D4' }} }};
                    var layout = {{ title: 'Resultado Ponderado', yaxis: {{ ticksuffix: '%', range: [0, 110] }} }};
                    Plotly.newPlot('grafico', [trace], layout).then(function() {{ setTimeout(function() {{ window.print(); }}, 800); }});
                </script>
            </body>
            </html>
            """
            
            st.download_button(label="📥 Baixar Relatório para Impressão", data=html_relatorio, file_name=f"Relatorio_{p_sel}.html", mime="text/html")