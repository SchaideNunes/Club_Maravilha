import React, { useEffect, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { Camera, Trash2 } from 'lucide-react';
import { apiClient } from '../../api/client';
import { extrairMensagemErro } from '../../api/errors';
import { Associado } from './tipos';

function iniciais(nome: string): string {
  const partes = nome.trim().split(/\s+/);
  return ((partes[0]?.[0] ?? '') + (partes.length > 1 ? partes[partes.length - 1][0] : '')).toUpperCase();
}

/**
 * A rota da foto exige o token do admin, que um <img src> não envia: a imagem é baixada pelo
 * apiClient como blob e exibida por uma URL temporária (revogada ao trocar de foto).
 */
function useUrlDaFoto(associado: Associado): string | null {
  const { data: blob } = useQuery<Blob>({
    queryKey: ['foto-associado', associado.id, associado.foto_url],
    queryFn: async () =>
      (await apiClient.get<Blob>(`/associados/${associado.id}/foto`, { responseType: 'blob' })).data,
    enabled: Boolean(associado.foto_url),
    staleTime: Infinity,
  });
  const [url, setUrl] = useState<string | null>(null);

  useEffect(() => {
    if (!blob || !associado.foto_url || typeof URL.createObjectURL !== 'function') {
      setUrl(null);
      return;
    }
    const objeto = URL.createObjectURL(blob);
    setUrl(objeto);
    return () => URL.revokeObjectURL(objeto);
  }, [blob, associado.foto_url]);

  return url;
}

export type FotoAssociadoProps = {
  associado: Associado;
  onAtualizado: (associado: Associado) => void;
};

export function FotoAssociado({ associado, onAtualizado }: FotoAssociadoProps): React.ReactElement {
  const url = useUrlDaFoto(associado);
  const [enviando, setEnviando] = useState(false);
  const [erro, setErro] = useState<string | null>(null);

  const enviar = async (arquivo: File | undefined) => {
    if (!arquivo) return;
    setEnviando(true);
    setErro(null);
    try {
      const formData = new FormData();
      formData.append('file', arquivo);
      const { data } = await apiClient.put<Associado>(`/associados/${associado.id}/foto`, formData, {
        headers: { 'Content-Type': 'multipart/form-data' },
      });
      onAtualizado(data);
    } catch (err: unknown) {
      setErro(extrairMensagemErro(err, 'Não foi possível enviar a foto.'));
    } finally {
      setEnviando(false);
    }
  };

  const remover = async () => {
    setErro(null);
    try {
      await apiClient.delete(`/associados/${associado.id}/foto`);
      onAtualizado({ ...associado, foto_url: null });
    } catch (err: unknown) {
      setErro(extrairMensagemErro(err, 'Não foi possível remover a foto.'));
    }
  };

  return (
    <div className="flex flex-col items-center gap-2 shrink-0">
      {url ? (
        <img
          src={url}
          alt={`Foto de ${associado.nome}`}
          className="w-24 h-24 rounded-full object-cover border border-slate-200"
        />
      ) : (
        <div
          aria-hidden="true"
          className="w-24 h-24 rounded-full bg-slate-100 border border-slate-200 flex items-center justify-center text-2xl font-semibold text-slate-500"
        >
          {iniciais(associado.nome)}
        </div>
      )}

      <div className="flex items-center gap-1">
        <label
          htmlFor="foto-associado"
          className="inline-flex items-center gap-1 px-2 py-1 rounded-md text-xs font-medium text-slate-600 hover:bg-slate-100 cursor-pointer focus-within:ring-2 focus-within:ring-slate-900/20"
        >
          <Camera className="w-3.5 h-3.5" />
          {enviando ? 'Enviando...' : 'Enviar foto'}
          <input
            id="foto-associado"
            type="file"
            accept="image/jpeg,image/png,image/webp"
            className="sr-only"
            disabled={enviando}
            onChange={(e) => {
              void enviar(e.target.files?.[0]);
              e.target.value = '';
            }}
          />
        </label>
        {associado.foto_url && (
          <button
            type="button"
            onClick={remover}
            aria-label="Remover foto"
            title="Remover foto"
            className="p-1 rounded-md text-slate-400 hover:text-rose-600 hover:bg-rose-50"
          >
            <Trash2 className="w-3.5 h-3.5" />
          </button>
        )}
      </div>
      {erro && (
        <p role="alert" className="max-w-[12rem] text-center text-xs text-red-600">
          {erro}
        </p>
      )}
    </div>
  );
}

export default FotoAssociado;
