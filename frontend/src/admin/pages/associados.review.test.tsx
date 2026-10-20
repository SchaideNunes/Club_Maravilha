import React from 'react';
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import fs from 'fs';
import path from 'path';

import { server } from '../../test/server';
import { API, criarAssociado, paginado } from '../../test/handlers';
import { renderAdmin } from '../../test/utils';
import tailwindConfig from '../../../tailwind.config.js';

describe('AssociadosPage Review (Itens 12, 13 e 14)', () => {
  it('Item 12: falha na inativação (500 com detail) exibe role="alert" e mantém o modal aberto', async () => {
    const socio = criarAssociado({
      id: 'socio-inativar-id-1',
      nome: 'Carlos Drummond',
    });

    server.use(
      http.get(`${API}/associados/:id`, () => HttpResponse.json(socio)),
      http.post(`${API}/associados/:id/inativar`, () => {
        return HttpResponse.json({ detail: 'Falha no banco de dados ao inativar associado' }, { status: 500 });
      }),
    );

    const { user } = renderAdmin({ route: `/admin/associados/${socio.id}` });

    await user.click(await screen.findByRole('button', { name: 'Inativar associado' }));
    const dialog = await screen.findByRole('dialog', { name: 'Inativar associado' });

    await user.click(within(dialog).getByRole('button', { name: 'Confirmar inativação' }));

    const alerta = await within(dialog).findByRole('alert');
    expect(alerta).toHaveTextContent('Falha no banco de dados ao inativar associado');
    expect(screen.getByRole('dialog', { name: 'Inativar associado' })).toBeInTheDocument();
  });

  it('Item 13: foco inicial no primeiro campo, Escape fecha e devolve foco ao botão disparador', async () => {
    const socio = criarAssociado();

    server.use(
      http.get(`${API}/associados/`, () => {
        return HttpResponse.json(paginado([socio]));
      }),
    );

    const { user } = renderAdmin({ route: '/admin/associados' });

    const btnConvidado = await screen.findByRole('button', { name: `Adicionar convidado para ${socio.nome}` });
    btnConvidado.focus();
    expect(btnConvidado).toHaveFocus();

    await user.click(btnConvidado);

    const dialog = await screen.findByRole('dialog', { name: 'Adicionar convidado' });
    const inputNome = within(dialog).getByLabelText('Nome do convidado');
    await waitFor(() => {
      expect(inputNome).toHaveFocus();
    });

    await user.keyboard('{Escape}');

    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: 'Adicionar convidado' })).not.toBeInTheDocument();
    });
    await waitFor(() => {
      expect(btnConvidado).toHaveFocus();
    });
  });

  it('Item 14: tema possui primary configurado e não há classes ring-primary órfãs em src/admin', () => {
    // 1. primary configurado no tema
    const extendedColors = tailwindConfig.theme?.extend?.colors as Record<string, unknown> | undefined;
    expect(extendedColors?.primary).toBeDefined();

    // 2. Nenhuma ocorrência órfã de ring-primary nos arquivos de src/admin
    const adminDir = path.resolve(__dirname, '..');
    const files = fs.readdirSync(adminDir, { recursive: true }) as string[];

    for (const file of files) {
      if (typeof file === 'string' && (file.endsWith('.tsx') || file.endsWith('.ts')) && !file.includes('.test.')) {
        const fullPath = path.join(adminDir, file);
        if (fs.existsSync(fullPath) && fs.statSync(fullPath).isFile()) {
          const content = fs.readFileSync(fullPath, 'utf-8');
          expect(content).not.toContain('ring-primary');
        }
      }
    }
  });
});
