"""
Limitador em memória de tentativas de login por chave (IP + e-mail).
"""
import math
import time
from collections import defaultdict
from typing import Callable, Dict, List


class LoginRateLimiter:
    """
    Limitador deslizante em memória para tentativas de login inválidas.
    """

    def __init__(
        self,
        max_falhas: int = 5,
        janela_segundos: int = 60,
        relogio: Callable[[], float] = time.monotonic,
    ) -> None:
        self.max_falhas = max_falhas
        self.janela_segundos = janela_segundos
        self.relogio = relogio
        self._falhas: Dict[str, List[float]] = defaultdict(list)

    def _limpar_expiradas(self, chave: str, agora: float) -> List[float]:
        limite = agora - self.janela_segundos
        recentes = [t for t in self._falhas[chave] if t > limite]
        self._falhas[chave] = recentes
        return recentes

    def bloqueado(self, chave: str) -> bool:
        agora = self.relogio()
        recentes = self._limpar_expiradas(chave, agora)
        return len(recentes) >= self.max_falhas

    def registrar_falha(self, chave: str) -> None:
        agora = self.relogio()
        self._falhas[chave].append(agora)
        self._limpar_expiradas(chave, agora)

    def limpar(self, chave: str) -> None:
        if chave in self._falhas:
            del self._falhas[chave]

    def segundos_para_liberar(self, chave: str) -> int:
        agora = self.relogio()
        recentes = self._limpar_expiradas(chave, agora)
        if len(recentes) < self.max_falhas:
            return 0
        # A falha que causou o atingimento do limite precisa sair da janela
        indice_critico = len(recentes) - self.max_falhas
        falha_critica = recentes[indice_critico]
        restante = self.janela_segundos - (agora - falha_critica)
        return max(1, math.ceil(restante))

    def reset(self) -> None:
        self._falhas.clear()


login_rate_limiter = LoginRateLimiter(max_falhas=5, janela_segundos=60)
