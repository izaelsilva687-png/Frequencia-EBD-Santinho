import datetime
import pandas as pd
import plotly.express as px
import streamlit as st

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
    "1. OFICIAIS",
    "2. BERÇARIO",
    "3. JARDIM DE INFÂNCIA",
    "4. JUNIORES",
    "5. PRÉ-ADOLESCENTES",
    "6. VENCEDORES POR CRISTO",
    "7. LÍRIOS DO VALE",
]

# -----------------------------------------------------------------------------
# BANCO DE DADOS EM MEMÓRIA / ARQUIVO LOCAL (Com suporte a Google Sheets)
# -----------------------------------------------------------------------------
# Inicialização de alunos demonstrativos (caso não haja cadastro prévio)
if "db_alunos" not in st.session_state:
  st.session_state["db_alunos"] = pd.DataFrame([
      {"id": 1, "nome": "João Silva", "turma": "4. Jovens", "ativo": True},
      {"id": 2, "nome": "Maria Santos", "turma": "4. Jovens", "ativo": True},
      {"id": 3, "nome": "Pedro Oliveira", "turma": "4. Jovens", "ativo": True},
      {
          "id": 4,
          "nome": "Lucas Lima",
          "turma": "5. Adultos (Classe 1)",
          "ativo": True,
      },
      {
          "id": 5,
          "nome": "Ana Costa",
          "turma": "5. Adultos (Classe 1)",
          "ativo": True,
      },
  ])

if "db_chamadas" not in st.session_state:
  st.session_state["db_chamadas"] = pd.DataFrame(
      columns=["data", "turma", "aluno_id", "nome", "presente"]
  )

if "db_resumo_turma" not in st.session_state:
  st.session_state["db_resumo_turma"] = pd.DataFrame(
      columns=["data", "turma", "visitantes", "oferta"]
  )

# -----------------------------------------------------------------------------
# CABEÇALHO DO APLICATIVO
# -----------------------------------------------------------------------------
st.title("📖 Sistema de Frequência da Escola Dominical")
st.caption(
    "Gestão em tempo real das 7 turmas da EBD — Chamada Nominal e Relatórios"
    " Consolidados"
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
    data_aula = st.date_input("Data da Aula:", datetime.date.today())

  st.markdown("---")

  # Filtrar alunos cadastrados e ativos da turma selecionada
  df_alunos_turma = st.session_state["db_alunos"][
      (st.session_state["db_alunos"]["turma"] == turma_prof)
      & (st.session_state["db_alunos"]["ativo"] == True)
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

    # Formulário de Chamada
    with st.form(key=f"form_chamada_{turma_prof}"):
      presencas = {}
      cols_alunos = st.columns(2)

      for idx, row in df_alunos_turma.reset_index(drop=True).iterrows():
        col_target = cols_alunos[idx % 2]
        # Checkbox individual por aluno
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
        str_data = data_aula.strftime("%Y-%m-%d")

        # 1. Limpar chamada anterior da mesma data/turma se houver sobrescrita
        st.session_state["db_chamadas"] = st.session_state["db_chamadas"][
            ~(
                (st.session_state["db_chamadas"]["data"] == str_data)
                & (st.session_state["db_chamadas"]["turma"] == turma_prof)
            )
        ]

        st.session_state["db_resumo_turma"] = st.session_state[
            "db_resumo_turma"
        ][
            ~(
                (st.session_state["db_resumo_turma"]["data"] == str_data)
                & (st.session_state["db_resumo_turma"]["turma"] == turma_prof)
            )
        ]

        # 2. Registrar chamadas individuais
        novas_chamadas = []
        for aluno_id, esteve_presente in presencas.items():
          nome_aluno = df_alunos_turma[
              df_alunos_turma["id"] == aluno_id
          ]["nome"].values[0]
          novas_chamadas.append({
              "data": str_data,
              "turma": turma_prof,
              "aluno_id": aluno_id,
              "nome": nome_aluno,
              "presente": esteve_presente,
          })

        df_novas = pd.DataFrame(novas_chamadas)
        st.session_state["db_chamadas"] = pd.concat(
            [st.session_state["db_chamadas"], df_novas], ignore_index=True
        )

        # 3. Registrar resumo de oferta/visitantes
        novo_resumo = pd.DataFrame([{
            "data": str_data,
            "turma": turma_prof,
            "visitantes": num_visitantes,
            "oferta": val_oferta,
        }])
        st.session_state["db_resumo_turma"] = pd.concat(
            [st.session_state["db_resumo_turma"], novo_resumo],
            ignore_index=True,
        )

        total_presentes_dia = sum(presencas.values())
        st.success(
            f"✅ Chamada da turma '{turma_prof}' salva com sucesso! "
            f"({total_presentes_dia} presentes, {num_visitantes} visitantes e"
            f" R$ {val_oferta:.2f} de oferta)."
        )

# =============================================================================
# ABA 2: RELATÓRIO DO DOMINGO (DIREÇÃO)
# =============================================================================
with aba_relatorio_domingo:
  st.subheader("📊 Painel Consolidado da Apuração de Domingo")

  col_r1, col_r2 = st.columns(2)
  with col_r1:
    filtro_data = st.date_input(
        "Data do Domingo:", datetime.date.today(), key="filtro_data_rel"
    )
  with col_r2:
    filtro_turma = st.selectbox(
        "Selecione o Escopo do Relatório:",
        ["🌟 CONSOLIDADO GERAL (Todas as 7 Turmas)"] + TURMAS,
    )

  str_filtro_data = filtro_data.strftime("%Y-%m-%d")

  # Obter dados de chamadas e resumos para a data
  df_ch_data = st.session_state["db_chamadas"][
      st.session_state["db_chamadas"]["data"] == str_filtro_data
  ]
  df_res_data = st.session_state["db_resumo_turma"][
      st.session_state["db_resumo_turma"]["data"] == str_filtro_data
  ]

  if "CONSOLIDADO GERAL" not in filtro_turma:
    df_ch_data = df_ch_data[df_ch_data["turma"] == filtro_turma]
    df_res_data = df_res_data[df_res_data["turma"] == filtro_turma]
    df_matr = st.session_state["db_alunos"][
        (st.session_state["db_alunos"]["turma"] == filtro_turma)
        & (st.session_state["db_alunos"]["ativo"] == True)
    ]
  else:
    df_matr = st.session_state["db_alunos"][
        st.session_state["db_alunos"]["ativo"] == True
    ]

  num_matriculados = len(df_matr)
  num_presentes = (
      df_ch_data["presente"].sum() if not df_ch_data.empty else 0
  )
  num_ausentes = max(0, num_matriculados - num_presentes)
  num_visitantes = (
      df_res_data["visitantes"].sum() if not df_res_data.empty else 0
  )
  presenca_total = num_presentes + num_visitantes
  total_oferta = df_res_data["oferta"].sum() if not df_res_data.empty else 0.0
  taxa_freq = (
      (num_presentes / num_matriculados * 100) if num_matriculados > 0 else 0
  )

  # CARTÕES DE MÉTRICAS EXIGIDOS
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

  # Tabela detalhada por turma caso seja o Consolidado
  if "CONSOLIDADO GERAL" in filtro_turma:
    st.write("### 📈 Resumo Comparativo por Turma")
    resumo_turmas_list = []

    for t in TURMAS:
      mat_t = len(
          st.session_state["db_alunos"][
              (st.session_state["db_alunos"]["turma"] == t)
              & (st.session_state["db_alunos"]["ativo"] == True)
          ]
      )
      ch_t = st.session_state["db_chamadas"][
          (st.session_state["db_chamadas"]["data"] == str_filtro_data)
          & (st.session_state["db_chamadas"]["turma"] == t)
      ]
      res_t = st.session_state["db_resumo_turma"][
          (st.session_state["db_resumo_turma"]["data"] == str_filtro_data)
          & (st.session_state["db_resumo_turma"]["turma"] == t)
      ]

      pres_t = ch_t["presente"].sum() if not ch_t.empty else 0
      aus_t = max(0, mat_t - pres_t)
      vis_t = res_t["visitantes"].sum() if not res_t.empty else 0
      p_tot_t = pres_t + vis_t
      ofe_t = res_t["oferta"].sum() if not res_t.empty else 0.0

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

    # Gráfico de Barras Comparativo
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

  if st.session_state["db_chamadas"].empty:
    st.info("Nenhuma chamada realizada ainda no sistema.")
  else:
    df_ch = st.session_state["db_chamadas"].copy()
    df_rank = (
        df_ch.groupby(["aluno_id", "nome", "turma"])
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
            st.session_state["db_alunos"]["id"].max() + 1
            if not st.session_state["db_alunos"].empty
            else 1
        )
        novo_aluno = pd.DataFrame([{
            "id": novo_id,
            "nome": nome_novo.strip(),
            "turma": turma_nova,
            "ativo": True,
        }])
        st.session_state["db_alunos"] = pd.concat(
            [st.session_state["db_alunos"], novo_aluno], ignore_index=True
        )
        st.success(
            f"Aluno **{nome_novo}** cadastrado com sucesso na turma"
            f" '{turma_nova}'!"
        )

  st.markdown("---")
  st.write("### 📋 Alunos Cadastrados no Sistema")
  st.dataframe(
      st.session_state["db_alunos"][
          st.session_state["db_alunos"]["ativo"] == True
      ][["id", "nome", "turma"]],
      hide_index=True,
      use_container_width=True,
  )
