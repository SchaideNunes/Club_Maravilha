"""
Testes de integração para as correções de Code Review da Feature 2:
1. Validação de CPF de convidado (rejeição de '123' com 422 em ambos os endpoints)
2. Preservação de dia_vencimento no upsert de importação via API
3. Limites de upload (413 para > 5MB, 400 para > 5000 linhas, 400 para CSV malformado)
4. Paridade estrita de elegibilidade entre POST /associados/{id}/convidados e POST /convidados/
5. Paginação estável e determinística com associados homônimos (sem repetição entre páginas)
"""
import io
import uuid
from datetime import date
from decimal import Decimal
import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import settings
from app.models.associado import Associado, StatusAssociado
from app.models.fatura import Fatura, StatusFatura


async def _criar_associado(
    db_session: AsyncSession,
    nome: str = "Titular Teste Review",
    cpf: str = "529.982.247-25",
    status: StatusAssociado = StatusAssociado.ATIVO,
    dia_vencimento: int = 10,
    email: str = "titular.review@clube.com"
) -> Associado:
    socio = Associado(
        nome=nome,
        cpf=cpf,
        whatsapp="5575999990000",
        email=email,
        status=status,
        dia_vencimento=dia_vencimento,
    )
    db_session.add(socio)
    await db_session.commit()
    return socio


# ---------------------------------------------------------------------------
# 1. Validação de CPF de convidado: 422 com "123"
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_post_convidado_rapido_com_cpf_invalido_retorna_422(async_client: AsyncClient, db_session: AsyncSession):
    socio = await _criar_associado(db_session, email="cpf_inv1@clube.com")
    res = await async_client.post(
        f"/api/v1/associados/{socio.id}/convidados",
        json={"nome": "Convidado Teste", "cpf": "123"}
    )
    assert res.status_code == 422
    assert "CPF deve conter exatamente 11 dígitos" in res.text


@pytest.mark.asyncio
async def test_post_convidado_legado_com_cpf_invalido_retorna_422(async_client: AsyncClient, db_session: AsyncSession):
    socio = await _criar_associado(db_session, email="cpf_inv2@clube.com")
    res = await async_client.post(
        "/api/v1/convidados/",
        json={
            "associado_titular_id": str(socio.id),
            "nome": "Convidado Legado Inválido",
            "data_visita": date.today().isoformat(),
            "cpf": "123"
        }
    )
    assert res.status_code == 422
    assert "CPF deve conter exatamente 11 dígitos" in res.text


@pytest.mark.asyncio
async def test_post_convidado_aceita_cpf_valido_ou_vazio(async_client: AsyncClient, db_session: AsyncSession):
    socio = await _criar_associado(db_session, email="cpf_val@clube.com")

    # CPF vazio => grava None sem erro
    r1 = await async_client.post(
        f"/api/v1/associados/{socio.id}/convidados",
        json={"nome": "Convidado Sem CPF", "cpf": ""}
    )
    assert r1.status_code == 201
    assert r1.json()["convidado"]["cpf"] is None

    # CPF válido sem máscara => normaliza para 000.000.000-00
    r2 = await async_client.post(
        f"/api/v1/associados/{socio.id}/convidados",
        json={"nome": "Convidado CPF Válido", "cpf": "52998224725"}
    )
    assert r2.status_code == 201
    assert r2.json()["convidado"]["cpf"] == "529.982.247-25"


# ---------------------------------------------------------------------------
# 2. Upsert e dia_vencimento
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upsert_reimportacao_sem_coluna_vencimento_preserva_dia_existente(
    async_client: AsyncClient,
    db_session: AsyncSession
):
    # 1. Cria sócio com vencimento dia 5
    socio = await _criar_associado(
        db_session,
        nome="Sócio Vencimento Cinco",
        cpf="529.982.247-25",
        dia_vencimento=5,
        email="cinco@clube.com"
    )
    assert socio.dia_vencimento == 5

    # 2. Reimporta planilha CSV SEM coluna de vencimento
    csv_sem_venc = (
        "Nome,CPF,WhatsApp,Email\n"
        "Sócio Vencimento Cinco Novo Nome,529.982.247-25,5575999990000,cinco@clube.com\n"
    )
    files = {"file": ("planilha_sem_venc.csv", io.BytesIO(csv_sem_venc.encode("utf-8")), "text/csv")}
    res_import = await async_client.post(
        "/api/v1/associados/importar",
        params={"atualizar_existentes": "true"},
        files=files
    )
    assert res_import.status_code == 200
    assert res_import.json()["total_atualizados"] == 1

    # 3. Consulta detalhes via GET: nome atualizou, mas dia_vencimento PERMANECEU 5
    res_detalhe = await async_client.get(f"/api/v1/associados/{socio.id}")
    assert res_detalhe.status_code == 200
    body = res_detalhe.json()
    assert body["nome"] == "Sócio Vencimento Cinco Novo Nome"
    assert body["dia_vencimento"] == 5


# ---------------------------------------------------------------------------
# 3. Limites de upload: 413 (> 5MB), 400 (> 5000 linhas), 400 (CSV malformado)
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_upload_arquivo_maior_que_limite_retorna_413(async_client: AsyncClient):
    # Cria payload artificial com 5 MB + 10 bytes
    excesso = settings.IMPORT_MAX_BYTES + 10
    arquivo_gigante = b"X" * excesso

    files = {"file": ("gigante.csv", io.BytesIO(arquivo_gigante), "text/csv")}
    res = await async_client.post("/api/v1/associados/importar", files=files)
    assert res.status_code == 413
    assert "limite máximo permitido" in res.json()["detail"]


@pytest.mark.asyncio
async def test_upload_arquivo_com_mais_de_5000_linhas_retorna_400(async_client: AsyncClient):
    linhas = ["Nome,CPF,WhatsApp,Email"]
    for i in range(5002):
        linhas.append(f"Pessoa {i},529.982.247-25,5575999990000,p{i}@clube.com")
    csv_bytes = "\n".join(linhas).encode("utf-8")

    files = {"file": ("muitas_linhas.csv", io.BytesIO(csv_bytes), "text/csv")}
    res = await async_client.post("/api/v1/associados/importar", files=files)
    assert res.status_code == 400
    assert "limite máximo permitido de 5000 linhas" in res.json()["detail"]


@pytest.mark.asyncio
async def test_upload_excel_corrompido_retorna_400_sem_vazar_internals(async_client: AsyncClient):
    lixo_binario = b"\x00\x01\x02\x03\x04\x05\x06\x07"
    files = {"file": ("danificado.xlsx", io.BytesIO(lixo_binario), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")}
    res = await async_client.post("/api/v1/associados/importar", files=files)
    assert res.status_code == 400
    assert res.json()["detail"] == "Arquivo Excel corrompido ou inválido."


# ---------------------------------------------------------------------------
# 4. Paridade estrita de elegibilidade entre os dois endpoints de convidados
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_paridade_elegibilidade_associado_bloqueado_retorna_403(async_client: AsyncClient, db_session: AsyncSession):
    socio_bloq = await _criar_associado(db_session, status=StatusAssociado.BLOQUEADO, email="bloq_par@clube.com")

    # Endpoint rápido
    r1 = await async_client.post(
        f"/api/v1/associados/{socio_bloq.id}/convidados",
        json={"nome": "Visitante 1"}
    )
    assert r1.status_code == 403
    assert "bloqueado" in r1.json()["detail"].lower()

    # Endpoint legado
    r2 = await async_client.post(
        "/api/v1/convidados/",
        json={
            "associado_titular_id": str(socio_bloq.id),
            "nome": "Visitante 2",
            "data_visita": date.today().isoformat()
        }
    )
    assert r2.status_code == 403
    assert "bloqueado" in r2.json()["detail"].lower()


@pytest.mark.asyncio
async def test_paridade_elegibilidade_fatura_atrasada_retorna_403(async_client: AsyncClient, db_session: AsyncSession):
    socio = await _criar_associado(db_session, email="fatura_par@clube.com")
    fatura = Fatura(
        associado_id=socio.id,
        status=StatusFatura.ATRASADA,
        valor_base=Decimal("150.00"),
        valor_total=Decimal("150.00"),
        data_vencimento=date(2026, 9, 10),
        referencia_mes="2026-09",
    )
    db_session.add(fatura)
    await db_session.commit()

    # Ambos os endpoints devem bloquear emissão quando há fatura atrasada
    r1 = await async_client.post(
        f"/api/v1/associados/{socio.id}/convidados",
        json={"nome": "Visitante Fatura"}
    )
    assert r1.status_code == 403
    assert "mensalidade vencida" in r1.json()["detail"].lower()

    r2 = await async_client.post(
        "/api/v1/convidados/",
        json={
            "associado_titular_id": str(socio.id),
            "nome": "Visitante Fatura 2",
            "data_visita": date.today().isoformat()
        }
    )
    assert r2.status_code == 403
    assert "mensalidade vencida" in r2.json()["detail"].lower()


# ---------------------------------------------------------------------------
# 5. Paginação estável com homônimos
# ---------------------------------------------------------------------------

@pytest.mark.asyncio
async def test_paginacao_estavel_com_dois_homonimos_sem_repeticao(async_client: AsyncClient, db_session: AsyncSession):
    # Cria dois sócios com o MESMO nome
    s1 = await _criar_associado(
        db_session,
        nome="Lucas Maravilha Homonimo",
        cpf="529.982.247-25",
        email="homonimo1@clube.com"
    )
    s2 = await _criar_associado(
        db_session,
        nome="Lucas Maravilha Homonimo",
        cpf="729.982.247-33",
        email="homonimo2@clube.com"
    )

    # Página 1 com page_size=1
    r_pag1 = await async_client.get(
        "/api/v1/associados/",
        params={"q": "Lucas Maravilha Homonimo", "page": 1, "page_size": 1}
    )
    assert r_pag1.status_code == 200
    body1 = r_pag1.json()
    assert body1["total"] == 2
    assert len(body1["items"]) == 1
    id_pag1 = body1["items"][0]["id"]

    # Página 2 com page_size=1
    r_pag2 = await async_client.get(
        "/api/v1/associados/",
        params={"q": "Lucas Maravilha Homonimo", "page": 2, "page_size": 1}
    )
    assert r_pag2.status_code == 200
    body2 = r_pag2.json()
    assert body2["total"] == 2
    assert len(body2["items"]) == 1
    id_pag2 = body2["items"][0]["id"]

    # Os IDs devem ser distintos e cobrir s1 e s2 (sem registros duplicados entre páginas)
    assert id_pag1 != id_pag2
    assert set([id_pag1, id_pag2]) == {str(s1.id), str(s2.id)}
