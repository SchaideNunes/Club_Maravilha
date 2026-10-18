"""
Modelo da tabela de Configurações do clube (singleton, sempre id = 1).
Centraliza as regras financeiras, o agendamento da régua de cobrança e os
templates de mensagem de WhatsApp editáveis pelo painel administrativo.
"""
from decimal import Decimal
from typing import Optional
from sqlalchemy import Boolean, CheckConstraint, Integer, Numeric, String, Text
from sqlalchemy.orm import Mapped, mapped_column
from app.core.config import settings
from app.models.base import Base, TimestampMixin

# Identificador fixo do único registro da tabela
CONFIGURACAO_ID = 1

# Variáveis aceitas nos templates, escritas entre chaves (ex: "{nome}")
VARIAVEIS_TEMPLATE = (
    "nome",
    "valor_base",
    "convites_usados",
    "convites_extras",
    "valor_total",
    "vencimento",
    "chave_pix",
)

TEMPLATE_D_MENOS_3_PADRAO = (
    "Olá, {nome}! Sua mensalidade do Club Maravilha vence em {vencimento}.\n\n"
    "Resumo da fatura:\n"
    "- Mensalidade: R$ {valor_base}\n"
    "- Convites usados no mês: {convites_usados} ({convites_extras} excedente(s))\n"
    "- Total: R$ {valor_total}\n\n"
    "Para pagar via Pix, use a chave: {chave_pix}\n\n"
    "Qualquer dúvida, é só responder esta mensagem."
)

TEMPLATE_D0_PADRAO = (
    "Bom dia, {nome}! Sua mensalidade do Club Maravilha vence hoje ({vencimento}).\n\n"
    "Valor total: R$ {valor_total}\n"
    "(Mensalidade R$ {valor_base} + {convites_extras} convite(s) excedente(s))\n\n"
    "Pague via Pix usando a chave:\n"
    "{chave_pix}\n\n"
    "Assim que o pagamento for confirmado, você receberá o recibo por aqui."
)

TEMPLATE_RECIBO_PADRAO = (
    "Olá, {nome}! Recebemos o pagamento da sua mensalidade no valor de R$ {valor_total}.\n\n"
    "Seu acesso ao Club Maravilha está regularizado. Obrigado e até breve!"
)

TEMPLATE_D_MAIS_3_PADRAO = (
    "Olá, {nome}! Identificamos que a sua mensalidade do Club Maravilha, "
    "com vencimento em {vencimento}, ainda está em aberto.\n\n"
    "Valor total: R$ {valor_total}\n"
    "Chave Pix: {chave_pix}\n\n"
    "Se você já pagou, por favor desconsidere esta mensagem."
)

TEMPLATE_D_MAIS_7_PADRAO = (
    "Atenção, {nome}! Sua mensalidade do Club Maravilha (vencimento em {vencimento}) "
    "está em atraso há 7 dias e o seu acesso ao clube será bloqueado até a regularização.\n\n"
    "Valor total: R$ {valor_total}\n"
    "Chave Pix: {chave_pix}\n\n"
    "Após o pagamento, a liberação é imediata. Se precisar de ajuda, responda esta mensagem."
)


def _decimal_monetario(valor: float) -> Decimal:
    """Converte um valor float de `settings` em Decimal com 2 casas, sem ruído binário."""
    return Decimal(str(valor)).quantize(Decimal("0.01"))


class Configuracao(Base, TimestampMixin):
    """
    Configurações globais do clube. A tabela mantém exatamente um registro
    (id = 1, garantido por CHECK) e os defaults vêm das regras de negócio do `settings`.

    Regras associadas:
    1. `valor_mensalidade`, `franquia_convidados` e `valor_convidado_extra` compõem o
       cálculo da fatura: valor_base + convidados excedentes * valor_convidado_extra.
    2. `horario_disparo` (HH:MM) e `automacao_ativa` controlam a régua diária de cobrança.
    3. Cada etapa da régua (D-3, D-0, recibo, D+3, D+7) usa um template editável
       com as variáveis de `VARIAVEIS_TEMPLATE`.
    """
    __tablename__ = "configuracoes"
    __table_args__ = (
        CheckConstraint(f"id = {CONFIGURACAO_ID}", name="ck_configuracoes_singleton"),
    )

    id: Mapped[int] = mapped_column(
        Integer,
        primary_key=True,
        autoincrement=False,
        default=CONFIGURACAO_ID,
    )

    # Regras financeiras
    valor_mensalidade: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=lambda: _decimal_monetario(settings.VALOR_MENSALIDADE_PADRAO),
        nullable=False,
        comment="Valor padrão da mensalidade"
    )
    franquia_convidados: Mapped[int] = mapped_column(
        Integer,
        default=lambda: settings.FRANQUIA_CONVITES_MENSAL,
        nullable=False,
        comment="Quantidade de convites gratuitos por sócio a cada mês"
    )
    valor_convidado_extra: Mapped[Decimal] = mapped_column(
        Numeric(10, 2),
        default=lambda: _decimal_monetario(settings.VALOR_CONVITE_EXCEDENTE),
        nullable=False,
        comment="Valor cobrado por convite que exceder a franquia mensal"
    )
    chave_pix: Mapped[Optional[str]] = mapped_column(
        String(150),
        nullable=True,
        comment="Chave Pix do clube informada nas mensagens de cobrança"
    )

    # Régua de cobrança
    horario_disparo: Mapped[str] = mapped_column(
        String(5),
        default="08:00",
        nullable=False,
        comment="Horário (HH:MM) do disparo diário da régua de cobrança"
    )
    automacao_ativa: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        nullable=False,
        comment="Liga/desliga o disparo automático da régua de cobrança"
    )

    # Templates de mensagem (variáveis: ver VARIAVEIS_TEMPLATE)
    template_d_menos_3: Mapped[str] = mapped_column(Text, default=TEMPLATE_D_MENOS_3_PADRAO, nullable=False)
    template_d0: Mapped[str] = mapped_column(Text, default=TEMPLATE_D0_PADRAO, nullable=False)
    template_recibo: Mapped[str] = mapped_column(Text, default=TEMPLATE_RECIBO_PADRAO, nullable=False)
    template_d_mais_3: Mapped[str] = mapped_column(Text, default=TEMPLATE_D_MAIS_3_PADRAO, nullable=False)
    template_d_mais_7: Mapped[str] = mapped_column(Text, default=TEMPLATE_D_MAIS_7_PADRAO, nullable=False)

    def calcular_convidados_excedentes(self, convidados_usados: int) -> int:
        """Quantidade de convites que ultrapassaram a franquia mensal."""
        return max(0, convidados_usados - self.franquia_convidados)

    def calcular_valor_excedentes(self, convidados_usados: int) -> Decimal:
        """Valor a cobrar pelos convites que excederam a franquia: excedentes * valor_convidado_extra."""
        excedentes = self.calcular_convidados_excedentes(convidados_usados)
        return (self.valor_convidado_extra * excedentes).quantize(Decimal("0.01"))

    def __repr__(self) -> str:
        return (
            f"<Configuracao(id={self.id}, mensalidade={self.valor_mensalidade}, "
            f"franquia={self.franquia_convidados}, automacao_ativa={self.automacao_ativa})>"
        )
