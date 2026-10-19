import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server } from '../../test/server';
import { API, FaturaFixture, ResumoFaturasFixture, criarFatura, paginado } from '../../test/handlers';
import { renderAdmin } from '../../test/utils';

const RESUMO_BASE: ResumoFaturasFixture = {
  total: 1,
  pagas: 0,
  pendentes: 1,
  atrasadas: 0,
  valor_total: '150.00',
  valor_recebido: '0.00',
};

const FATURA_EXEMPLO: FaturaFixture = criarFatura({
  id: 'f-rev-01',
  associado_nome: 'Associado Teste',
  valor_total: '150.00',
  status: 'PENDENTE',
});

describe('MensalidadesPage Review (Item 2 - Proteção de Geração de Faturas)', () => {
  it('mês vazio desabilita o botão Gerar faturas do mês', async () => {
    server.use(
      http.get(`${API}/faturas/`, () => {
        return HttpResponse.json(paginado([FATURA_EXEMPLO], { resumo: RESUMO_BASE }));
      }),
    );

    const { user } = renderAdmin({ route: '/admin/mensalidades' });

    const btnGerar = await screen.findByRole('button', { name: 'Gerar faturas do mês' });
    expect(btnGerar).not.toBeDisabled();

    // Limpa o mês
    const inputMes = screen.getByLabelText('Mês de referência');
    fireEvent.change(inputMes, { target: { value: '' } });

    expect(btnGerar).toBeDisabled();
  });

  it('exibe o mês alvo formatado no rótulo auxiliar (ex.: outubro/2026)', async () => {
    server.use(
      http.get(`${API}/faturas/`, () => {
        return HttpResponse.json(paginado([FATURA_EXEMPLO], { resumo: RESUMO_BASE }));
      }),
    );

    renderAdmin({ route: '/admin/mensalidades' });

    const inputMes = await screen.findByLabelText('Mês de referência');
    fireEvent.change(inputMes, { target: { value: '2026-10' } });

    expect(await screen.findByText('outubro/2026')).toBeInTheDocument();

    fireEvent.change(inputMes, { target: { value: '2026-12' } });
    expect(await screen.findByText('dezembro/2026')).toBeInTheDocument();
  });

  it('mês passado abre diálogo de confirmação e Cancelar não faz POST', async () => {
    let chamadasGerar = 0;
    server.use(
      http.get(`${API}/faturas/`, () => {
        return HttpResponse.json(paginado([FATURA_EXEMPLO], { resumo: RESUMO_BASE }));
      }),
      http.post(`${API}/faturas/gerar-mes`, () => {
        chamadasGerar++;
        return HttpResponse.json({ referencia_mes: '2026-08', criadas: 5, ja_existentes: 0, total: 5 });
      }),
    );

    const { user } = renderAdmin({ route: '/admin/mensalidades' });

    // Seleciona mês passado (agosto/2026, anterior a outubro/2026)
    const inputMes = await screen.findByLabelText('Mês de referência');
    fireEvent.change(inputMes, { target: { value: '2026-08' } });

    const btnGerar = screen.getByRole('button', { name: 'Gerar faturas do mês' });
    await user.click(btnGerar);

    // Diálogo de confirmação deve aparecer
    const dialog = await screen.findByRole('dialog');
    expect(dialog).toBeInTheDocument();
    expect(within(dialog).getByText(/anterior/i)).toBeInTheDocument();

    // Clica em Cancelar
    const btnCancelar = within(dialog).getByRole('button', { name: /cancelar/i });
    await user.click(btnCancelar);

    // Diálogo fecha e nenhum POST foi feito
    await waitFor(() => {
      expect(screen.queryByRole('dialog')).not.toBeInTheDocument();
    });
    expect(chamadasGerar).toBe(0);
  });

  it('mês corrente/futuro continua sem diálogo e executa diretamente o POST', async () => {
    let chamadasGerar = 0;
    server.use(
      http.get(`${API}/faturas/`, () => {
        return HttpResponse.json(paginado([FATURA_EXEMPLO], { resumo: RESUMO_BASE }));
      }),
      http.post(`${API}/faturas/gerar-mes`, () => {
        chamadasGerar++;
        return HttpResponse.json({ referencia_mes: '2026-12', criadas: 3, ja_existentes: 0, total: 3 });
      }),
    );

    const { user } = renderAdmin({ route: '/admin/mensalidades' });

    const inputMes = await screen.findByLabelText('Mês de referência');
    fireEvent.change(inputMes, { target: { value: '2026-12' } });

    const btnGerar = screen.getByRole('button', { name: 'Gerar faturas do mês' });
    await user.click(btnGerar);

    // Não deve abrir nenhum diálogo
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument();

    await waitFor(() => {
      expect(chamadasGerar).toBe(1);
    });
  });
});
