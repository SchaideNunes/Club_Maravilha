/**
 * Feature 6 - Central de WhatsApp & Configurações (`src/admin/pages/WhatsAppConfigPage.tsx`, rota
 * /admin/whatsapp, substitui o placeholder). Exporta `WhatsAppConfigPage`,
 * `WHATSAPP_STATUS_POLL_MS = 5000` e `WHATSAPP_QRCODE_POLL_MS = 2000` (ver WhatsAppConfigPage.polling.test.tsx).
 *
 * Contratos de UI:
 * - <h1>"WhatsApp & Configurações"</h1>; quatro <section aria-labelledby> (role="region") com <h2>:
 *   "Conexão", "Templates da régua", "Parâmetros gerais", "Últimos disparos".
 *
 * 1. Conexão
 *    - data-testid="whatsapp-connection-status" com o rótulo de GET /whatsapp/status
 *      ("Conectado" | "Desconectado" | "Aguardando QR Code"), atualizado por polling (refetchInterval).
 *    - Enquanto status = AGUARDANDO_QRCODE: GET /whatsapp/qrcode (polling mais rápido) e
 *      <img alt="QR Code do WhatsApp" src={qrcode}> (data URL). Fora desse estado o QR não é buscado
 *      nem exibido.
 *    - Botão "Desconectar" -> role="dialog" nome "Desconectar WhatsApp" com botões "Confirmar desconexão"
 *      (POST /whatsapp/desconectar e recarrega o status) e "Cancelar" (fecha sem chamar a API).
 *    - Botão "Reiniciar conexão" -> POST /whatsapp/reiniciar e recarrega o status. Erros -> role="alert"
 *      com o detail.
 *    - Teste de envio: campos "Número" e "Mensagem (opcional)", botão "Enviar teste" ->
 *      POST /whatsapp/teste-envio {numero, mensagem} (mensagem vazia -> omitida ou null).
 *      Sucesso: "Mensagem de teste enviada". Erro: role="alert" com o detail.
 *      Número vazio: "Informe o número" sem chamar a API.
 *
 * 2. Templates da régua (GET /configuracao)
 *    - 5 <textarea> com labels "Lembrete D-3" (template_d_menos_3), "Cobrança D-0" (template_d0),
 *      "Recibo de Pagamento" (template_recibo), "Aviso D+3" (template_d_mais_3), "Aviso D+7" (template_d_mais_7).
 *    - Botões de variável com nome exato "{nome}", "{valor_base}", "{convites_usados}",
 *      "{convites_extras}", "{valor_total}", "{vencimento}", "{chave_pix}": inserem a variável no
 *      último textarea focado, na posição do cursor.
 *    - Por template, botão "Pré-visualizar <label>" (ex.: "Pré-visualizar Cobrança D-0") ->
 *      POST /configuracao/preview-template {template: <texto atual do textarea>} e mostra `mensagem` em
 *      data-testid="preview-<campo>" (ex.: preview-template_d0). Erro 422 -> role="alert" com o detail.
 *    - Input "Chave Pix do clube" (chave_pix).
 *
 * 3. Parâmetros gerais
 *    - "Valor da mensalidade (R$)" (type=number, valor_mensalidade), "Convidados gratuitos por mês"
 *      (type=number, franquia_convidados), "Taxa por convidado extra (R$)" (type=number,
 *      valor_convidado_extra), "Horário diário de disparo" (type=time, horario_disparo),
 *      "Automação da régua" (role="switch" ou checkbox; marcado = automacao_ativa).
 *
 *    Botão "Salvar configurações" -> PATCH /configuracao com SOMENTE os campos alterados em relação ao
 *    último estado carregado/salvo (sem alterações -> nenhuma requisição). Sucesso: "Configurações salvas".
 *    422: mensagens `msg` do detail (lista Pydantic) ou o detail string exibidos (role="alert").
 *
 * 4. Últimos disparos (GET /whatsapp/logs)
 *    - <table> com cabeçalhos Data/Hora, Destinatário, Etapa, Status, Erro. Linha: "dd/mm/aaaa HH:mm"
 *      (fuso do clube), destinatário formatado "(DD) 99999-9999" (e o associado_nome quando houver),
 *      rótulo da etapa (D_MENOS_3 "Lembrete D-3", D0 "Cobrança D-0", RECIBO "Recibo de Pagamento",
 *      D_MAIS_3 "Aviso D+3", D_MAIS_7 "Aviso D+7", AVULSO "Avulso", TESTE "Teste"), selo "Sucesso" | "Erro"
 *      e o texto do erro. Vazio: "Nenhum disparo registrado".
 *    - <select> "Filtrar por etapa" (opção "Todas" sem parâmetro + rótulos acima -> `etapa`) e
 *      <select> "Filtrar por status" ("Todos", "Sucesso" SUCESSO, "Erro" ERRO -> `status`).
 */
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server } from '../../test/server';
import { API, CONFIGURACAO_PADRAO, ConfiguracaoFixture } from '../../test/handlers';
import { renderAdmin } from '../../test/utils';

const QR_1 = 'data:image/png;base64,QRCODE-UM';

const LOGS = [
  {
    id: 'l1',
    associado_id: '22222222-2222-4222-8222-222222222222',
    associado_nome: 'Maria Souza',
    fatura_id: 'f1',
    destinatario: '5575999998888',
    etapa: 'D_MENOS_3',
    status: 'SUCESSO',
    mensagem: 'Olá Maria',
    erro: null,
    enviado_em: '2026-10-15T13:00:00Z',
  },
  {
    id: 'l2',
    associado_id: '33333333-3333-4333-8333-333333333333',
    associado_nome: 'João Lima',
    fatura_id: 'f2',
    destinatario: '5575988887777',
    etapa: 'D0',
    status: 'ERRO',
    mensagem: 'Olá João',
    erro: 'Número sem WhatsApp',
    enviado_em: '2026-10-15T12:05:00Z',
  },
];

const TEMPLATES: [string, keyof ConfiguracaoFixture][] = [
  ['Lembrete D-3', 'template_d_menos_3'],
  ['Cobrança D-0', 'template_d0'],
  ['Recibo de Pagamento', 'template_recibo'],
  ['Aviso D+3', 'template_d_mais_3'],
  ['Aviso D+7', 'template_d_mais_7'],
];

const VARIAVEIS = ['{nome}', '{valor_base}', '{convites_usados}', '{convites_extras}', '{valor_total}', '{vencimento}', '{chave_pix}'];

type Req = { method: string; url: URL; body?: unknown };

/** Backend fake e com estado para /whatsapp e /configuracao. */
function backendWhatsApp(
  opcoes: { status?: string; qrcodes?: (string | null)[]; config?: ConfiguracaoFixture; logs?: unknown[] } = {},
) {
  let status = opcoes.status ?? 'CONECTADO';
  const qrcodes = opcoes.qrcodes ?? [QR_1];
  let config = { ...(opcoes.config ?? CONFIGURACAO_PADRAO) };
  const requisicoes: Req[] = [];
  const contagem = { status: 0, qrcode: 0 };

  server.use(
    http.get(`${API}/whatsapp/status`, () => {
      contagem.status += 1;
      return HttpResponse.json({ status });
    }),
    http.get(`${API}/whatsapp/qrcode`, () => {
      const qr = qrcodes[Math.min(contagem.qrcode, qrcodes.length - 1)];
      contagem.qrcode += 1;
      return HttpResponse.json({ status, qrcode: status === 'AGUARDANDO_QRCODE' ? qr : null });
    }),
    http.post(`${API}/whatsapp/desconectar`, ({ request }) => {
      requisicoes.push({ method: 'DESCONECTAR', url: new URL(request.url) });
      status = 'DESCONECTADO';
      return HttpResponse.json({ status });
    }),
    http.post(`${API}/whatsapp/reiniciar`, ({ request }) => {
      requisicoes.push({ method: 'REINICIAR', url: new URL(request.url) });
      status = 'AGUARDANDO_QRCODE';
      return HttpResponse.json({ status });
    }),
    http.post(`${API}/whatsapp/teste-envio`, async ({ request }) => {
      const body = (await request.json()) as { numero: string; mensagem?: string | null };
      requisicoes.push({ method: 'TESTE', url: new URL(request.url), body });
      return HttpResponse.json({
        status: 'SUCESSO',
        destinatario: '5575999998888',
        mensagem: body.mensagem || 'Olá! Mensagem de teste do Club Maravilha.',
        message_id: 'MSG-1',
        log_id: 'log-1',
      });
    }),
    http.get(`${API}/whatsapp/logs`, ({ request }) => {
      const url = new URL(request.url);
      requisicoes.push({ method: 'LOGS', url });
      let logs = (opcoes.logs ?? LOGS) as typeof LOGS;
      const etapa = url.searchParams.get('etapa');
      const st = url.searchParams.get('status');
      if (etapa) logs = logs.filter((l) => l.etapa === etapa);
      if (st) logs = logs.filter((l) => l.status === st);
      return HttpResponse.json(logs);
    }),
    http.get(`${API}/configuracao`, () => HttpResponse.json(config)),
    http.patch(`${API}/configuracao`, async ({ request }) => {
      const body = (await request.json()) as Partial<ConfiguracaoFixture>;
      requisicoes.push({ method: 'PATCH', url: new URL(request.url), body });
      config = { ...config, ...body };
      return HttpResponse.json(config);
    }),
    http.post(`${API}/configuracao/preview-template`, async ({ request }) => {
      const body = (await request.json()) as { template: string };
      requisicoes.push({ method: 'PREVIEW', url: new URL(request.url), body });
      return HttpResponse.json({ mensagem: `PREVIEW: ${body.template.replace('{nome}', 'Associado Exemplo')}` });
    }),
  );

  return {
    requisicoes,
    contagem,
    porMetodo: (m: string) => requisicoes.filter((r) => r.method === m),
    setStatus: (novo: string) => {
      status = novo;
    },
  };
}

function secao(nome: string) {
  return screen.findByRole('region', { name: nome });
}

function chaveAutomacao(): HTMLElement {
  return (
    screen.queryByRole('switch', { name: 'Automação da régua' }) ??
    screen.getByRole('checkbox', { name: 'Automação da régua' })
  );
}

async function aguardarConfiguracaoCarregada() {
  await waitFor(() => expect(screen.getByLabelText('Cobrança D-0')).toHaveValue(CONFIGURACAO_PADRAO.template_d0));
}

describe('WhatsAppConfigPage - estrutura', () => {
  it('título e as quatro seções', async () => {
    backendWhatsApp();
    renderAdmin({ route: '/admin/whatsapp' });

    expect(await screen.findByRole('heading', { level: 1, name: 'WhatsApp & Configurações' })).toBeInTheDocument();
    for (const nome of ['Conexão', 'Templates da régua', 'Parâmetros gerais', 'Últimos disparos']) {
      expect(await secao(nome)).toBeInTheDocument();
    }
  });
});

// ------------------------------------------------------------------------------
// 1. Conexão
// ------------------------------------------------------------------------------
describe('WhatsAppConfigPage - conexão', () => {
  it.each([
    ['CONECTADO', 'Conectado'],
    ['DESCONECTADO', 'Desconectado'],
    ['AGUARDANDO_QRCODE', 'Aguardando QR Code'],
  ])('status %s -> rótulo %s', async (status, rotulo) => {
    backendWhatsApp({ status });
    renderAdmin({ route: '/admin/whatsapp' });

    const indicador = await screen.findByTestId('whatsapp-connection-status');
    await waitFor(() => expect(indicador).toHaveTextContent(rotulo));
  });

  it('exibe o QR Code (data URL) quando aguardando pareamento', async () => {
    backendWhatsApp({ status: 'AGUARDANDO_QRCODE' });
    renderAdmin({ route: '/admin/whatsapp' });

    const img = await screen.findByRole('img', { name: 'QR Code do WhatsApp' });
    expect(img).toHaveAttribute('src', QR_1);
  });

  it('conectado: não busca nem exibe QR Code', async () => {
    const backend = backendWhatsApp({ status: 'CONECTADO' });
    renderAdmin({ route: '/admin/whatsapp' });

    await waitFor(() => expect(screen.getByTestId('whatsapp-connection-status')).toHaveTextContent('Conectado'));
    await aguardarConfiguracaoCarregada();
    expect(screen.queryByRole('img', { name: 'QR Code do WhatsApp' })).not.toBeInTheDocument();
    expect(backend.contagem.qrcode).toBe(0);
  });

  it('desconectar pede confirmação e chama a API', async () => {
    const backend = backendWhatsApp({ status: 'CONECTADO' });
    const { user } = renderAdmin({ route: '/admin/whatsapp' });
    const conexao = await secao('Conexão');

    await user.click(within(conexao).getByRole('button', { name: 'Desconectar' }));
    const dialog = await screen.findByRole('dialog', { name: 'Desconectar WhatsApp' });
    expect(backend.porMetodo('DESCONECTAR')).toHaveLength(0);
    await user.click(within(dialog).getByRole('button', { name: 'Confirmar desconexão' }));

    await waitFor(() => expect(backend.porMetodo('DESCONECTAR')).toHaveLength(1));
    await waitFor(() =>
      expect(screen.getByTestId('whatsapp-connection-status')).toHaveTextContent('Desconectado'),
    );
  });

  it('cancelar a desconexão não chama a API', async () => {
    const backend = backendWhatsApp({ status: 'CONECTADO' });
    const { user } = renderAdmin({ route: '/admin/whatsapp' });
    const conexao = await secao('Conexão');

    await user.click(within(conexao).getByRole('button', { name: 'Desconectar' }));
    const dialog = await screen.findByRole('dialog', { name: 'Desconectar WhatsApp' });
    await user.click(within(dialog).getByRole('button', { name: 'Cancelar' }));

    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Desconectar WhatsApp' })).not.toBeInTheDocument());
    expect(backend.porMetodo('DESCONECTAR')).toHaveLength(0);
  });

  it('reiniciar conexão chama a API e passa a exibir o QR Code', async () => {
    const backend = backendWhatsApp({ status: 'DESCONECTADO' });
    const { user } = renderAdmin({ route: '/admin/whatsapp' });
    const conexao = await secao('Conexão');

    await user.click(within(conexao).getByRole('button', { name: 'Reiniciar conexão' }));

    await waitFor(() => expect(backend.porMetodo('REINICIAR')).toHaveLength(1));
    expect(await screen.findByRole('img', { name: 'QR Code do WhatsApp' })).toHaveAttribute('src', QR_1);
    expect(screen.getByTestId('whatsapp-connection-status')).toHaveTextContent('Aguardando QR Code');
  });

  it('erro ao reiniciar exibe o detail', async () => {
    backendWhatsApp({ status: 'DESCONECTADO' });
    server.use(
      http.post(`${API}/whatsapp/reiniciar`, () =>
        HttpResponse.json({ detail: 'Falha ao reiniciar: engine offline' }, { status: 502 }),
      ),
    );
    const { user } = renderAdmin({ route: '/admin/whatsapp' });
    const conexao = await secao('Conexão');

    await user.click(within(conexao).getByRole('button', { name: 'Reiniciar conexão' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Falha ao reiniciar: engine offline');
  });
});

describe('WhatsAppConfigPage - teste de envio', () => {
  it('envia número e mensagem e mostra sucesso', async () => {
    const backend = backendWhatsApp();
    const { user } = renderAdmin({ route: '/admin/whatsapp' });

    await user.type(await screen.findByLabelText('Número'), '75999998888');
    await user.type(screen.getByLabelText('Mensagem (opcional)'), 'Olá teste');
    await user.click(screen.getByRole('button', { name: 'Enviar teste' }));

    expect(await screen.findByText(/Mensagem de teste enviada/)).toBeInTheDocument();
    expect(backend.porMetodo('TESTE')[0].body).toEqual({ numero: '75999998888', mensagem: 'Olá teste' });
  });

  it('mensagem vazia é omitida (ou null)', async () => {
    const backend = backendWhatsApp();
    const { user } = renderAdmin({ route: '/admin/whatsapp' });

    await user.type(await screen.findByLabelText('Número'), '75999998888');
    await user.click(screen.getByRole('button', { name: 'Enviar teste' }));

    await waitFor(() => expect(backend.porMetodo('TESTE')).toHaveLength(1));
    const body = backend.porMetodo('TESTE')[0].body as { numero: string; mensagem?: string | null };
    expect(body.numero).toBe('75999998888');
    expect(body.mensagem ?? null).toBeNull();
  });

  it('número vazio mostra validação sem chamar a API', async () => {
    const backend = backendWhatsApp();
    const { user } = renderAdmin({ route: '/admin/whatsapp' });

    await screen.findByLabelText('Número');
    await user.click(screen.getByRole('button', { name: 'Enviar teste' }));

    expect(await screen.findByText(/Informe o número/)).toBeInTheDocument();
    expect(backend.porMetodo('TESTE')).toHaveLength(0);
  });

  it('erro do motor exibe o detail', async () => {
    backendWhatsApp();
    server.use(
      http.post(`${API}/whatsapp/teste-envio`, () =>
        HttpResponse.json({ detail: 'Motor de WhatsApp indisponível' }, { status: 502 }),
      ),
    );
    const { user } = renderAdmin({ route: '/admin/whatsapp' });

    await user.type(await screen.findByLabelText('Número'), '75999998888');
    await user.click(screen.getByRole('button', { name: 'Enviar teste' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Motor de WhatsApp indisponível');
  });
});

// ------------------------------------------------------------------------------
// 2. Templates
// ------------------------------------------------------------------------------
describe('WhatsAppConfigPage - templates da régua', () => {
  it('carrega os 5 templates e a chave Pix', async () => {
    backendWhatsApp();
    renderAdmin({ route: '/admin/whatsapp' });

    await aguardarConfiguracaoCarregada();
    for (const [rotulo, campo] of TEMPLATES) {
      const textarea = screen.getByLabelText(rotulo);
      expect(textarea.tagName).toBe('TEXTAREA');
      expect(textarea).toHaveValue(CONFIGURACAO_PADRAO[campo] as string);
    }
    expect(screen.getByLabelText('Chave Pix do clube')).toHaveValue(CONFIGURACAO_PADRAO.chave_pix);
  });

  it('lista as variáveis disponíveis como botões', async () => {
    backendWhatsApp();
    renderAdmin({ route: '/admin/whatsapp' });

    const templates = await secao('Templates da régua');
    for (const variavel of VARIAVEIS) {
      expect(within(templates).getByRole('button', { name: variavel })).toBeInTheDocument();
    }
  });

  it('clicar numa variável insere no textarea focado, na posição do cursor', async () => {
    backendWhatsApp();
    const { user } = renderAdmin({ route: '/admin/whatsapp' });
    await aguardarConfiguracaoCarregada();
    const templates = await secao('Templates da régua');

    const d0 = screen.getByLabelText('Cobrança D-0');
    await user.clear(d0);
    await user.type(d0, 'Olá ');
    await user.click(within(templates).getByRole('button', { name: '{nome}' }));

    expect(d0).toHaveValue('Olá {nome}');
    expect(screen.getByLabelText('Lembrete D-3')).toHaveValue(CONFIGURACAO_PADRAO.template_d_menos_3);

    const recibo = screen.getByLabelText('Recibo de Pagamento') as HTMLTextAreaElement;
    await user.clear(recibo);
    await user.type(recibo, 'Total: !');
    recibo.setSelectionRange(7, 7);
    fireEvent.select(recibo);
    await user.click(within(templates).getByRole('button', { name: '{valor_total}' }));

    expect(recibo).toHaveValue('Total: {valor_total}!');
    expect(d0).toHaveValue('Olá {nome}');
  });

  it('pré-visualizar envia o texto atual do template e mostra a mensagem renderizada', async () => {
    const backend = backendWhatsApp();
    const { user } = renderAdmin({ route: '/admin/whatsapp' });
    await aguardarConfiguracaoCarregada();

    const d0 = screen.getByLabelText('Cobrança D-0');
    await user.clear(d0);
    await user.click(d0);
    await user.paste('Oi {nome}, tudo bem?');
    await user.click(screen.getByRole('button', { name: 'Pré-visualizar Cobrança D-0' }));

    expect(await screen.findByTestId('preview-template_d0')).toHaveTextContent('PREVIEW: Oi Associado Exemplo, tudo bem?');
    expect(backend.porMetodo('PREVIEW')[0].body).toMatchObject({ template: 'Oi {nome}, tudo bem?' });
  });

  it.each(TEMPLATES)('há botão de pré-visualização para %s', async (rotulo) => {
    backendWhatsApp();
    renderAdmin({ route: '/admin/whatsapp' });
    await aguardarConfiguracaoCarregada();

    expect(screen.getByRole('button', { name: `Pré-visualizar ${rotulo}` })).toBeInTheDocument();
  });

  it('pré-visualização com template inválido exibe o erro 422', async () => {
    backendWhatsApp();
    server.use(
      http.post(`${API}/configuracao/preview-template`, () =>
        HttpResponse.json(
          { detail: [{ loc: ['body', 'template'], msg: "Template inválido: variável desconhecida '{nom}'.", type: 'value_error' }] },
          { status: 422 },
        ),
      ),
    );
    const { user } = renderAdmin({ route: '/admin/whatsapp' });
    await aguardarConfiguracaoCarregada();

    await user.click(screen.getByRole('button', { name: 'Pré-visualizar Aviso D+3' }));

    expect(await screen.findByRole('alert')).toHaveTextContent("variável desconhecida '{nom}'");
  });
});

// ------------------------------------------------------------------------------
// 3. Parâmetros gerais e salvar
// ------------------------------------------------------------------------------
describe('WhatsAppConfigPage - parâmetros gerais e salvar', () => {
  it('carrega os parâmetros do clube', async () => {
    backendWhatsApp();
    renderAdmin({ route: '/admin/whatsapp' });
    await aguardarConfiguracaoCarregada();

    expect(screen.getByLabelText('Valor da mensalidade (R$)')).toHaveValue(150);
    expect(screen.getByLabelText('Convidados gratuitos por mês')).toHaveValue(8);
    expect(screen.getByLabelText('Taxa por convidado extra (R$)')).toHaveValue(35);
    const horario = screen.getByLabelText('Horário diário de disparo');
    expect(horario).toHaveAttribute('type', 'time');
    expect(horario).toHaveValue('08:00');
    expect(chaveAutomacao()).toBeChecked();
  });

  it('salvar envia somente os campos alterados', async () => {
    const backend = backendWhatsApp();
    const { user } = renderAdmin({ route: '/admin/whatsapp' });
    await aguardarConfiguracaoCarregada();

    const mensalidade = screen.getByLabelText('Valor da mensalidade (R$)');
    await user.clear(mensalidade);
    await user.type(mensalidade, '180');
    const d0 = screen.getByLabelText('Cobrança D-0');
    await user.clear(d0);
    await user.click(d0);
    await user.paste('Novo {nome}');
    await user.click(screen.getByRole('button', { name: 'Salvar configurações' }));

    expect(await screen.findByText(/Configurações salvas/)).toBeInTheDocument();
    const [patch] = backend.porMetodo('PATCH');
    const body = patch.body as Record<string, unknown>;
    expect(Object.keys(body).sort()).toEqual(['template_d0', 'valor_mensalidade']);
    expect(Number(body.valor_mensalidade)).toBe(180);
    expect(body.template_d0).toBe('Novo {nome}');
  });

  it('horário, chave Pix e automação', async () => {
    const backend = backendWhatsApp();
    const { user } = renderAdmin({ route: '/admin/whatsapp' });
    await aguardarConfiguracaoCarregada();

    fireEvent.change(screen.getByLabelText('Horário diário de disparo'), { target: { value: '09:30' } });
    const pix = screen.getByLabelText('Chave Pix do clube');
    await user.clear(pix);
    await user.type(pix, 'novo@pix.com');
    await user.click(chaveAutomacao());
    expect(chaveAutomacao()).not.toBeChecked();
    await user.click(screen.getByRole('button', { name: 'Salvar configurações' }));

    await waitFor(() => expect(backend.porMetodo('PATCH')).toHaveLength(1));
    expect(backend.porMetodo('PATCH')[0].body).toEqual({
      horario_disparo: '09:30',
      chave_pix: 'novo@pix.com',
      automacao_ativa: false,
    });
  });

  it('convidados e taxa extra', async () => {
    const backend = backendWhatsApp();
    const { user } = renderAdmin({ route: '/admin/whatsapp' });
    await aguardarConfiguracaoCarregada();

    const franquia = screen.getByLabelText('Convidados gratuitos por mês');
    await user.clear(franquia);
    await user.type(franquia, '10');
    const taxa = screen.getByLabelText('Taxa por convidado extra (R$)');
    await user.clear(taxa);
    await user.type(taxa, '40.5');
    await user.click(screen.getByRole('button', { name: 'Salvar configurações' }));

    await waitFor(() => expect(backend.porMetodo('PATCH')).toHaveLength(1));
    const body = backend.porMetodo('PATCH')[0].body as Record<string, unknown>;
    expect(Object.keys(body).sort()).toEqual(['franquia_convidados', 'valor_convidado_extra']);
    expect(body.franquia_convidados).toBe(10);
    expect(Number(body.valor_convidado_extra)).toBe(40.5);
  });

  it('sem alterações não envia PATCH', async () => {
    const backend = backendWhatsApp();
    const { user } = renderAdmin({ route: '/admin/whatsapp' });
    await aguardarConfiguracaoCarregada();

    await user.click(screen.getByRole('button', { name: 'Salvar configurações' }));

    await new Promise((r) => setTimeout(r, 100));
    expect(backend.porMetodo('PATCH')).toHaveLength(0);
  });

  it('após salvar, o próximo salvamento envia só as novas alterações', async () => {
    const backend = backendWhatsApp();
    const { user } = renderAdmin({ route: '/admin/whatsapp' });
    await aguardarConfiguracaoCarregada();

    const mensalidade = screen.getByLabelText('Valor da mensalidade (R$)');
    await user.clear(mensalidade);
    await user.type(mensalidade, '180');
    await user.click(screen.getByRole('button', { name: 'Salvar configurações' }));
    await screen.findByText(/Configurações salvas/);

    const franquia = screen.getByLabelText('Convidados gratuitos por mês');
    await user.clear(franquia);
    await user.type(franquia, '9');
    await user.click(screen.getByRole('button', { name: 'Salvar configurações' }));

    await waitFor(() => expect(backend.porMetodo('PATCH')).toHaveLength(2));
    expect(Object.keys(backend.porMetodo('PATCH')[1].body as object)).toEqual(['franquia_convidados']);
  });

  it('422 com lista Pydantic exibe a mensagem do campo', async () => {
    backendWhatsApp();
    server.use(
      http.patch(`${API}/configuracao`, () =>
        HttpResponse.json(
          {
            detail: [
              { loc: ['body', 'template_d0'], msg: "Template inválido: variável desconhecida '{nom}'.", type: 'value_error' },
            ],
          },
          { status: 422 },
        ),
      ),
    );
    const { user } = renderAdmin({ route: '/admin/whatsapp' });
    await aguardarConfiguracaoCarregada();

    const d0 = screen.getByLabelText('Cobrança D-0');
    await user.clear(d0);
    await user.click(d0);
    await user.paste('Olá {nom}');
    await user.click(screen.getByRole('button', { name: 'Salvar configurações' }));

    expect(await screen.findByText(/variável desconhecida '\{nom\}'/)).toBeInTheDocument();
    expect(screen.queryByText(/Configurações salvas/)).not.toBeInTheDocument();
  });

  it('422 com detail string exibe alerta geral', async () => {
    backendWhatsApp();
    server.use(
      http.patch(`${API}/configuracao`, () =>
        HttpResponse.json({ detail: 'Horário de disparo inválido.' }, { status: 422 }),
      ),
    );
    const { user } = renderAdmin({ route: '/admin/whatsapp' });
    await aguardarConfiguracaoCarregada();

    fireEvent.change(screen.getByLabelText('Horário diário de disparo'), { target: { value: '07:45' } });
    await user.click(screen.getByRole('button', { name: 'Salvar configurações' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Horário de disparo inválido.');
  });
});

// ------------------------------------------------------------------------------
// 4. Últimos disparos
// ------------------------------------------------------------------------------
describe('WhatsAppConfigPage - últimos disparos', () => {
  it('tabela com os logs formatados', async () => {
    backendWhatsApp();
    renderAdmin({ route: '/admin/whatsapp' });

    const regiao = await secao('Últimos disparos');
    const tabela = await within(regiao).findByRole('table');
    const cabecalhos = within(tabela).getAllByRole('columnheader').map((th) => th.textContent?.trim());
    expect(cabecalhos).toEqual(['Data/Hora', 'Destinatário', 'Etapa', 'Status', 'Erro']);

    const maria = await within(tabela).findByRole('row', { name: /Maria Souza/ });
    expect(maria).toHaveTextContent('15/10/2026 10:00');
    expect(maria).toHaveTextContent('(75) 99999-8888');
    expect(maria).toHaveTextContent('Lembrete D-3');
    expect(maria).toHaveTextContent('Sucesso');

    const joao = within(tabela).getByRole('row', { name: /João Lima/ });
    expect(joao).toHaveTextContent('15/10/2026 09:05');
    expect(joao).toHaveTextContent('Cobrança D-0');
    expect(joao).toHaveTextContent('Erro');
    expect(joao).toHaveTextContent('Número sem WhatsApp');
  });

  it('estado vazio', async () => {
    backendWhatsApp({ logs: [] });
    renderAdmin({ route: '/admin/whatsapp' });

    const regiao = await secao('Últimos disparos');
    expect(await within(regiao).findByText('Nenhum disparo registrado')).toBeInTheDocument();
  });

  it('filtro por etapa envia o parâmetro etapa', async () => {
    const backend = backendWhatsApp();
    const { user } = renderAdmin({ route: '/admin/whatsapp' });
    const regiao = await secao('Últimos disparos');
    await within(regiao).findByRole('row', { name: /Maria Souza/ });

    await user.selectOptions(within(regiao).getByLabelText('Filtrar por etapa'), 'Aviso D+7');

    await waitFor(() => expect(backend.porMetodo('LOGS').at(-1)!.url.searchParams.get('etapa')).toBe('D_MAIS_7'));
    expect(await within(regiao).findByText('Nenhum disparo registrado')).toBeInTheDocument();
  });

  it('filtro por status envia o parâmetro status', async () => {
    const backend = backendWhatsApp();
    const { user } = renderAdmin({ route: '/admin/whatsapp' });
    const regiao = await secao('Últimos disparos');
    await within(regiao).findByRole('row', { name: /Maria Souza/ });

    await user.selectOptions(within(regiao).getByLabelText('Filtrar por status'), 'Erro');

    await waitFor(() => expect(backend.porMetodo('LOGS').at(-1)!.url.searchParams.get('status')).toBe('ERRO'));
    await waitFor(() => expect(within(regiao).queryByRole('row', { name: /Maria Souza/ })).not.toBeInTheDocument());
    expect(within(regiao).getByRole('row', { name: /João Lima/ })).toBeInTheDocument();
  });
});
