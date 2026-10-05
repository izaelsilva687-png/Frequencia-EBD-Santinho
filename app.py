import datetime
import pandas as pd
import plotly.express as px
import streamlit as st
from streamlit_gsheets import GSheetsConnection

# Configuração da Página
st.set_page_config(
    page_title="Frequência EBD — Gestão da Escola Dominical",
    page_icon="📖",
    layout="wide",
)

# -----------------------------------------------------------------------------
# LISTA DAS 7 TURMAS DA EBD
# -----------------------------------------------------------------------------
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
# CONEXÃO COM O GOOGLE SHEETS
# -----------------------------------------------------------------------------
conn = st.connection("gsheets", type=GSheetsConnection)


def carregar_dados():
  """Lê as abas da planilha no Google Drive"""
  try:
    df_alunos = conn.read(worksheet="Alunos", ttl=0)
    if df_alunos is None or df_alunos.empty:
      df_alunos = pd.DataFrame(columns=["id", "nome", "turma", "ativo"])
    else:
      df_alunos["ativo"] = (
          df_alunos["ativo"].astype(str).str.upper().isin(["TRUE", "1"])
      )
  except Exception:
    df_alunos = pd.DataFrame(columns=["id", "nome", "turma", "ativo"])

  try:
    df_chamadas = conn.read(worksheet="Chamadas", ttl=0)
    if df_chamadas is None or df_chamadas.empty:
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
    df_resumo = conn.read(worksheet="Resumo", ttl=0)
    if df_resumo is None or df_resumo.empty:
      df_resumo = pd.DataFrame(columns=["data", "turma", "visitantes", "oferta"])
  except Exception:
    df_resumo = pd.DataFrame(columns=["data", "turma", "visitantes", "oferta"])

  return df_alunos, df_chamadas, df_resumo


# Carrega dados do Google Sheets
df_alunos, df_chamadas, df_resumo_turma = carregar_dados()

# -----------------------------------------------------------------------------
# CABEÇALHO DO APLICATIVO
# -----------------------------------------------------------------------------
st.title("📖 Sistema de Frequência da Escola Dominical")
st.caption(
    "Gestão em tempo real das 7 turmas da EBD — Conectado ao Google Sheets"
)

# NAVEGAÇÃO PRINCIPAL (ABAS)
aba_chamada, aba_relatorio_domingo, aba_anual, aba_cadastro = st.tabs([
    "📱 Fazer Chamada",
    "📊 Relatório do Domingo",
    "🏆 Histórico Anual do Aluno",
    "👤 Cadastrar Alunos",
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

  # Filtrar alunos da turma selecionada
  df_alunos_turma = df_alunos[
      (df_alunos["turma"] == turma_prof) & (df_alunos["ativo"] == True)
  ].sort_values("nome")

  if df_alunos_turma.empty:
    st.warning(
        f"Nenhum aluno cadastrado para a turma '{turma_prof}'. Vá na aba"
        " 'Cadastrar Alunos' para incluir a lista."
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

        # Remover registros anteriores da mesma data/turma se houver recálculo
        df_chamadas_limpas = df_chamadas[
            ~((df_chamadas["data"] == str_data) & (df_chamadas["turma"] == turma_prof))
        ]
        df_resumo_limpo = df_resumo_turma[
            ~((df_resumo_turma["data"] == str_data) & (df_resumo_turma["turma"] == turma_prof))
        ]

        # Novas chamadas
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

        # Atualiza o Google Sheets
        conn.update(worksheet="Chamadas", data=df_chamadas_final)
        conn.update(worksheet="Resumo", data=df_resumo_final)

        total_presentes_dia = sum(presencas.values())
        st.success(
            f"✅ Chamada da turma '{turma_prof}' referente a {str_data} salva no"
            f" Google Sheets! ({total_presentes_dia} presentes, {num_visitantes}"
            f" visitantes e R$ {val_oferta:.2f} de oferta)."
        )
        st.rerun()

# =============================================================================
# ABA 2: RELATÓRIO DO DOMINGO (DIREÇÃO)
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
# ABA 3: HISTÓRICO ANUAL DO ALUNO
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

# =============================================================================
# ABA 4: CADASTRO E GESTÃO DE ALUNOS
# =============================================================================
with aba_cadastro:
  st.subheader("👤 Cadastrar Novo Aluno")

  with st.form("form_cad_aluno", clear_on_submit=True):
    col_a1, col_a2 = st.columns(2)
    with col_a1:
      nome_novo = st.text_input("Nome Completo do Aluno:")
    with col_a2:
      turma_nova = st.selectbox("Atribuir à Turma:", TURMAS)

    btn_cadastrar = st.form_submit_button("➕ Cadastrar Aluno")

    if btn_cadastrar:
      if nome_novo.strip() == "":
        st.error("Por favor, digite o nome do aluno.")
      else:
        novo_id = (
            int(df_alunos["id"].max()) + 1
            if not df_alunos.empty and pd.notna(df_alunos["id"].max())
            else 1
        )
        novo_aluno = pd.DataFrame([{
            "id": novo_id,
            "nome": nome_novo.strip(),
            "turma": turma_nova,
            "ativo": True,
        }])
        df_alunos_atualizado = pd.concat(
            [df_alunos, novo_aluno], ignore_index=True
        )

        conn.update(worksheet="Alunos", data=df_alunos_atualizado)
        st.success(
            f"Aluno **{nome_novo}** salvo com sucesso na planilha Google!"
        )
        st.rerun()

  st.markdown("---")
  st.write("### 📋 Alunos Cadastrados no Sistema")
  df_alunos_ativos = df_alunos[df_alunos["ativo"] == True]
  st.dataframe(
      df_alunos_ativos[["id", "nome", "turma"]],
      hide_index=True,
      use_container_width=True,
  )

  # -----------------------------------------------------------------------------
  # EDITAR ALUNO OU MUDAR DE TURMA
  # -----------------------------------------------------------------------------
  st.markdown("---")
  st.subheader("✏️ Editar Aluno ou Mudar de Turma")

  if not df_alunos_ativos.empty:
    opcoes_alunos_edit = {
        row["id"]: f"{row['nome']} — {row['turma']}"
        for _, row in df_alunos_ativos.iterrows()
    }

    aluno_id_edit = st.selectbox(
        "Selecione o Aluno que deseja editar:",
        options=list(opcoes_alunos_edit.keys()),
        format_func=lambda x: opcoes_alunos_edit[x],
        key="select_edit_aluno",
    )

    aluno_atual = df_alunos_ativos[
        df_alunos_ativos["id"] == aluno_id_edit
    ].iloc[0]

    with st.form(key=f"form_edit_aluno_{aluno_id_edit}"):
      col_ed1, col_ed2 = st.columns(2)
      with col_ed1:
        novo_nome_edit = st.text_input(
            "Nome do Aluno:", value=aluno_atual["nome"]
        )
      with col_ed2:
        index_turma_atual = (
            TURMAS.index(aluno_atual["turma"])
            if aluno_atual["turma"] in TURMAS
            else 0
        )
        nova_turma_edit = st.selectbox(
            "Selecione a Nova Turma:", TURMAS, index=index_turma_atual
        )

      btn_salvar_edit = st.form_submit_button("💾 Salvar Alterações")

      if btn_salvar_edit:
        df_alunos.loc[df_alunos["id"] == aluno_id_edit, "nome"] = (
            novo_nome_edit.strip()
        )
        df_alunos.loc[df_alunos["id"] == aluno_id_edit, "turma"] = (
            nova_turma_edit
        )

        conn.update(worksheet="Alunos", data=df_alunos)
        st.success("Alterações salvas com sucesso no Google Sheets!")
        st.rerun()

  # -----------------------------------------------------------------------------
  # EXCLUIR ALUNO CADASTRADO
  # -----------------------------------------------------------------------------
  st.markdown("---")
  st.subheader("🗑️ Excluir Aluno Cadastrado")

  if not df_alunos_ativos.empty:
    col_ex1, col_ex2 = st.columns(2)

    with col_ex1:
      opcoes_alunos = {
          row["id"]: f"{row['nome']} — {row['turma']}"
          for _, row in df_alunos_ativos.iterrows()
      }
      aluno_id_selecionado = st.selectbox(
          "Selecione o Aluno que deseja remover:",
          options=list(opcoes_alunos.keys()),
          format_func=lambda x: opcoes_alunos[x],
          key="select_excluir_aluno",
      )

    with col_ex2:
      st.write("")
      st.write("")
      btn_excluir = st.button("❌ Excluir Aluno", use_container_width=True)

    if btn_excluir:
      df_alunos_restantes = df_alunos[df_alunos["id"] != aluno_id_selecionado]
      conn.update(worksheet="Alunos", data=df_alunos_restantes)
      st.success("Aluno removido da planilha com sucesso!")
      st.rerun()
