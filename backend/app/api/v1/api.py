"""
Roteador principal da API v1 agregando todos os sub-módulos do Club Maravilha.
"""
from fastapi import APIRouter
from app.api.v1.endpoints import (
    agendamentos,
    associados,
    catraca,
    convidados,
    faturas,
    health,
    webhooks,
    whatsapp,
)

api_router = APIRouter()

api_router.include_router(health.router, tags=["Saúde & Diagnóstico"])
api_router.include_router(associados.router, prefix="/associados", tags=["Associados"])
api_router.include_router(faturas.router, prefix="/faturas", tags=["Financeiro & Mensalidades"])
api_router.include_router(agendamentos.router, prefix="/agendamentos", tags=["Quadras Esportivas"])
api_router.include_router(convidados.router, prefix="/convidados", tags=["Gestão de Convidados & Visitantes"])
api_router.include_router(catraca.router, prefix="/catraca", tags=["Catraca Facial & Acesso"])
api_router.include_router(webhooks.router, prefix="/webhooks", tags=["Webhooks de Pagamento"])
api_router.include_router(whatsapp.router, prefix="/whatsapp", tags=["WhatsApp & Automação"])

