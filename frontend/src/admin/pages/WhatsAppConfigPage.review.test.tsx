import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { delay, http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server } from '../../test/server';
import { API, CONFIGURACAO_PADRAO, ConfiguracaoFixture } from '../../test/handlers';
import { renderAdmin } from '../../test/utils';

describe('WhatsAppConfigPage Review (Itens 3, 4 e 5)', () => {
  // ============================================================================
  // Item 3: Tratamento de loading e erro em Configuração e Disparos
  // ============================================================================
  it('Item 3: GET /configuracao 500 exibe alerta com Tentar novamente e Salvar desabilitado', async () => {
    let tentouNovamente = false;
    server.use(
      http.get(`${API}/configuracao`, () => {
        if (!tentouNovamente) {
          return HttpResponse.json({ detail: 'Erro no banco de dados' }, { status: 500 });
        }
        return HttpResponse.json(CONFIGURACAO_PADRAO);
      }),
      http.get(`${API}/whatsapp/status`, () => {
        return HttpResponse.json({ status: 'DESCONECTADO' });
      }),
      http.get(`${API}/whatsapp/logs`, () => {
        return HttpResponse.json([]);
      }),
    );

    const { user } = renderAdmin({ route: '/admin/whatsapp' });

    // Deve exibir alerta de erro de carga
    const alerta = await screen.findByRole('alert');
    expect(alerta).toHaveTextContent(/Erro ao carregar configurações/i);

    // Botão "Salvar configurações" deve estar desabilitado
    const btnSalvar = screen.getByRole('button', { name: 'Salvar configurações' });
    expect(btnSalvar).toBeDisabled();

    // Clica em "Tentar novamente"
    tentouNovamente = true;
    const btnTentar = within(alerta).getByRole('button', { name: /tentar novamente/i });
    await user.click(btnTentar);

    // Agora deve carregar com sucesso e habilitar a interface
    await waitFor(() => {
      expect(screen.queryByRole('alert')).not.toBeInTheDocument();
    });
  });

  it('Item 3: GET /whatsapp/logs 500 exibe role="alert" na seção de disparos em vez de lista vazia', async () => {
    server.use(
      http.get(`${API}/configuracao`, () => {
        return HttpResponse.json(CONFIGURACAO_PADRAO);
      }),
      http.get(`${API}/whatsapp/status`, () => {
        return HttpResponse.json({ status: 'DESCONECTADO' });
      }),
      http.get(`${API}/whatsapp/logs`, () => {
        return HttpResponse.json({ detail: 'Falha ao buscar logs' }, { status: 500 });
      }),
    );

    renderAdmin({ route: '/admin/whatsapp' });

    // Deve exibir alerta na seção de disparos
    const alertas = await screen.findAllByRole('alert');
    const alertaDisparos = alertas.find((el) => el.textContent?.includes('histórico de disparos') || el.textContent?.includes('Erro'));
    expect(alertaDisparos).toBeDefined();

    // Não deve exibir o texto de lista vazia
    expect(screen.queryByText('Nenhum disparo registrado')).not.toBeInTheDocument();
  });

  // ============================================================================
  // Item 4: Dirty-tracking resiliente a edições concorrentes durante salvamento
  // ============================================================================
  it('Item 4: edição de outro campo durante PATCH com atraso é preservada e enviada no próximo PATCH', async () => {
    let patchCount = 0;
    const patchesRecebidos: Record<string, unknown>[] = [];

    server.use(
      http.get(`${API}/configuracao`, () => {
        return HttpResponse.json({
          ...CONFIGURACAO_PADRAO,
          horario_disparo: '08:00',
          valor_mensalidade: '150.00',
          chave_pix: 'antiga@pix.com',
        });
      }),
      http.get(`${API}/whatsapp/status`, () => {
        return HttpResponse.json({ status: 'DESCONECTADO' });
      }),
      http.get(`${API}/whatsapp/logs`, () => {
        return HttpResponse.json([]);
      }),
      http.patch(`${API}/configuracao`, async ({ request }) => {
        patchCount++;
        const body = (await request.json()) as Record<string, unknown>;
        patchesRecebidos.push(body);
        // Simula latência no backend
        await delay(60);
        return HttpResponse.json({
          ...CONFIGURACAO_PADRAO,
          horario_disparo: '08:00',
          valor_mensalidade: '150.00',
          ...body,
        });
      }),
    );

    const { user } = renderAdmin({ route: '/admin/whatsapp' });

    // Aguarda carregar as configurações do backend
    const btnSalvar = await screen.findByRole('button', { name: 'Salvar configurações' });
    await waitFor(() => expect(btnSalvar).not.toBeDisabled());
    await waitFor(() => expect(screen.getByLabelText('Cobrança D-0')).toHaveValue(CONFIGURACAO_PADRAO.template_d0));

    const inputHorario = screen.getByLabelText('Horário diário de disparo');
    expect(inputHorario).toHaveValue('08:00');

    // 1. Altera horário para 09:30
    fireEvent.change(inputHorario, { target: { value: '09:30' } });

    // 2. Dispara salvar
    await user.click(btnSalvar);

    // 3. Enquanto o PATCH está em trânsito, o usuário edita outro campo (Valor da mensalidade)
    const inputMensalidade = screen.getByLabelText('Valor da mensalidade (R$)');
    fireEvent.change(inputMensalidade, { target: { value: '250.00' } });

    // Aguarda o primeiro PATCH terminar e exibir sucesso
    await screen.findByText('Configurações salvas');
    expect(patchCount).toBe(1);
    expect(patchesRecebidos[0]).toEqual({ horario_disparo: '09:30' });

    // O valor 250.00 digitado deve ser PRESERVADO (não resetado pela resposta do primeiro PATCH)
    expect(inputMensalidade).toHaveValue(250);

    // 4. Clica em salvar novamente: deve enviar SOMENTE a nova alteração de valor_mensalidade
    await user.click(btnSalvar);

    await waitFor(() => {
      expect(patchCount).toBe(2);
    });
    expect(patchesRecebidos[1]).toEqual({ valor_mensalidade: '250.00' });
  });

  // ============================================================================
  // Item 5: Alerta quando Chave Pix não está configurada e automação está ligada
  // ============================================================================
  it('Item 5: página mostra o alerta quando chave_pix é null e automação ligada', async () => {
    server.use(
      http.get(`${API}/configuracao`, () => {
        return HttpResponse.json({
          ...CONFIGURACAO_PADRAO,
          chave_pix: null,
          automacao_ativa: true,
        });
      }),
      http.get(`${API}/whatsapp/status`, () => {
        return HttpResponse.json({ status: 'DESCONECTADO' });
      }),
      http.get(`${API}/whatsapp/logs`, () => {
        return HttpResponse.json([]);
      }),
    );

    renderAdmin({ route: '/admin/whatsapp' });

    const alerta = await screen.findByRole('alert');
    expect(alerta).toHaveTextContent(/Chave Pix não configurada — as cobranças sairão sem chave/i);
  });

  it('Item 5: não exibe alerta quando chave_pix está preenchida', async () => {
    server.use(
      http.get(`${API}/configuracao`, () => {
        return HttpResponse.json({
          ...CONFIGURACAO_PADRAO,
          chave_pix: 'pix.financeiro@club.com',
          automacao_ativa: true,
        });
      }),
      http.get(`${API}/whatsapp/status`, () => {
        return HttpResponse.json({ status: 'DESCONECTADO' });
      }),
      http.get(`${API}/whatsapp/logs`, () => {
        return HttpResponse.json([]);
      }),
    );

    renderAdmin({ route: '/admin/whatsapp' });

    await screen.findByLabelText('Horário diário de disparo');
    expect(screen.queryByText(/Chave Pix não configurada/i)).not.toBeInTheDocument();
  });
});
