"""
Roteador principal da API v1 agregando todos os sub-módulos do Club Maravilha.
Aplica proteção com get_current_admin em todas as rotas administrativas.
"""
from fastapi import APIRouter, Depends

from app.api.deps import get_current_admin
from app.api.v1.endpoints import (
    agendamentos,
    associados,
    auth,
    catraca,
    configuracao,
    convidados,
    dashboard,
    familia,
    faturas,
    health,
    planos,
    webhooks,
    whatsapp,
)

api_router = APIRouter()

# ------------------------------------------------------------------------------
# Rotas Públicas (Health, Login de Administrador, Webhooks de Pagamento e Catraca)
# ------------------------------------------------------------------------------
api_router.include_router(health.router, tags=["Saúde & Diagnóstico"])
api_router.include_router(auth.router, prefix="/auth", tags=["Autenticação"])
api_router.include_router(catraca.router, prefix="/catraca", tags=["Catraca Facial & Acesso"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks de Pagamento"])

# ------------------------------------------------------------------------------
# Rotas Administrativas Protegidas (exigem Depends(get_current_admin))
# Sub-routers incluídos aqui protegem todas as rotas presentes e futuras automaticamente.
# ------------------------------------------------------------------------------
admin_router = APIRouter(dependencies=[Depends(get_current_admin)])

admin_router.include_router(associados.router, prefix="/associados", tags=["Associados"])
admin_router.include_router(
    familia.router, prefix="/associados/{associado_id}/familia", tags=["Associados - Família"]
)
admin_router.include_router(planos.router, prefix="/planos", tags=["Planos de Mensalidade"])
admin_router.include_router(faturas.router, prefix="/faturas", tags=["Financeiro & Mensalidades"])
admin_router.include_router(agendamentos.router, prefix="/agendamentos", tags=["Quadras Esportivas"])
admin_router.include_router(convidados.router, prefix="/convidados", tags=["Gestão de Convidados & Visitantes"])
admin_router.include_router(whatsapp.router, prefix="/whatsapp", tags=["WhatsApp & Automação"])
admin_router.include_router(configuracao.router, prefix="/configuracao", tags=["Central de Configurações"])
admin_router.include_router(dashboard.router, prefix="/dashboard", tags=["Dashboard"])

api_router.include_router(admin_router)
