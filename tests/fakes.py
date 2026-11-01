"""Dublês de teste compartilhados entre os testes dos agentes."""


class FakeLLMClient:
    """LLMClient de teste: devolve ``respostas`` em ordem e repete a última."""

    def __init__(self, respostas: list[str]) -> None:
        if not respostas:
            raise ValueError("FakeLLMClient exige ao menos uma resposta")
        self.respostas = list(respostas)
        self.calls: list[tuple[str, str]] = []

    def complete(self, system: str, user: str) -> str:
        indice = min(len(self.calls), len(self.respostas) - 1)
        self.calls.append((system, user))
        return self.respostas[indice]
