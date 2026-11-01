"""Front-end Streamlit. Conhece só ``orchestrator`` e ``models`` (spec 4.1/4.9).

O histórico em ``st.session_state`` existe apenas para redesenhar o chat: cada
mensagem do assistente guarda o ``OrchestratorResponse`` pronto, então redesenhar
nunca reexecuta o pipeline. O orquestrador em si não recebe histórico.
"""

import streamlit as st

from models import OrchestratorResponse
from orchestrator import Orchestrator, build_orchestrator

TITULO = "Assistente de Álgebra"
LEGENDA = (
    "Peça exercícios, resumos teóricos ou resoluções passo a passo. "
    "Exemplo: \"exercícios de equação do 2º grau\"."
)
PLACEHOLDER = "Pergunte sobre álgebra..."
TITULO_EXPANDER = "Como a resposta foi gerada"


@st.cache_resource
def get_orchestrator() -> Orchestrator:
    return build_orchestrator()


def render_trace(response: OrchestratorResponse) -> None:
    trace = response.trace
    with st.expander(TITULO_EXPANDER):
        if trace.intent is not None:
            confianca = f"{trace.confidence:.0%}" if trace.confidence is not None else "n/d"
            st.markdown(f"**Intenção:** `{trace.intent.value}` (confiança: {confianca})")
        else:
            st.markdown("**Intenção:** não identificada")

        if trace.attempts:
            st.markdown("**Tentativas de SQL:**")
            for numero, tentativa in enumerate(trace.attempts, start=1):
                st.markdown(f"Tentativa {numero}")
                st.code(tentativa.sql or "(nenhum SQL gerado)", language="sql")
                if tentativa.error:
                    st.markdown(f"Erro: {tentativa.error}")
                if tentativa.row_count is not None:
                    st.markdown(f"Linhas devolvidas: {tentativa.row_count}")
        else:
            st.markdown("**Tentativas de SQL:** nenhuma")

        if trace.avisos:
            st.markdown("**Avisos:**")
            for aviso in trace.avisos:
                st.markdown(f"- {aviso}")

        if trace.tempos_ms:
            st.markdown("**Tempos (ms):**")
            for etapa, ms in trace.tempos_ms.items():
                st.markdown(f"- {etapa}: {ms:.1f}")


def render_response(response: OrchestratorResponse) -> None:
    if response.status == "ok":
        st.markdown(response.text)
    elif response.status == "erro":
        st.error(response.text)
    elif response.status == "fora_do_escopo":
        st.info(response.text)
    else:  # sem_resultados
        st.warning(response.text)
    render_trace(response)


def render_message(message: dict) -> None:
    with st.chat_message(message["role"]):
        if message["role"] == "user":
            st.markdown(message["text"])
        else:
            render_response(message["response"])


def main() -> None:
    st.set_page_config(page_title=TITULO, page_icon="📐")
    st.title(TITULO)
    st.caption(LEGENDA)

    if "messages" not in st.session_state:
        st.session_state.messages = []

    for message in st.session_state.messages:
        render_message(message)

    pergunta = st.chat_input(PLACEHOLDER)
    if pergunta:
        user_message = {"role": "user", "text": pergunta}
        st.session_state.messages.append(user_message)
        render_message(user_message)

        with st.spinner("Pensando..."):
            response = get_orchestrator().handle(pergunta)
        assistant_message = {"role": "assistant", "response": response}
        st.session_state.messages.append(assistant_message)
        render_message(assistant_message)


main()
