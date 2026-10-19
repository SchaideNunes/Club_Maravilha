/**
 * Smoke test da infraestrutura de testes do frontend (não depende de código de produção):
 * jsdom visível (react-query só faz polling com a aba visível), env VITE_API_URL de teste,
 * fuso America/Sao_Paulo e MSW interceptando axios (JSON e multipart) sem rede.
 */
import axios from 'axios';
import { http, HttpResponse } from 'msw';
import userEvent from '@testing-library/user-event';
import { describe, expect, it } from 'vitest';
import { server } from './server';

describe('infra de testes', () => {
  it('jsdom reporta a aba como visível', () => {
    expect(document.visibilityState).toBe('visible');
  });

  it('expõe VITE_API_URL de teste e fuso do clube', () => {
    expect(import.meta.env.VITE_API_URL).toBe('http://api.test');
    expect(Intl.DateTimeFormat().resolvedOptions().timeZone).toBe('America/Sao_Paulo');
  });

  it('MSW intercepta axios com JSON e multipart', async () => {
    let campo: string | null = null;
    server.use(
      http.get('http://api.test/ping', () => HttpResponse.json({ ok: true })),
      http.post('http://api.test/upload', async ({ request }) => {
        const form = await request.formData();
        const arquivo = form.get('file');
        campo = arquivo instanceof File ? arquivo.name : null;
        return HttpResponse.json({ recebido: campo });
      }),
    );
    const ping = await axios.get('http://api.test/ping');
    expect(ping.data).toEqual({ ok: true });

    const form = new FormData();
    form.append('file', new File(['nome;cpf'], 'socios.csv', { type: 'text/csv' }));
    const up = await axios.post('http://api.test/upload', form);
    expect(up.data).toEqual({ recebido: 'socios.csv' });
  });

  it('arquivo enviado via user-event.upload segue no multipart interceptado pelo MSW', async () => {
    let recebido: string | null = null;
    server.use(
      http.post('http://api.test/upload', async ({ request }) => {
        const arquivo = (await request.formData()).get('file');
        recebido = arquivo instanceof File ? `${arquivo.name}:${await arquivo.text()}` : null;
        return HttpResponse.json({ ok: true });
      }),
    );
    const input = document.createElement('input');
    input.type = 'file';
    document.body.appendChild(input);
    await userEvent.setup().upload(input, new File(['nome;cpf'], 'socios.csv', { type: 'text/csv' }));

    const form = new FormData();
    form.append('file', input.files![0]);
    await axios.post('http://api.test/upload', form);
    expect(recebido).toBe('socios.csv:nome;cpf');
    input.remove();
  });
});
