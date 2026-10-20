"""
Cadastro de Sócios - Foto do associado (upload pelo painel admin).

Contratos (prefixo /api/v1/associados/{id}/foto, rotas administrativas):
- PUT    multipart `file`  200 associado com foto_url "/api/v1/associados/{id}/foto?v=<n>"
                           | 404 associado | 413 acima de FOTO_MAX_BYTES | 415 não é JPEG/PNG/WEBP
                           (o tipo é verificado pelos bytes do arquivo, não pela extensão)
- GET                      200 bytes da imagem com o media type correto | 404 sem foto
- DELETE                   204 remove arquivo e limpa foto_url | 404 associado

Os arquivos ficam em <UPLOADS_DIR>/associados/<id>.<ext>; uma nova foto substitui a anterior.
"""
import uuid

import pytest
from httpx import AsyncClient

from app.core.config import settings

URL = "/api/v1/associados/"

PNG = b"\x89PNG\r\n\x1a\n" + b"\x00" * 64
JPEG = b"\xff\xd8\xff\xe0" + b"\x00" * 64
WEBP = b"RIFF\x24\x00\x00\x00WEBPVP8 " + b"\x00" * 64


@pytest.fixture(autouse=True)
def _uploads_temporarios(monkeypatch, tmp_path):
    monkeypatch.setattr(settings, "UPLOADS_DIR", str(tmp_path))
    return tmp_path


async def _socio(client: AsyncClient) -> dict:
    res = await client.post(URL, json={
        "nome": "Maria Maravilha", "cpf": "529.982.247-25", "whatsapp": "75999999999", "email": "maria@maravilha.com",
    })
    assert res.status_code == 201, res.text
    return res.json()


async def test_envia_le_e_substitui_foto(async_client: AsyncClient, _uploads_temporarios):
    socio = await _socio(async_client)

    res = await async_client.put(f"{URL}{socio['id']}/foto", files={"file": ("foto.png", PNG, "image/png")})
    assert res.status_code == 200, res.text
    assert res.json()["foto_url"].startswith(f"/api/v1/associados/{socio['id']}/foto?v=")
    assert (_uploads_temporarios / "associados" / f"{socio['id']}.png").exists()

    foto = await async_client.get(f"{URL}{socio['id']}/foto")
    assert foto.status_code == 200
    assert foto.headers["content-type"] == "image/png"
    assert foto.content == PNG

    # Substitui por um JPEG (nome de arquivo enganoso): vale o conteúdo, e o PNG antigo some
    res = await async_client.put(f"{URL}{socio['id']}/foto", files={"file": ("foto.png", JPEG, "image/png")})
    assert res.status_code == 200
    assert not (_uploads_temporarios / "associados" / f"{socio['id']}.png").exists()
    foto = await async_client.get(f"{URL}{socio['id']}/foto")
    assert foto.headers["content-type"] == "image/jpeg"
    assert foto.content == JPEG


async def test_aceita_webp(async_client: AsyncClient):
    socio = await _socio(async_client)
    res = await async_client.put(f"{URL}{socio['id']}/foto", files={"file": ("f.webp", WEBP, "image/webp")})
    assert res.status_code == 200, res.text
    assert (await async_client.get(f"{URL}{socio['id']}/foto")).headers["content-type"] == "image/webp"


async def test_rejeita_arquivo_que_nao_e_imagem(async_client: AsyncClient):
    socio = await _socio(async_client)
    res = await async_client.put(f"{URL}{socio['id']}/foto", files={"file": ("foto.jpg", b"%PDF-1.7 ...", "image/jpeg")})
    assert res.status_code == 415


async def test_rejeita_arquivo_grande(async_client: AsyncClient, monkeypatch):
    monkeypatch.setattr(settings, "FOTO_MAX_BYTES", 32)
    socio = await _socio(async_client)
    res = await async_client.put(f"{URL}{socio['id']}/foto", files={"file": ("foto.png", PNG, "image/png")})
    assert res.status_code == 413


async def test_remove_foto(async_client: AsyncClient, _uploads_temporarios):
    socio = await _socio(async_client)
    await async_client.put(f"{URL}{socio['id']}/foto", files={"file": ("foto.png", PNG, "image/png")})

    assert (await async_client.delete(f"{URL}{socio['id']}/foto")).status_code == 204
    assert (await async_client.get(f"{URL}{socio['id']}")).json()["foto_url"] is None
    assert (await async_client.get(f"{URL}{socio['id']}/foto")).status_code == 404
    assert not any((_uploads_temporarios / "associados").iterdir())


async def test_associado_inexistente_ou_sem_foto(async_client: AsyncClient):
    fake = uuid.uuid4()
    assert (await async_client.put(f"{URL}{fake}/foto", files={"file": ("f.png", PNG, "image/png")})).status_code == 404
    assert (await async_client.delete(f"{URL}{fake}/foto")).status_code == 404
    socio = await _socio(async_client)
    assert (await async_client.get(f"{URL}{socio['id']}/foto")).status_code == 404


async def test_foto_exige_autenticacao(async_client_sem_auth: AsyncClient):
    assert (await async_client_sem_auth.get(f"{URL}{uuid.uuid4()}/foto")).status_code == 401
