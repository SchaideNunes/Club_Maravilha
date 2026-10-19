"""
Limitador em memória de tentativas de login por chave (IP + e-mail).
"""
import math
import time
from typing import Callable, Dict, List


class LoginRateLimiter:
    """
    Limitador deslizante em memória para tentativas de login inválidas com teto de capacidade.
    """

    def __init__(
        self,
        max_falhas: int = 5,
        janela_segundos: int = 60,
        max_chaves: int = 10000,
        relogio: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_falhas = max_falhas
        self.janela_segundos = janela_segundos
        self.max_chaves = max_chaves
        self.relogio = relogio
        self._falhas: Dict[str, List[float]] = {}

    def _limpar_expiradas(self, chave: str, agora: float) -> List[float]:
        if chave not in self._falhas:
            return []
        limite = agora - self.janela_segundos
        recentes = [t for t in self._falhas.get(chave, []) if t > limite]
        if not recentes:
            self._falhas.pop(chave, None)
            return []
        self._falhas[chave] = recentes
        return recentes

    def bloqueado(self, chave: str) -> bool:
        if chave not in self._falhas:
            return False
        agora = self.relogio()
        recentes = self._limpar_expiradas(chave, agora)
        return len(recentes) >= self.max_falhas

    def registrar_falha(self, chave: str) -> None:
        agora = self.relogio()
        if chave not in self._falhas and len(self._falhas) >= self.max_chaves:
            # Descarte da chave mais antiga (inserção FIFO em Python dict)
            chave_mais_antiga = next(iter(self._falhas))
            del self._falhas[chave_mais_antiga]

        falhas = self._falhas.setdefault(chave, [])
        falhas.append(agora)
        self._limpar_expiradas(chave, agora)

    def registrar_requisicao(self, chave: str) -> None:
        """Alias semântico para registrar uma requisição/operação contabilizada no limitador."""
        self.registrar_falha(chave)

    def limpar(self, chave: str) -> None:
        self._falhas.pop(chave, None)

    def segundos_para_liberar(self, chave: str) -> int:
        if chave not in self._falhas:
            return 0
        agora = self.relogio()
        recentes = self._limpar_expiradas(chave, agora)
        if len(recentes) < self.max_falhas:
            return 0
        indice_critico = len(recentes) - self.max_falhas
        falha_critica = recentes[indice_critico]
        restante = self.janela_segundos - (agora - falha_critica)
        return max(1, math.ceil(restante))

    def reset(self) -> None:
        self._falhas.clear()


RateLimiter = LoginRateLimiter

login_rate_limiter = LoginRateLimiter(max_falhas=5, janela_segundos=60, max_chaves=10000)
teste_envio_rate_limiter = LoginRateLimiter(max_falhas=5, janela_segundos=60, max_chaves=10000)
