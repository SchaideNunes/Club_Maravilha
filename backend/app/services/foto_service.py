"""
Armazenamento local das fotos dos sócios (enviadas pelo painel admin).

As fotos ficam em <UPLOADS_DIR>/associados/<associado_id>.<ext>. O tipo da imagem é detectado
pelos primeiros bytes do arquivo (assinatura), nunca pela extensão ou pelo Content-Type enviado.
"""
from pathlib import Path
from typing import Optional, Tuple
import uuid
from app.core.config import settings

# extensão -> media type
FORMATOS_ACEITOS = {
    "jpg": "image/jpeg",
    "png": "image/png",
    "webp": "image/webp",
}


def detectar_formato(conteudo: bytes) -> Optional[str]:
    """Retorna a extensão (jpg/png/webp) a partir da assinatura do arquivo, ou None."""
    if conteudo.startswith(b"\xff\xd8\xff"):
        return "jpg"
    if conteudo.startswith(b"\x89PNG\r\n\x1a\n"):
        return "png"
    if len(conteudo) >= 12 and conteudo[:4] == b"RIFF" and conteudo[8:12] == b"WEBP":
        return "webp"
    return None


def _pasta() -> Path:
    return Path(settings.UPLOADS_DIR) / "associados"


def remover_foto(associado_id: uuid.UUID) -> None:
    for extensao in FORMATOS_ACEITOS:
        (_pasta() / f"{associado_id}.{extensao}").unlink(missing_ok=True)


def salvar_foto(associado_id: uuid.UUID, conteudo: bytes, extensao: str) -> None:
    """Grava a nova foto substituindo a anterior (mesmo que em outro formato)."""
    pasta = _pasta()
    pasta.mkdir(parents=True, exist_ok=True)
    remover_foto(associado_id)
    (pasta / f"{associado_id}.{extensao}").write_bytes(conteudo)


def localizar_foto(associado_id: uuid.UUID) -> Optional[Tuple[Path, str]]:
    """Retorna (caminho, media type) da foto do sócio, se existir."""
    for extensao, media_type in FORMATOS_ACEITOS.items():
        caminho = _pasta() / f"{associado_id}.{extensao}"
        if caminho.is_file():
            return caminho, media_type
    return None
