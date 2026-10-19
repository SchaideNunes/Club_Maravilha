"""
Constantes centrais de regras de negócio do Club Maravilha.
"""

# Dia da régua em que é enviado o aviso de carência (D+7). Não altera o status do associado.
DIAS_AVISO_CARENCIA: int = 7

# Prazo (1 mês de atraso) antes do bloqueio físico na catraca e da transição para inadimplente
DIAS_CARENCIA_BLOQUEIO: int = 30
