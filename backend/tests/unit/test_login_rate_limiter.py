"""
Feature 5 - Limitador em memória de tentativas de login (app/core/rate_limit.py).

Contrato:
- `LoginRateLimiter(max_falhas=5, janela_segundos=60, relogio=time.monotonic)` com atributos
  `max_falhas`/`janela_segundos` e métodos:
    bloqueado(chave) -> bool              # True quando há >= max_falhas falhas dentro da janela deslizante
    registrar_falha(chave) -> None
    limpar(chave) -> None                 # zera as falhas da chave (login bem-sucedido)
    segundos_para_liberar(chave) -> int   # >= 1 enquanto bloqueado; 0 quando liberado
    reset() -> None                       # zera tudo (usado pelo conftest entre testes)
- Instância global `login_rate_limiter` (5 falhas / 60 s) usada pelo POST /auth/login com chave
  IP + e-mail normalizado.
"""
from app.core.rate_limit import LoginRateLimiter, login_rate_limiter


class Relogio:
    def __init__(self) -> None:
        self.agora = 1000.0

    def __call__(self) -> float:
        return self.agora


def test_bloqueia_apos_max_falhas_na_janela():
    limiter = LoginRateLimiter(max_falhas=5, janela_segundos=60, relogio=Relogio())

    for _ in range(4):
        limiter.registrar_falha("ip|a@b.com")
    assert limiter.bloqueado("ip|a@b.com") is False

    limiter.registrar_falha("ip|a@b.com")
    assert limiter.bloqueado("ip|a@b.com") is True
    assert 1 <= limiter.segundos_para_liberar("ip|a@b.com") <= 60


def test_falhas_expiram_apos_a_janela():
    relogio = Relogio()
    limiter = LoginRateLimiter(max_falhas=5, janela_segundos=60, relogio=relogio)
    for _ in range(5):
        limiter.registrar_falha("k")

    relogio.agora += 61

    assert limiter.bloqueado("k") is False
    assert limiter.segundos_para_liberar("k") == 0


def test_janela_deslizante_conta_so_falhas_recentes():
    relogio = Relogio()
    limiter = LoginRateLimiter(max_falhas=3, janela_segundos=60, relogio=relogio)
    limiter.registrar_falha("k")
    relogio.agora += 40
    limiter.registrar_falha("k")
    relogio.agora += 30  # a primeira falha saiu da janela
    limiter.registrar_falha("k")

    assert limiter.bloqueado("k") is False


def test_chaves_sao_independentes_e_limpar_zera():
    limiter = LoginRateLimiter(max_falhas=2, janela_segundos=60, relogio=Relogio())
    limiter.registrar_falha("a")
    limiter.registrar_falha("a")

    assert limiter.bloqueado("a") is True
    assert limiter.bloqueado("b") is False

    limiter.limpar("a")
    assert limiter.bloqueado("a") is False


def test_reset_zera_todas_as_chaves():
    limiter = LoginRateLimiter(max_falhas=1, janela_segundos=60, relogio=Relogio())
    limiter.registrar_falha("a")
    limiter.registrar_falha("b")
    limiter.reset()
    assert not limiter.bloqueado("a") and not limiter.bloqueado("b")


def test_instancia_global_padrao():
    assert isinstance(login_rate_limiter, LoginRateLimiter)
    assert login_rate_limiter.max_falhas == 5
    assert login_rate_limiter.janela_segundos == 60
