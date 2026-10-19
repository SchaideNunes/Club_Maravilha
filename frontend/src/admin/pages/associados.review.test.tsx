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
  it('Item 12: falha na exclusão (500 com detail) exibe role="alert" e mantém o modal aberto', async () => {
    const socio = criarAssociado({
      id: 'socio-delete-id-1',
      nome: 'Carlos Drummond',
    });

    server.use(
      http.get(`${API}/associados/`, () => {
        return HttpResponse.json(paginado([socio]));
      }),
      http.delete(`${API}/associados/:id`, () => {
        return HttpResponse.json({ detail: 'Falha no banco de dados ao excluir associado' }, { status: 500 });
      }),
    );

    const { user } = renderAdmin({ route: '/admin/associados' });

    // Localiza e abre o modal de exclusão
    const btnExcluir = await screen.findByRole('button', { name: `Excluir ${socio.nome}` });
    await user.click(btnExcluir);

    const dialogExcluir = await screen.findByRole('dialog', { name: 'Excluir associado' });
    expect(dialogExcluir).toBeInTheDocument();

    // Clica para confirmar exclusão
    const btnConfirmar = within(dialogExcluir).getByRole('button', { name: 'Confirmar exclusão' });
    await user.click(btnConfirmar);

    // O alert deve aparecer com a mensagem da API
    const alerta = await within(dialogExcluir).findByRole('alert');
    expect(alerta).toHaveTextContent('Falha no banco de dados ao excluir associado');

    // O modal deve permanecer aberto
    expect(screen.getByRole('dialog', { name: 'Excluir associado' })).toBeInTheDocument();
  });

  it('Item 13: foco inicial no campo Nome, Escape fecha e devolve foco ao botão disparador', async () => {
    const socio = criarAssociado();

    server.use(
      http.get(`${API}/associados/`, () => {
        return HttpResponse.json(paginado([socio]));
      }),
    );

    const { user } = renderAdmin({ route: '/admin/associados' });

    const btnNovo = await screen.findByRole('button', { name: 'Novo associado' });
    btnNovo.focus();
    expect(btnNovo).toHaveFocus();

    // Abre o modal
    await user.click(btnNovo);

    const dialogNovo = await screen.findByRole('dialog', { name: 'Novo associado' });
    expect(dialogNovo).toBeInTheDocument();

    // Foco inicial deve ir para o campo "Nome"
    const inputNome = within(dialogNovo).getByLabelText('Nome');
    await waitFor(() => {
      expect(inputNome).toHaveFocus();
    });

    // Pressionar tecla Escape deve fechar o modal
    await user.keyboard('{Escape}');

    // Modal fechou
    await waitFor(() => {
      expect(screen.queryByRole('dialog', { name: 'Novo associado' })).not.toBeInTheDocument();
    });

    // Foco deve retornar ao botão que abriu o modal
    await waitFor(() => {
      expect(btnNovo).toHaveFocus();
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
