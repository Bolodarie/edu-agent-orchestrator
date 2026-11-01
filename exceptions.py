class AgentPipelineError(Exception):
    recuperavel: bool = False


class IntencaoDesconhecidaError(AgentPipelineError):
    recuperavel = False


class SQLRejeitadoError(AgentPipelineError):
    recuperavel = True


class SQLExecucaoError(AgentPipelineError):
    recuperavel = True


class SaidaDoAgenteInvalidaError(AgentPipelineError):
    recuperavel = True
