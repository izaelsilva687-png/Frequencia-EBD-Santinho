import datetime
import pandas as pd
import plotly.express as px
import requests
import streamlit as st

# Configuração da Página
st.set_page_config(
    page_title="Frequência EBD — Gestão da Escola Dominical - AD Santinho",
    page_icon="📖",
    layout="wide",
)

# -----------------------------------------------------------------------------
# CONFIGURAÇÃO DA PLANILHA E DO WEB APP
# -----------------------------------------------------------------------------
# 1. COLE O ID DA SUA PLANILHA AQUI:
SPREADSHEET_ID = "1jeR_pPWlkss_4O7lEumQbF6ajTOHAN4VEHTkvVEqQyw"

# 2. COLE A URL DO WEB APP GERADO NO GOOGLE APPS SCRIPT AQUI:
URL_WEB_APP = "https://script.google.com/macros/s/AKfycbz2QimxIPzLJTuQMFOavn_sAuroUifn22oIoPWz4rKMc_CoUlXY8siJDggu1csph1CBSw/exec"

# LISTA DAS 7 TURMAS DA EBD
TURMAS = [
    "OFICIAIS",
    "LÍRIOS DO VALE",
    "VENCEDORES POR CRISTO",
    "PRÉ-ADOLESCENTES",
    "JUNIORES",
    "JARDIM DE INFÂNCIA",
    "BERÇÁRIO",
]


# -----------------------------------------------------------------------------
# FUNÇÕES DE LEITURA E GRAVAÇÃO
# -----------------------------------------------------------------------------
def carregar_dados():
  """Lê as abas da planilha pública do Google Sheets"""
  try:
    url_alunos = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=Alunos"
    df_alunos = pd.read_csv(url_alunos)
    if df_alunos.empty or "nome" not in df_alunos.columns:
      df_alunos = pd.DataFrame(columns=["id", "nome", "turma", "ativo"])
    else:
      df_alunos["ativo"] = (
          df_alunos["ativo"].astype(str).str.upper().isin(["TRUE", "1"])
      )
  except Exception:
    df_alunos = pd.DataFrame(columns=["id", "nome", "turma", "ativo"])

  try:
    url_chamadas = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=Chamadas"
    df_chamadas = pd.read_csv(url_chamadas)
    if df_chamadas.empty or "presente" not in df_chamadas.columns:
      df_chamadas = pd.DataFrame(
          columns=["data", "turma", "aluno_id", "nome", "presente"]
      )
    else:
      df_chamadas["presente"] = (
          df_chamadas["presente"].astype(str).str.upper().isin(["TRUE", "1"])
      )
  except Exception:
    df_chamadas = pd.DataFrame(
        columns=["data", "turma", "aluno_id", "nome", "presente"]
    )

  try:
    url_resumo = f"https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet=Resumo"
    df_resumo = pd.read_csv(url_resumo)
    if df_resumo.empty:
      df_resumo = pd.DataFrame(columns=["data", "turma", "visitantes", "oferta"])
  except Exception:
    df_resumo = pd.DataFrame(columns=["data", "turma", "visitantes", "oferta"])

  return df_alunos, df_chamadas, df_resumo


def salvar_na_planilha(nome_aba, df, mode="overwrite"):
  """Envia os dados para o Web App do Google salvar na planilha."""
  try:
    dados = [df.columns.tolist()] + df.values.tolist()
    payload = {"sheet": nome_aba, "rows": dados, "mode": mode}
    res = requests.post(URL_WEB_APP, json=payload)
    return res.status_code == 200
  except Exception as e:
    st.error(f"Erro ao salvar dados: {e}")
    return False


# Carrega dados
df_alunos, df_chamadas, df_resumo_turma = carregar_dados()

# -----------------------------------------------------------------------------
# CABEÇALHO E NAVEGAÇÃO
# -----------------------------------------------------------------------------
st.title("📖 Sistema de Frequência da Escola Dominical - AD Santinho")
st.caption("Gestão em tempo real das 7 turmas da EBD — Conectado ao Google Drive")

aba_chamada, aba_relatorio_domingo, aba_anual, = st.tabs([
    "📱 Fazer Chamada",
    "📊 Relatório do Domingo",
    "🏆 Histórico Anual do Aluno",
])

# =============================================================================
# ABA 1: FAZER CHAMADA (PROFESSORES)
# =============================================================================
with aba_chamada:
  st.subheader("📱 Registro de Frequência do Domingo")

  col_t1, col_t2 = st.columns(2)
  with col_t1:
    turma_prof = st.selectbox("Selecione a sua Turma:", TURMAS)
  with col_t2:
    data_aula = st.date_input(
        "Data da Aula:", datetime.date.today(), format="DD/MM/YYYY"
    )

  st.markdown("---")

  df_alunos_turma = df_alunos[
      (df_alunos["turma"] == turma_prof) & (df_alunos["ativo"] == True)
  ].sort_values("nome")

  if df_alunos_turma.empty:
    st.warning(
        f"Nenhum aluno cadastrado para a turma '{turma_prof}'. Cadastre alunos"
        " na aba 'Cadastrar Alunos'."
    )
  else:
    st.write(
        f"### Lista de Alunos Matriculados ({len(df_alunos_turma)} alunos)"
    )
    st.caption(
        "Marque a caixa para os alunos PRESENTES. Deixe desmarcado para quem"
        " faltou:"
    )

    with st.form(key=f"form_chamada_{turma_prof}"):
      presencas = {}
      cols_alunos = st.columns(2)

      for idx, row in df_alunos_turma.reset_index(drop=True).iterrows():
        col_target = cols_alunos[idx % 2]
        presencas[row["id"]] = col_target.checkbox(
            label=f"👤 **{row['nome']}**", value=True, key=f"aluno_{row['id']}"
        )

      st.markdown("---")
      st.write("### ➕ Visitantes e Oferta da Turma")
      col_v, col_o = st.columns(2)

      with col_v:
        num_visitantes = st.number_input(
            "Número de Visitantes no dia:", min_value=0, value=0, step=1
        )
      with col_o:
        val_oferta = st.number_input(
            "Valor da Oferta Coletada (R$):",
            min_value=0.0,
            value=0.0,
            step=1.0,
            format="%.2f",
        )

      btn_salvar = st.form_submit_button(
          "💾 Salvar Chamada do Domingo", use_container_width=True
      )

      if btn_salvar:
        str_data = data_aula.strftime("%d/%m/%Y")

        df_chamadas_limpas = df_chamadas[
            ~((df_chamadas["data"] == str_data) & (df_chamadas["turma"] == turma_prof))
        ]
        df_resumo_limpo = df_resumo_turma[
            ~((df_resumo_turma["data"] == str_data) & (df_resumo_turma["turma"] == turma_prof))
        ]

        novas_chamadas = []
        for aluno_id, esteve_presente in presencas.items():
          nome_aluno = df_alunos_turma[df_alunos_turma["id"] == aluno_id][
              "nome"
          ].values[0]
          novas_chamadas.append({
              "data": str_data,
              "turma": turma_prof,
              "aluno_id": aluno_id,
              "nome": nome_aluno,
              "presente": esteve_presente,
          })

        df_novas_ch = pd.DataFrame(novas_chamadas)
        df_chamadas_final = pd.concat(
            [df_chamadas_limpas, df_novas_ch], ignore_index=True
        )

        novo_resumo = pd.DataFrame([{
            "data": str_data,
            "turma": turma_prof,
            "visitantes": num_visitantes,
            "oferta": val_oferta,
        }])
        df_resumo_final = pd.concat(
            [df_resumo_limpo, novo_resumo], ignore_index=True
        )

        salvar_na_planilha("Chamadas", df_chamadas_final, mode="overwrite")
        salvar_na_planilha("Resumo", df_resumo_final, mode="overwrite")

        total_presentes_dia = sum(presencas.values())
        st.success(
            f"✅ Chamada da turma '{turma_prof}' referente a {str_data} salva com"
            f" sucesso! ({total_presentes_dia} presentes, {num_visitantes}"
            f" visitantes e R$ {val_oferta:.2f} de oferta)."
        )
        st.rerun()

# =============================================================================
# ABA 2: RELATÓRIO DO DOMINGO
# =============================================================================
with aba_relatorio_domingo:
  st.subheader("📊 Painel Consolidado da Apuração de Domingo")

  col_r1, col_r2 = st.columns(2)
  with col_r1:
    filtro_data = st.date_input(
        "Data do Domingo:",
        datetime.date.today(),
        format="DD/MM/YYYY",
        key="filtro_data_rel",
    )
  with col_r2:
    filtro_turma = st.selectbox(
        "Selecione o Escopo do Relatório:",
        ["🌟 CONSOLIDADO GERAL (Todas as 7 Turmas)"] + TURMAS,
    )

  str_filtro_data = filtro_data.strftime("%d/%m/%Y")

  df_ch_data = df_chamadas[df_chamadas["data"] == str_filtro_data]
  df_res_data = df_resumo_turma[df_resumo_turma["data"] == str_filtro_data]

  if "CONSOLIDADO GERAL" not in filtro_turma:
    df_ch_data = df_ch_data[df_ch_data["turma"] == filtro_turma]
    df_res_data = df_res_data[df_res_data["turma"] == filtro_turma]
    df_matr = df_alunos[
        (df_alunos["turma"] == filtro_turma) & (df_alunos["ativo"] == True)
    ]
  else:
    df_matr = df_alunos[df_alunos["ativo"] == True]

  num_matriculados = len(df_matr)
  num_presentes = (
      df_ch_data["presente"].sum() if not df_ch_data.empty else 0
  )
  num_ausentes = max(0, num_matriculados - num_presentes)
  num_visitantes = (
      int(df_res_data["visitantes"].sum()) if not df_res_data.empty else 0
  )
  presenca_total = num_presentes + num_visitantes
  total_oferta = (
      float(df_res_data["oferta"].sum()) if not df_res_data.empty else 0.0
  )
  taxa_freq = (
      (num_presentes / num_matriculados * 100) if num_matriculados > 0 else 0
  )

  m1, m2, m3, m4 = st.columns(4)
  m1.metric("📋 Matriculados", num_matriculados)
  m2.metric("✅ Presentes (Alunos)", num_presentes)
  m3.metric("❌ Ausentes", num_ausentes)
  m4.metric("📊 Taxa de Frequência", f"{taxa_freq:.1f}%")

  m5, m6, m7 = st.columns(3)
  m5.metric("🤝 Visitantes", num_visitantes)
  m6.metric("👥 Presença Total (Alunos + Vis.)", presenca_total)
  m7.metric("💰 Oferta Total", f"R$ {total_oferta:.2f}")

  st.markdown("---")

  if "CONSOLIDADO GERAL" in filtro_turma:
    st.write("### 📈 Resumo Comparativo por Turma")
    resumo_turmas_list = []

    for t in TURMAS:
      mat_t = len(
          df_alunos[(df_alunos["turma"] == t) & (df_alunos["ativo"] == True)]
      )
      ch_t = df_chamadas[
          (df_chamadas["data"] == str_filtro_data) & (df_chamadas["turma"] == t)
      ]
      res_t = df_resumo_turma[
          (df_resumo_turma["data"] == str_filtro_data)
          & (df_resumo_turma["turma"] == t)
      ]

      pres_t = ch_t["presente"].sum() if not ch_t.empty else 0
      aus_t = max(0, mat_t - pres_t)
      vis_t = int(res_t["visitantes"].sum()) if not res_t.empty else 0
      p_tot_t = pres_t + vis_t
      ofe_t = float(res_t["oferta"].sum()) if not res_t.empty else 0.0

      resumo_turmas_list.append({
          "Turma": t,
          "Matriculados": mat_t,
          "Presentes": pres_t,
          "Ausentes": aus_t,
          "Visitantes": vis_t,
          "Presença Total": p_tot_t,
          "Oferta (R$)": f"R$ {ofe_t:.2f}",
      })

    df_resumo_final = pd.DataFrame(resumo_turmas_list)
    st.dataframe(df_resumo_final, hide_index=True, use_container_width=True)

    fig_comp = px.bar(
        df_resumo_final,
        x="Turma",
        y=["Presentes", "Visitantes"],
        title="Presença de Alunos x Visitantes por Turma",
        barmode="stack",
    )
    st.plotly_chart(fig_comp, use_container_width=True)

# =============================================================================
# ABA 3: HISTÓRICO ANUAL
# =============================================================================
with aba_anual:
  st.subheader("🏆 Relatório Acumulado de Assiduidade dos Alunos")

  if df_chamadas.empty:
    st.info("Nenhuma chamada realizada ainda no sistema.")
  else:
    df_rank = (
        df_chamadas.groupby(["aluno_id", "nome", "turma"])
        .agg(
            total_aulas=("presente", "count"),
            presencas=("presente", lambda x: x.sum()),
        )
        .reset_index()
    )

    df_rank["faltas"] = df_rank["total_aulas"] - df_rank["presencas"]
    df_rank["frequencia_pct"] = (
        df_rank["presencas"] / df_rank["total_aulas"] * 100
    )

    df_rank = df_rank.sort_values(
        by=["frequencia_pct", "presencas"], ascending=False
    )

    st.write("### 🥇 Ranking de Assiduidade")
    st.dataframe(
        df_rank.rename(
            columns={
                "nome": "Nome do Aluno",
                "turma": "Turma",
                "total_aulas": "Total de Domingos",
                "presencas": "Presenças",
                "faltas": "Faltas",
                "frequencia_pct": "% Assiduidade",
            }
        )[
            [
                "Nome do Aluno",
                "Turma",
                "Total de Domingos",
                "Presenças",
                "Faltas",
                "% Assiduidade",
            ]
        ],
        hide_index=True,
        use_container_width=True,
    )
