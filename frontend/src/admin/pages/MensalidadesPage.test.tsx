/**
 * Feature 6 - Tela de Mensalidades (`src/admin/pages/MensalidadesPage.tsx`, rota /admin/mensalidades,
 * substitui o placeholder). Exporta `MensalidadesPage`.
 *
 * Contratos de UI:
 * - <h1>"Mensalidades"</h1>.
 * - Filtros:
 *     input type="month" com label "Mês de referência", padrão = mês corrente no fuso do clube
 *       (America/Sao_Paulo, "AAAA-MM") -> parâmetro `referencia_mes` de GET /faturas/;
 *     <select> label "Status": "Todas" (sem parâmetro), "Pendente" (PENDENTE), "Atrasada" (ATRASADA),
 *       "Paga" (PAGO) -> parâmetro `status`;
 *     input label "Buscar por nome ou CPF" com debounce (~300-500 ms) -> parâmetro `q`
 *       (uma requisição pelo termo final, não por tecla);
 *     qualquer filtro volta para a página 1. Paginação: "Página X de Y", botões "Página anterior" /
 *       "Próxima página" (desabilitados nas pontas) -> parâmetro `page`.
 * - React-query: a lista usa queryKey iniciando por 'faturas' (ex.: ['faturas', ref, status, q, page]).
 * - Resumo do mês (campo `resumo` de GET /faturas/), cards com data-testid:
 *     resumo-total, resumo-pagas, resumo-pendentes, resumo-atrasadas (contagens),
 *     resumo-valor-total, resumo-valor-recebido (valores em BRL "R$ 1.234,56").
 * - <table> com cabeçalhos: Associado, Vencimento, Valor Base, Acréscimo Convidados, Valor Total,
 *   Status, Ações. Linha: associado_nome, vencimento "dd/mm/aaaa", valor_base,
 *   valor_convidados_excedentes e valor_total em BRL, selo do status ("Pendente" | "Atrasada" |
 *   "Paga" | "Cancelada"). Vazio: "Nenhuma fatura encontrada". Erro: role="alert" com
 *   "Não foi possível carregar...".
 * - Botão "Gerar faturas do mês" -> POST /faturas/gerar-mes {referencia_mes: <mês selecionado>} ->
 *   texto "<criadas> criadas, <ja_existentes> já existentes" e recarrega a lista; erro -> role="alert"
 *   com o detail.
 * - Por linha (somente PENDENTE/ATRASADA; para PAGO/CANCELADO os botões não existem ou ficam disabled):
 *     botão "Dar Baixa Manual" -> role="dialog" nome "Dar baixa manual" exibindo nome do associado e
 *       valor total; radios (grupo "Forma de pagamento") "Pix" (padrão marcado), "Cartão", "Dinheiro";
 *       botão "Confirmar pagamento" -> POST /faturas/{id}/baixa-manual {forma_pagamento: PIX|CARTAO|DINHEIRO}.
 *       Sucesso: fecha o dialog, mostra "Pagamento confirmado — recibo enviado no WhatsApp", a linha
 *       passa a "Paga" (refetch) e invalida as queries ['faturas'], ['dashboard-resumo'] e
 *       ['dashboard-atividades']. Erro (409 etc.): role="alert" com o detail e o dialog permanece.
 *     botão "Cobrar Agora via WhatsApp" -> POST /faturas/{id}/cobrar-whatsapp -> "Cobrança enfileirada";
 *       erro 409/422 -> role="alert" com o detail.
 *   (Os nomes acessíveis dos botões devem CONTER esses textos; aria-label com o nome do associado é permitido.)
 */
import { fireEvent, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';
import { server } from '../../test/server';
import {
  API,
  FaturaFixture,
  ResumoFaturasFixture,
  criarFatura,
  paginado,
} from '../../test/handlers';
import { renderAdmin } from '../../test/utils';

const F_MARIA = criarFatura({
  id: 'f0000000-0000-4000-8000-000000000001',
  associado_nome: 'Maria Souza',
  valor_base: '150.00',
  valor_convidados_excedentes: '70.00',
  valor_total: '220.00',
  convites_usados: 10,
  convites_extras: 2,
  data_vencimento: '2026-11-10',
  status: 'PENDENTE',
});
const F_JOAO = criarFatura({
  id: 'f0000000-0000-4000-8000-000000000002',
  associado_id: '33333333-3333-4333-8333-333333333333',
  associado_nome: 'João Lima',
  associado_cpf: '111.444.777-35',
  data_vencimento: '2026-11-05',
  status: 'ATRASADA',
});
const F_ANA = criarFatura({
  id: 'f0000000-0000-4000-8000-000000000003',
  associado_id: '55555555-5555-4555-8555-555555555555',
  associado_nome: 'Ana Costa',
  associado_cpf: '987.654.321-00',
  valor_base: '185.00',
  valor_total: '185.00',
  status: 'PAGO',
  forma_pagamento: 'PIX',
  data_pagamento: '2026-11-02T13:00:00Z',
  lembretes_ativos: false,
});
const F_BETO = criarFatura({
  id: 'f0000000-0000-4000-8000-000000000004',
  associado_id: '66666666-6666-4666-8666-666666666666',
  associado_nome: 'Beto Cancelado',
  associado_cpf: '222.333.444-05',
  status: 'CANCELADO',
});

const RESUMO: ResumoFaturasFixture = {
  total: 4,
  pagas: 2,
  pendentes: 1,
  atrasadas: 1,
  valor_total: '1705.00',
  valor_recebido: '335.00',
};

type Req = { method: string; url: URL; body?: unknown };

function mesCorrenteNoClube(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Sao_Paulo' }).format(new Date()).slice(0, 7);
}

/** Backend fake e com estado para /faturas (filtra status/q, pagina e aplica baixa manual). */
function backendFaturas(
  inicial: FaturaFixture[] = [F_MARIA, F_JOAO, F_ANA, F_BETO],
  opcoes: { totalPages?: number; resumo?: ResumoFaturasFixture } = {},
) {
  let faturas = inicial.map((f) => ({ ...f }));
  const requisicoes: Req[] = [];

  server.use(
    http.get(`${API}/faturas/`, ({ request }) => {
      const url = new URL(request.url);
      requisicoes.push({ method: 'GET', url });
      const q = url.searchParams.get('q')?.toLowerCase();
      const status = url.searchParams.get('status');
      const page = Number(url.searchParams.get('page') ?? 1);
      let itens = faturas;
      if (status) itens = itens.filter((f) => f.status === status);
      if (q) itens = itens.filter((f) => f.associado_nome.toLowerCase().includes(q) || f.associado_cpf.includes(q));
      const totalPages = opcoes.totalPages ?? 1;
      return HttpResponse.json({
        ...paginado(itens, { page, total: totalPages > 1 ? totalPages * 20 : itens.length, total_pages: totalPages }),
        resumo: opcoes.resumo ?? RESUMO,
      });
    }),
    http.post(`${API}/faturas/gerar-mes`, async ({ request }) => {
      const body = await request.json().catch(() => null);
      requisicoes.push({ method: 'GERAR', url: new URL(request.url), body });
      return HttpResponse.json({
        referencia_mes: (body as { referencia_mes?: string } | null)?.referencia_mes ?? mesCorrenteNoClube(),
        criadas: 3,
        ja_existentes: 2,
        total: 5,
      });
    }),
    http.post(`${API}/faturas/:id/baixa-manual`, async ({ request, params }) => {
      const body = (await request.json()) as { forma_pagamento: FaturaFixture['forma_pagamento'] };
      requisicoes.push({ method: 'BAIXA', url: new URL(request.url), body });
      faturas = faturas.map((f) =>
        f.id === params.id
          ? { ...f, status: 'PAGO', forma_pagamento: body.forma_pagamento, data_pagamento: '2026-11-03T12:00:00Z', lembretes_ativos: false }
          : f,
      );
      return HttpResponse.json(faturas.find((f) => f.id === params.id));
    }),
    http.post(`${API}/faturas/:id/cobrar-whatsapp`, ({ request, params }) => {
      requisicoes.push({ method: 'COBRAR', url: new URL(request.url) });
      const fatura = faturas.find((f) => f.id === params.id)!;
      return HttpResponse.json(
        { fatura_id: fatura.id, etapa: 'AVULSO', template: 'D0', destinatario: '5575999998888', mensagem: 'Olá' },
        { status: 202 },
      );
    }),
  );

  return {
    requisicoes,
    listas: () => requisicoes.filter((r) => r.method === 'GET'),
    porMetodo: (m: string) => requisicoes.filter((r) => r.method === m),
  };
}

async function linhaDe(nome: string) {
  return screen.findByRole('row', { name: new RegExp(nome) });
}

function botaoNaLinha(linha: HTMLElement, nome: RegExp): HTMLElement | null {
  return within(linha).queryByRole('button', { name: nome });
}

function esperarAcaoIndisponivel(linha: HTMLElement, nome: RegExp) {
  const botao = botaoNaLinha(linha, nome);
  if (botao) expect(botao).toBeDisabled();
}

// ------------------------------------------------------------------------------
// Tabela e resumo
// ------------------------------------------------------------------------------
describe('MensalidadesPage - tabela', () => {
  it('renderiza título, cabeçalhos e linhas com valores em BRL e selos de status', async () => {
    backendFaturas();
    renderAdmin({ route: '/admin/mensalidades' });

    expect(await screen.findByRole('heading', { level: 1, name: 'Mensalidades' })).toBeInTheDocument();
    const tabela = await screen.findByRole('table');
    const cabecalhos = within(tabela).getAllByRole('columnheader').map((th) => th.textContent?.trim());
    expect(cabecalhos).toEqual([
      'Associado',
      'Vencimento',
      'Valor Base',
      'Acréscimo Convidados',
      'Valor Total',
      'Status',
      'Ações',
    ]);

    const maria = await linhaDe('Maria Souza');
    expect(maria).toHaveTextContent('10/11/2026');
    expect(maria).toHaveTextContent(/R\$\s150,00/);
    expect(maria).toHaveTextContent(/R\$\s70,00/);
    expect(maria).toHaveTextContent(/R\$\s220,00/);
    expect(maria).toHaveTextContent('Pendente');

    expect(await linhaDe('João Lima')).toHaveTextContent('Atrasada');
    expect(await linhaDe('Ana Costa')).toHaveTextContent('Paga');
    expect(await linhaDe('Beto Cancelado')).toHaveTextContent('Cancelada');
  });

  it('exibe os cards de resumo do mês', async () => {
    backendFaturas();
    renderAdmin({ route: '/admin/mensalidades' });

    expect(await screen.findByTestId('resumo-total')).toHaveTextContent('4');
    expect(screen.getByTestId('resumo-pagas')).toHaveTextContent('2');
    expect(screen.getByTestId('resumo-pendentes')).toHaveTextContent('1');
    expect(screen.getByTestId('resumo-atrasadas')).toHaveTextContent('1');
    expect(screen.getByTestId('resumo-valor-total')).toHaveTextContent(/R\$\s1\.705,00/);
    expect(screen.getByTestId('resumo-valor-recebido')).toHaveTextContent(/R\$\s335,00/);
  });

  it('estado vazio', async () => {
    backendFaturas([]);
    renderAdmin({ route: '/admin/mensalidades' });

    expect(await screen.findByText('Nenhuma fatura encontrada')).toBeInTheDocument();
  });

  it('estado de erro', async () => {
    server.use(http.get(`${API}/faturas/`, () => HttpResponse.json({ detail: 'falha' }, { status: 500 })));
    renderAdmin({ route: '/admin/mensalidades' });

    expect(await screen.findByRole('alert')).toHaveTextContent(/Não foi possível carregar/);
  });

  it('PAGO e CANCELADO não oferecem baixa manual nem cobrança', async () => {
    backendFaturas();
    renderAdmin({ route: '/admin/mensalidades' });

    for (const nome of ['Ana Costa', 'Beto Cancelado']) {
      const linha = await linhaDe(nome);
      esperarAcaoIndisponivel(linha, /dar baixa manual/i);
      esperarAcaoIndisponivel(linha, /cobrar agora via whatsapp/i);
    }
    const maria = await linhaDe('Maria Souza');
    expect(botaoNaLinha(maria, /dar baixa manual/i)).toBeEnabled();
    expect(botaoNaLinha(maria, /cobrar agora via whatsapp/i)).toBeEnabled();
    const joao = await linhaDe('João Lima');
    expect(botaoNaLinha(joao, /dar baixa manual/i)).toBeEnabled();
    expect(botaoNaLinha(joao, /cobrar agora via whatsapp/i)).toBeEnabled();
  });
});

// ------------------------------------------------------------------------------
// Filtros e paginação
// ------------------------------------------------------------------------------
describe('MensalidadesPage - filtros', () => {
  it('mês de referência padrão é o mês corrente e é enviado na listagem', async () => {
    const backend = backendFaturas();
    renderAdmin({ route: '/admin/mensalidades' });

    const mes = await screen.findByLabelText('Mês de referência');
    expect(mes).toHaveAttribute('type', 'month');
    expect(mes).toHaveValue(mesCorrenteNoClube());
    await waitFor(() => expect(backend.listas().length).toBeGreaterThan(0));
    expect(backend.listas()[0].url.searchParams.get('referencia_mes')).toBe(mesCorrenteNoClube());
  });

  it('trocar o mês refaz a busca com a nova referência na página 1', async () => {
    const backend = backendFaturas([F_MARIA], { totalPages: 3 });
    const { user } = renderAdmin({ route: '/admin/mensalidades' });

    await screen.findByText('Página 1 de 3');
    await user.click(screen.getByRole('button', { name: 'Próxima página' }));
    await waitFor(() => expect(backend.listas().at(-1)!.url.searchParams.get('page')).toBe('2'));

    fireEvent.change(screen.getByLabelText('Mês de referência'), { target: { value: '2026-09' } });

    await waitFor(() => {
      const ultima = backend.listas().at(-1)!.url.searchParams;
      expect(ultima.get('referencia_mes')).toBe('2026-09');
      expect(ultima.get('page') ?? '1').toBe('1');
    });
  });

  it.each([
    ['Pendente', 'PENDENTE'],
    ['Atrasada', 'ATRASADA'],
    ['Paga', 'PAGO'],
  ])('filtro de status %s -> status=%s', async (rotulo, valor) => {
    const backend = backendFaturas();
    const { user } = renderAdmin({ route: '/admin/mensalidades' });

    await linhaDe('Maria Souza');
    await user.selectOptions(screen.getByLabelText('Status'), rotulo);

    await waitFor(() => expect(backend.listas().at(-1)!.url.searchParams.get('status')).toBe(valor));
  });

  it('filtro "Todas" não envia o parâmetro status', async () => {
    const backend = backendFaturas();
    const { user } = renderAdmin({ route: '/admin/mensalidades' });

    await linhaDe('Maria Souza');
    await user.selectOptions(screen.getByLabelText('Status'), 'Paga');
    await waitFor(() => expect(backend.listas().at(-1)!.url.searchParams.get('status')).toBe('PAGO'));
    await user.selectOptions(screen.getByLabelText('Status'), 'Todas');

    await waitFor(() => expect(backend.listas().at(-1)!.url.searchParams.has('status')).toBe(false));
  });

  it('busca por nome/CPF com debounce (uma requisição pelo termo final)', async () => {
    const backend = backendFaturas();
    const { user } = renderAdmin({ route: '/admin/mensalidades' });

    await linhaDe('Maria Souza');
    await user.type(screen.getByLabelText('Buscar por nome ou CPF'), 'joão');

    await waitFor(() => expect(backend.listas().at(-1)!.url.searchParams.get('q')).toBe('joão'));
    const termos = backend.listas().map((r) => r.url.searchParams.get('q')).filter(Boolean);
    expect(termos).toEqual(['joão']);
    await waitFor(() => expect(screen.queryByRole('row', { name: /Maria Souza/ })).not.toBeInTheDocument());
    expect(screen.getByRole('row', { name: /João Lima/ })).toBeInTheDocument();
  });

  it('paginação: texto, botões nas pontas e parâmetro page', async () => {
    const backend = backendFaturas([F_MARIA], { totalPages: 2 });
    const { user } = renderAdmin({ route: '/admin/mensalidades' });

    expect(await screen.findByText('Página 1 de 2')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Página anterior' })).toBeDisabled();
    await user.click(screen.getByRole('button', { name: 'Próxima página' }));

    expect(await screen.findByText('Página 2 de 2')).toBeInTheDocument();
    expect(backend.listas().at(-1)!.url.searchParams.get('page')).toBe('2');
    expect(screen.getByRole('button', { name: 'Próxima página' })).toBeDisabled();
  });
});

// ------------------------------------------------------------------------------
// Gerar faturas do mês
// ------------------------------------------------------------------------------
describe('MensalidadesPage - gerar faturas do mês', () => {
  it('envia a referência selecionada, mostra o resultado e recarrega a lista', async () => {
    const backend = backendFaturas();
    const { user } = renderAdmin({ route: '/admin/mensalidades' });

    await linhaDe('Maria Souza');
    fireEvent.change(screen.getByLabelText('Mês de referência'), { target: { value: '2026-12' } });
    await waitFor(() => expect(backend.listas().at(-1)!.url.searchParams.get('referencia_mes')).toBe('2026-12'));
    const listasAntes = backend.listas().length;

    await user.click(screen.getByRole('button', { name: 'Gerar faturas do mês' }));

    expect(await screen.findByText(/3 criadas, 2 já existentes/)).toBeInTheDocument();
    expect(backend.porMetodo('GERAR')[0].body).toEqual({ referencia_mes: '2026-12' });
    await waitFor(() => expect(backend.listas().length).toBeGreaterThan(listasAntes));
  });

  it('erro na geração exibe o detail', async () => {
    backendFaturas();
    server.use(
      http.post(`${API}/faturas/gerar-mes`, () =>
        HttpResponse.json({ detail: 'Referência inválida para geração.' }, { status: 422 }),
      ),
    );
    const { user } = renderAdmin({ route: '/admin/mensalidades' });

    await linhaDe('Maria Souza');
    await user.click(screen.getByRole('button', { name: 'Gerar faturas do mês' }));

    expect(await screen.findByRole('alert')).toHaveTextContent('Referência inválida para geração.');
  });
});

// ------------------------------------------------------------------------------
// Baixa manual
// ------------------------------------------------------------------------------
describe('MensalidadesPage - baixa manual', () => {
  it('abre o modal com dados da fatura e Pix marcado por padrão', async () => {
    backendFaturas();
    const { user } = renderAdmin({ route: '/admin/mensalidades' });

    await user.click(botaoNaLinha(await linhaDe('Maria Souza'), /dar baixa manual/i)!);

    const dialog = await screen.findByRole('dialog', { name: 'Dar baixa manual' });
    expect(dialog).toHaveTextContent('Maria Souza');
    expect(dialog).toHaveTextContent(/R\$\s220,00/);
    expect(within(dialog).getByRole('radio', { name: 'Pix' })).toBeChecked();
    expect(within(dialog).getByRole('radio', { name: 'Cartão' })).not.toBeChecked();
    expect(within(dialog).getByRole('radio', { name: 'Dinheiro' })).not.toBeChecked();
  });

  it('confirmação em 1 clique envia PIX, fecha o modal, mostra a mensagem e a linha vira Paga', async () => {
    const backend = backendFaturas();
    const { user, queryClient } = renderAdmin({ route: '/admin/mensalidades' });
    const invalidar = vi.spyOn(queryClient, 'invalidateQueries');

    await user.click(botaoNaLinha(await linhaDe('Maria Souza'), /dar baixa manual/i)!);
    const dialog = await screen.findByRole('dialog', { name: 'Dar baixa manual' });
    await user.click(within(dialog).getByRole('button', { name: 'Confirmar pagamento' }));

    expect(await screen.findByText('Pagamento confirmado — recibo enviado no WhatsApp')).toBeInTheDocument();
    await waitFor(() => expect(screen.queryByRole('dialog', { name: 'Dar baixa manual' })).not.toBeInTheDocument());

    const [baixa] = backend.porMetodo('BAIXA');
    expect(baixa.url.pathname).toBe(`/api/v1/faturas/${F_MARIA.id}/baixa-manual`);
    expect(baixa.body).toMatchObject({ forma_pagamento: 'PIX' });

    await waitFor(() => {
      const linha = screen.getByRole('row', { name: /Maria Souza/ });
      expect(linha).toHaveTextContent('Paga');
      esperarAcaoIndisponivel(linha, /dar baixa manual/i);
    });

    const chaves = invalidar.mock.calls.map(([filtro]) => JSON.stringify((filtro as { queryKey?: unknown })?.queryKey));
    expect(chaves).toEqual(
      expect.arrayContaining([
        JSON.stringify(['faturas']),
        JSON.stringify(['dashboard-resumo']),
        JSON.stringify(['dashboard-atividades']),
      ]),
    );
  });

  it.each([
    ['Cartão', 'CARTAO'],
    ['Dinheiro', 'DINHEIRO'],
  ])('forma de pagamento %s -> %s', async (rotulo, valor) => {
    const backend = backendFaturas();
    const { user } = renderAdmin({ route: '/admin/mensalidades' });

    await user.click(botaoNaLinha(await linhaDe('João Lima'), /dar baixa manual/i)!);
    const dialog = await screen.findByRole('dialog', { name: 'Dar baixa manual' });
    await user.click(within(dialog).getByRole('radio', { name: rotulo }));
    await user.click(within(dialog).getByRole('button', { name: 'Confirmar pagamento' }));

    await waitFor(() => expect(backend.porMetodo('BAIXA')).toHaveLength(1));
    expect(backend.porMetodo('BAIXA')[0].body).toMatchObject({ forma_pagamento: valor });
    expect(backend.porMetodo('BAIXA')[0].url.pathname).toBe(`/api/v1/faturas/${F_JOAO.id}/baixa-manual`);
  });

  it('409 exibe o detail no modal, que permanece aberto', async () => {
    backendFaturas();
    server.use(
      http.post(`${API}/faturas/:id/baixa-manual`, () =>
        HttpResponse.json({ detail: 'Fatura já está paga.' }, { status: 409 }),
      ),
    );
    const { user } = renderAdmin({ route: '/admin/mensalidades' });

    await user.click(botaoNaLinha(await linhaDe('Maria Souza'), /dar baixa manual/i)!);
    const dialog = await screen.findByRole('dialog', { name: 'Dar baixa manual' });
    await user.click(within(dialog).getByRole('button', { name: 'Confirmar pagamento' }));

    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Fatura já está paga.');
    expect(screen.getByRole('dialog', { name: 'Dar baixa manual' })).toBeInTheDocument();
    expect(screen.queryByText('Pagamento confirmado — recibo enviado no WhatsApp')).not.toBeInTheDocument();
  });
});

// ------------------------------------------------------------------------------
// Cobrar agora via WhatsApp
// ------------------------------------------------------------------------------
describe('MensalidadesPage - cobrar agora via WhatsApp', () => {
  it('dispara a cobrança avulsa e mostra "Cobrança enfileirada"', async () => {
    const backend = backendFaturas();
    const { user } = renderAdmin({ route: '/admin/mensalidades' });

    await user.click(botaoNaLinha(await linhaDe('João Lima'), /cobrar agora via whatsapp/i)!);

    expect(await screen.findByText(/Cobrança enfileirada/)).toBeInTheDocument();
    expect(backend.porMetodo('COBRAR')).toHaveLength(1);
    expect(backend.porMetodo('COBRAR')[0].url.pathname).toBe(`/api/v1/faturas/${F_JOAO.id}/cobrar-whatsapp`);
  });

  it.each([
    [409, 'Fatura com status PAGO não pode ser cobrada.'],
    [422, 'Associado não possui WhatsApp cadastrado.'],
  ])('erro %s exibe o detail', async (codigo, detail) => {
    backendFaturas();
    server.use(
      http.post(`${API}/faturas/:id/cobrar-whatsapp`, () => HttpResponse.json({ detail }, { status: codigo })),
    );
    const { user } = renderAdmin({ route: '/admin/mensalidades' });

    await user.click(botaoNaLinha(await linhaDe('Maria Souza'), /cobrar agora via whatsapp/i)!);

    expect(await screen.findByRole('alert')).toHaveTextContent(detail);
    expect(screen.queryByText(/Cobrança enfileirada/)).not.toBeInTheDocument();
  });
});
