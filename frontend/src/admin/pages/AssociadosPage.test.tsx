/**
 * Feature 5 - Gestão de Associados, Convidados e Importação (`src/admin/pages/AssociadosPage.tsx`,
 * rota /admin/associados). Exporta `AssociadosPage`.
 *
 * Contratos de UI (o que os testes procuram):
 * - <h1>"Associados"</h1>; <table> com cabeçalhos Nome, CPF, WhatsApp, Vencimento, Situação, Convites, Ações.
 *   Cada linha: nome, CPF formatado, WhatsApp "(DD) 99999-9999", "Dia <dia_vencimento>", rótulo da situação
 *   ("Em dia" | "Pendente" | "Atrasado") e "<convidados_usados_mes>/<franquia_convidados> convites".
 *   Vazio: "Nenhum associado encontrado". Erro: role="alert" com "Não foi possível carregar...".
 * - Busca: input com label "Buscar por nome ou CPF", debounce (~300-500 ms) -> GET /associados/?q=<termo>
 *   (uma requisição por termo final, não por tecla) e volta para a página 1.
 * - Filtro: <select> com label "Situação", opções "Todas" (sem parâmetro), "Em dia" (EM_DIA),
 *   "Pendente" (PENDENTE), "Atrasado" (ATRASADO) -> parâmetro `situacao`.
 * - Paginação: texto "Página X de Y", botões "Página anterior" / "Próxima página" (desabilitados nas pontas)
 *   -> parâmetro `page`.
 * - Convidado: por linha, botão com texto "+ Adicionar Convidado" e aria-label
 *   "Adicionar convidado para <nome>" -> role="dialog" com nome acessível "Adicionar convidado";
 *   campos "Nome do convidado", "CPF (opcional)", "Data da visita" (type=date, padrão = hoje no fuso do clube);
 *   botão "Emitir convite" -> POST /associados/{id}/convidados {nome, data_visita, cpf (omitido/null se vazio)}.
 *   Nome vazio -> "Informe o nome do convidado" (sem chamar a API).
 *   Resposta GRATUITO -> mensagem "Convite emitido..."; EXCEDENTE -> role="alert" destacado com o `aviso`
 *   da API e a taxa `valor_taxa_extra` formatada em R$. O contador da tabela é atualizado (refetch).
 * - Associado: botão "Novo associado" -> dialog "Novo associado" com campos "Nome", "CPF", "WhatsApp",
 *   "E-mail", "Dia de vencimento" e botão "Salvar" -> POST /associados/ {nome, cpf, whatsapp, email,
 *   dia_vencimento:number}. Validação básica local (mensagens contendo "obrigatório").
 *   Erros 409 (detail string) e 422 (detail lista Pydantic -> msg) exibidos em role="alert" no dialog.
 *   Por linha: "Editar <nome>" -> dialog "Editar associado" pré-preenchido (CPF não editável) ->
 *   PATCH /associados/{id} sem `cpf`; "Excluir <nome>" -> dialog "Excluir associado" com o nome e
 *   botão "Confirmar exclusão" -> DELETE /associados/{id}.
 * - Importação: botão "Importar planilha" -> dialog "Importar planilha" com input file de label
 *   "Arquivo da planilha" (accept .xlsx,.csv), checkbox "Atualizar existentes" e botão "Enviar planilha"
 *   -> POST /associados/importar?atualizar_existentes=true|false (multipart, campo `file`).
 *   Arquivo com outra extensão -> role="alert" mencionando o formato (sem upload).
 *   Relatório: data-testid import-total-lidos / import-total-importados / import-total-atualizados /
 *   import-total-ignorados e a lista de erros ("Linha <n>", campo e motivo). Erros HTTP (ex.: 413) mostram o detail.
 */
import { screen, waitFor, within } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server } from '../../test/server';
import { API, AssociadoFixture, criarAssociado, paginado } from '../../test/handlers';
import { renderAdmin } from '../../test/utils';

const MARIA = criarAssociado();
const JOAO = criarAssociado({
  id: '33333333-3333-4333-8333-333333333333',
  nome: 'João Lima',
  cpf: '111.444.777-35',
  whatsapp: '557532211234',
  email: 'joao@exemplo.com',
  dia_vencimento: 20,
  convidados_usados_mes: 8,
  situacao_financeira: 'ATRASADO',
});

type Req = { method: string; url: URL; body?: unknown };

/** Backend fake e com estado para /associados (filtra q/situacao e pagina como o FastAPI). */
function backendAssociados(inicial: AssociadoFixture[] = [MARIA, JOAO], opcoes: { totalPages?: number } = {}) {
  let socios = [...inicial];
  const requisicoes: Req[] = [];
  const listas = () => requisicoes.filter((r) => r.method === 'GET');

  server.use(
    http.get(`${API}/associados/`, ({ request }) => {
      const url = new URL(request.url);
      requisicoes.push({ method: 'GET', url });
      const q = url.searchParams.get('q')?.toLowerCase();
      const situacao = url.searchParams.get('situacao');
      const page = Number(url.searchParams.get('page') ?? 1);
      let itens = socios;
      if (q) itens = itens.filter((s) => s.nome.toLowerCase().includes(q) || s.cpf.replace(/\D/g, '').includes(q.replace(/\D/g, '') || '#'));
      if (situacao) itens = itens.filter((s) => s.situacao_financeira === situacao);
      const totalPages = opcoes.totalPages ?? 1;
      return HttpResponse.json(
        paginado(itens, { page, total: totalPages > 1 ? totalPages * 20 : itens.length, total_pages: totalPages }),
      );
    }),
    http.post(`${API}/associados/:id/convidados`, async ({ request, params }) => {
      const body = await request.json();
      requisicoes.push({ method: 'POST_CONVIDADO', url: new URL(request.url), body });
      const socio = socios.find((s) => s.id === params.id)!;
      socio.convidados_usados_mes += 1;
      const excedente = socio.convidados_usados_mes > socio.franquia_convidados;
      return HttpResponse.json(
        {
          convidado: { id: 'c1', nome: (body as { nome: string }).nome },
          is_gratuito: !excedente,
          tipo: excedente ? 'EXCEDENTE' : 'GRATUITO',
          convidados_usados_mes: socio.convidados_usados_mes,
          franquia: socio.franquia_convidados,
          excedentes_mes: Math.max(0, socio.convidados_usados_mes - socio.franquia_convidados),
          valor_taxa_extra: excedente ? '35.00' : '0.00',
          aviso: excedente ? 'Franquia de convidados excedida: este convite será cobrado na próxima fatura.' : null,
        },
        { status: 201 },
      );
    }),
    http.post(`${API}/associados/`, async ({ request }) => {
      const body = (await request.json()) as Partial<AssociadoFixture>;
      requisicoes.push({ method: 'POST', url: new URL(request.url), body });
      const novo = criarAssociado({ ...body, id: '44444444-4444-4444-8444-444444444444', convidados_usados_mes: 0 });
      socios = [...socios, novo];
      return HttpResponse.json(novo, { status: 201 });
    }),
    http.patch(`${API}/associados/:id`, async ({ request, params }) => {
      const body = (await request.json()) as Partial<AssociadoFixture>;
      requisicoes.push({ method: 'PATCH', url: new URL(request.url), body });
      socios = socios.map((s) => (s.id === params.id ? { ...s, ...body } : s));
      return HttpResponse.json(socios.find((s) => s.id === params.id));
    }),
    http.delete(`${API}/associados/:id`, ({ request, params }) => {
      requisicoes.push({ method: 'DELETE', url: new URL(request.url) });
      socios = socios.filter((s) => s.id !== params.id);
      return new HttpResponse(null, { status: 204 });
    }),
  );

  return { requisicoes, listas, porMetodo: (m: string) => requisicoes.filter((r) => r.method === m) };
}

function hojeNoClube(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Sao_Paulo' }).format(new Date());
}

async function linhaDe(nome: string) {
  return screen.findByRole('row', { name: new RegExp(nome) });
}

// ------------------------------------------------------------------------------
// Tabela
// ------------------------------------------------------------------------------
describe('AssociadosPage - tabela', () => {
  it('renderiza cabeçalhos e linhas formatadas', async () => {
    backendAssociados();
    renderAdmin({ route: '/admin/associados' });

    expect(await screen.findByRole('heading', { level: 1, name: 'Associados' })).toBeInTheDocument();
    const tabela = await screen.findByRole('table');
    for (const cabecalho of ['Nome', 'CPF', 'WhatsApp', 'Vencimento', 'Situação', 'Convites', 'Ações']) {
      expect(within(tabela).getByRole('columnheader', { name: cabecalho })).toBeInTheDocument();
    }

    const maria = await linhaDe('Maria Souza');
    expect(maria).toHaveTextContent('529.982.247-25');
    expect(maria).toHaveTextContent('(75) 99999-8888');
    expect(maria).toHaveTextContent('Dia 10');
    expect(within(maria).getByText('Em dia')).toBeInTheDocument();
    expect(within(maria).getByText('5/8 convites')).toBeInTheDocument();

    const joao = await linhaDe('João Lima');
    expect(joao).toHaveTextContent('(75) 3221-1234');
    expect(joao).toHaveTextContent('Dia 20');
    expect(within(joao).getByText('Atrasado')).toBeInTheDocument();
    expect(within(joao).getByText('8/8 convites')).toBeInTheDocument();
  });

  it('estado vazio', async () => {
    backendAssociados([]);
    renderAdmin({ route: '/admin/associados' });

    expect(await screen.findByText('Nenhum associado encontrado')).toBeInTheDocument();
  });

  it('estado de erro', async () => {
    server.use(http.get(`${API}/associados/`, () => HttpResponse.json({ detail: 'erro' }, { status: 500 })));
    renderAdmin({ route: '/admin/associados' });

    expect(await screen.findByRole('alert')).toHaveTextContent(/não foi possível carregar/i);
  });
});

// ------------------------------------------------------------------------------
// Busca, filtro e paginação
// ------------------------------------------------------------------------------
describe('AssociadosPage - busca, filtro e paginação', () => {
  it('busca por nome com debounce (uma requisição por termo final)', async () => {
    const api = backendAssociados();
    const { user } = renderAdmin({ route: '/admin/associados' });
    await linhaDe('Maria Souza');

    await user.type(screen.getByLabelText('Buscar por nome ou CPF'), 'joão');

    await waitFor(() => expect(api.listas().some((r) => r.url.searchParams.get('q') === 'joão')).toBe(true));
    const termos = api.listas().map((r) => r.url.searchParams.get('q')).filter(Boolean);
    expect(termos).toEqual(['joão']);
    await waitFor(() => expect(screen.queryByRole('row', { name: /Maria Souza/ })).not.toBeInTheDocument());
    expect(screen.getByRole('row', { name: /João Lima/ })).toBeInTheDocument();
  });

  it('busca por CPF', async () => {
    const api = backendAssociados();
    const { user } = renderAdmin({ route: '/admin/associados' });
    await linhaDe('Maria Souza');

    await user.type(screen.getByLabelText('Buscar por nome ou CPF'), '11144477735');

    await waitFor(() =>
      expect(api.listas().some((r) => r.url.searchParams.get('q') === '11144477735')).toBe(true),
    );
  });

  it('filtro de situação envia EM_DIA/PENDENTE/ATRASADO', async () => {
    const api = backendAssociados();
    const { user } = renderAdmin({ route: '/admin/associados' });
    await linhaDe('Maria Souza');

    const filtro = screen.getByLabelText('Situação');
    expect(within(filtro).getAllByRole('option').map((o) => o.textContent)).toEqual([
      'Todas',
      'Em dia',
      'Pendente',
      'Atrasado',
    ]);

    await user.selectOptions(filtro, 'Atrasado');
    await waitFor(() =>
      expect(api.listas().at(-1)!.url.searchParams.get('situacao')).toBe('ATRASADO'),
    );
    await waitFor(() => expect(screen.queryByRole('row', { name: /Maria Souza/ })).not.toBeInTheDocument());

    await user.selectOptions(filtro, 'Em dia');
    await waitFor(() => expect(api.listas().at(-1)!.url.searchParams.get('situacao')).toBe('EM_DIA'));

    await user.selectOptions(filtro, 'Pendente');
    await waitFor(() => expect(api.listas().at(-1)!.url.searchParams.get('situacao')).toBe('PENDENTE'));

    await user.selectOptions(filtro, 'Todas');
    await waitFor(() => expect(api.listas().at(-1)!.url.searchParams.has('situacao')).toBe(false));
  });

  it('paginação', async () => {
    const api = backendAssociados([MARIA, JOAO], { totalPages: 3 });
    const { user } = renderAdmin({ route: '/admin/associados' });
    await linhaDe('Maria Souza');

    expect(screen.getByText('Página 1 de 3')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Página anterior' })).toBeDisabled();

    await user.click(screen.getByRole('button', { name: 'Próxima página' }));

    await waitFor(() => expect(api.listas().at(-1)!.url.searchParams.get('page')).toBe('2'));
    expect(await screen.findByText('Página 2 de 3')).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Página anterior' })).toBeEnabled();
  });

  it('nova busca volta para a página 1', async () => {
    const api = backendAssociados([MARIA, JOAO], { totalPages: 3 });
    const { user } = renderAdmin({ route: '/admin/associados' });
    await linhaDe('Maria Souza');
    await user.click(screen.getByRole('button', { name: 'Próxima página' }));
    await screen.findByText('Página 2 de 3');

    await user.type(screen.getByLabelText('Buscar por nome ou CPF'), 'maria');

    await waitFor(() => {
      const ultima = api.listas().at(-1)!.url.searchParams;
      expect(ultima.get('q')).toBe('maria');
      expect(ultima.get('page') ?? '1').toBe('1');
    });
  });
});

// ------------------------------------------------------------------------------
// Convidados
// ------------------------------------------------------------------------------
describe('AssociadosPage - adicionar convidado', () => {
  async function abrirModal(user: ReturnType<typeof userEvent.setup>, nome: string) {
    const linha = await linhaDe(nome);
    const botao = within(linha).getByRole('button', { name: `Adicionar convidado para ${nome}` });
    expect(botao).toHaveTextContent('+ Adicionar Convidado');
    await user.click(botao);
    return screen.findByRole('dialog', { name: /adicionar convidado/i });
  }

  it('abre modal com campos rotulados e data de hoje', async () => {
    backendAssociados();
    const { user } = renderAdmin({ route: '/admin/associados' });

    const dialog = await abrirModal(user, 'Maria Souza');

    expect(within(dialog).getByLabelText('Nome do convidado')).toBeInTheDocument();
    expect(within(dialog).getByLabelText('CPF (opcional)')).toBeInTheDocument();
    const data = within(dialog).getByLabelText('Data da visita');
    expect(data).toHaveAttribute('type', 'date');
    expect(data).toHaveValue(hojeNoClube());
  });

  it('valida nome obrigatório sem chamar a API', async () => {
    const api = backendAssociados();
    const { user } = renderAdmin({ route: '/admin/associados' });
    const dialog = await abrirModal(user, 'Maria Souza');

    await user.click(within(dialog).getByRole('button', { name: 'Emitir convite' }));

    expect(await within(dialog).findByText(/informe o nome do convidado/i)).toBeInTheDocument();
    expect(api.porMetodo('POST_CONVIDADO')).toHaveLength(0);
  });

  it('convite gratuito: envia payload, confirma e atualiza o contador', async () => {
    const api = backendAssociados();
    const { user } = renderAdmin({ route: '/admin/associados' });
    const dialog = await abrirModal(user, 'Maria Souza');

    await user.type(within(dialog).getByLabelText('Nome do convidado'), 'Pedro Alves');
    await user.click(within(dialog).getByRole('button', { name: 'Emitir convite' }));

    await waitFor(() => expect(api.porMetodo('POST_CONVIDADO')).toHaveLength(1));
    const req = api.porMetodo('POST_CONVIDADO')[0];
    expect(req.url.pathname).toBe(`/api/v1/associados/${MARIA.id}/convidados`);
    const corpo = req.body as { nome: string; data_visita: string; cpf?: string | null };
    expect(corpo.nome).toBe('Pedro Alves');
    expect(corpo.data_visita).toBe(hojeNoClube());
    expect(corpo.cpf ?? null).toBeNull();

    expect(await screen.findByText(/convite emitido/i)).toBeInTheDocument();
    const linha = await linhaDe('Maria Souza');
    await waitFor(() => expect(within(linha).getByText('6/8 convites')).toBeInTheDocument());
  });

  it('convite excedente: aviso destacado com a taxa extra em R$', async () => {
    const api = backendAssociados();
    const { user } = renderAdmin({ route: '/admin/associados' });
    const dialog = await abrirModal(user, 'João Lima');

    await user.type(within(dialog).getByLabelText('Nome do convidado'), 'Carla Dias');
    await user.type(within(dialog).getByLabelText('CPF (opcional)'), '52998224725');
    await user.click(within(dialog).getByRole('button', { name: 'Emitir convite' }));

    const alerta = await screen.findByRole('alert');
    expect(alerta).toHaveTextContent('Franquia de convidados excedida: este convite será cobrado na próxima fatura.');
    expect(alerta).toHaveTextContent(/R\$\s?35,00/);
    expect((api.porMetodo('POST_CONVIDADO')[0].body as { cpf: string }).cpf).toBe('52998224725');

    const linha = await linhaDe('João Lima');
    await waitFor(() => expect(within(linha).getByText('9/8 convites')).toBeInTheDocument());
  });

  it('erro da API ao emitir convite é exibido', async () => {
    backendAssociados();
    server.use(
      http.post(`${API}/associados/:id/convidados`, () =>
        HttpResponse.json(
          { detail: [{ loc: ['body', 'cpf'], msg: 'Value error, CPF do convidado inválido', type: 'value_error' }] },
          { status: 422 },
        ),
      ),
    );
    const { user } = renderAdmin({ route: '/admin/associados' });
    const dialog = await abrirModal(user, 'Maria Souza');

    await user.type(within(dialog).getByLabelText('Nome do convidado'), 'Pedro Alves');
    await user.click(within(dialog).getByRole('button', { name: 'Emitir convite' }));

    expect(await within(dialog).findByRole('alert')).toHaveTextContent(/CPF do convidado inválido/);
  });
});

// ------------------------------------------------------------------------------
// CRUD de associado
// ------------------------------------------------------------------------------
describe('AssociadosPage - criar, editar e excluir', () => {
  it('validação básica no cadastro sem chamar a API', async () => {
    const api = backendAssociados();
    const { user } = renderAdmin({ route: '/admin/associados' });
    await linhaDe('Maria Souza');

    await user.click(screen.getByRole('button', { name: 'Novo associado' }));
    const dialog = await screen.findByRole('dialog', { name: /novo associado/i });
    await user.click(within(dialog).getByRole('button', { name: 'Salvar' }));

    expect((await within(dialog).findAllByText(/obrigatório/i)).length).toBeGreaterThan(0);
    expect(api.porMetodo('POST')).toHaveLength(0);
  });

  it('cria associado e atualiza a lista', async () => {
    const api = backendAssociados();
    const { user } = renderAdmin({ route: '/admin/associados' });
    await linhaDe('Maria Souza');

    await user.click(screen.getByRole('button', { name: 'Novo associado' }));
    const dialog = await screen.findByRole('dialog', { name: /novo associado/i });
    await user.type(within(dialog).getByLabelText('Nome'), 'Paula Ramos');
    await user.type(within(dialog).getByLabelText('CPF'), '39053344705');
    await user.type(within(dialog).getByLabelText('WhatsApp'), '75988887777');
    await user.type(within(dialog).getByLabelText('E-mail'), 'paula@exemplo.com');
    const dia = within(dialog).getByLabelText('Dia de vencimento');
    await user.clear(dia);
    await user.type(dia, '15');
    await user.click(within(dialog).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(api.porMetodo('POST')).toHaveLength(1));
    expect(api.porMetodo('POST')[0].body).toMatchObject({
      nome: 'Paula Ramos',
      cpf: '39053344705',
      whatsapp: '75988887777',
      email: 'paula@exemplo.com',
      dia_vencimento: 15,
    });
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());
    expect(await linhaDe('Paula Ramos')).toBeInTheDocument();
  });

  it.each([
    [409, { detail: 'Já existe um associado com este CPF.' }, /Já existe um associado com este CPF/],
    [422, { detail: [{ loc: ['body', 'cpf'], msg: 'Value error, CPF inválido', type: 'value_error' }] }, /CPF inválido/],
  ])('erro %i do backend aparece no modal', async (status, corpo, esperado) => {
    backendAssociados();
    server.use(http.post(`${API}/associados/`, () => HttpResponse.json(corpo, { status })));
    const { user } = renderAdmin({ route: '/admin/associados' });
    await linhaDe('Maria Souza');

    await user.click(screen.getByRole('button', { name: 'Novo associado' }));
    const dialog = await screen.findByRole('dialog', { name: /novo associado/i });
    await user.type(within(dialog).getByLabelText('Nome'), 'Paula Ramos');
    await user.type(within(dialog).getByLabelText('CPF'), '39053344705');
    await user.type(within(dialog).getByLabelText('WhatsApp'), '75988887777');
    await user.type(within(dialog).getByLabelText('E-mail'), 'paula@exemplo.com');
    await user.click(within(dialog).getByRole('button', { name: 'Salvar' }));

    expect(await within(dialog).findByRole('alert')).toHaveTextContent(esperado);
    expect(screen.getByRole('dialog', { name: /novo associado/i })).toBeInTheDocument();
  });

  it('edita associado via PATCH sem enviar CPF', async () => {
    const api = backendAssociados();
    const { user } = renderAdmin({ route: '/admin/associados' });
    const linha = await linhaDe('Maria Souza');

    await user.click(within(linha).getByRole('button', { name: 'Editar Maria Souza' }));
    const dialog = await screen.findByRole('dialog', { name: /editar associado/i });
    const nome = within(dialog).getByLabelText('Nome');
    expect(nome).toHaveValue('Maria Souza');
    const cpf = within(dialog).queryByLabelText('CPF');
    if (cpf) expect(cpf).toBeDisabled();

    await user.clear(nome);
    await user.type(nome, 'Maria Souza Lima');
    await user.click(within(dialog).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(api.porMetodo('PATCH')).toHaveLength(1));
    const req = api.porMetodo('PATCH')[0];
    expect(req.url.pathname).toBe(`/api/v1/associados/${MARIA.id}`);
    expect(req.body).toMatchObject({ nome: 'Maria Souza Lima' });
    expect(req.body).not.toHaveProperty('cpf');
    expect(await linhaDe('Maria Souza Lima')).toBeInTheDocument();
  });

  it('exclui associado após confirmação', async () => {
    const api = backendAssociados();
    const { user } = renderAdmin({ route: '/admin/associados' });
    const linha = await linhaDe('João Lima');

    await user.click(within(linha).getByRole('button', { name: 'Excluir João Lima' }));
    const dialog = await screen.findByRole('dialog', { name: /excluir associado/i });
    expect(dialog).toHaveTextContent('João Lima');
    expect(api.porMetodo('DELETE')).toHaveLength(0);

    await user.click(within(dialog).getByRole('button', { name: 'Confirmar exclusão' }));

    await waitFor(() => expect(api.porMetodo('DELETE')).toHaveLength(1));
    expect(api.porMetodo('DELETE')[0].url.pathname).toBe(`/api/v1/associados/${JOAO.id}`);
    await waitFor(() => expect(screen.queryByRole('row', { name: /João Lima/ })).not.toBeInTheDocument());
  });
});

// ------------------------------------------------------------------------------
// Importação de planilha
// ------------------------------------------------------------------------------
describe('AssociadosPage - importar planilha', () => {
  const RELATORIO = {
    total_lidos: 10,
    total_importados: 6,
    total_atualizados: 2,
    total_ignorados_duplicados: 1,
    erros: [{ linha: 5, campo: 'cpf', motivo: 'CPF inválido (dígito verificador)' }],
  };

  function capturarImportacao(resposta: unknown = RELATORIO, status = 200) {
    const envios: { atualizar: string | null; arquivo: string | null; conteudo: string | null }[] = [];
    server.use(
      http.post(`${API}/associados/importar`, async ({ request }) => {
        const url = new URL(request.url);
        const arquivo = (await request.formData()).get('file');
        envios.push({
          atualizar: url.searchParams.get('atualizar_existentes'),
          arquivo: arquivo instanceof File ? arquivo.name : null,
          conteudo: arquivo instanceof File ? await arquivo.text() : null,
        });
        return HttpResponse.json(resposta, { status });
      }),
    );
    return envios;
  }

  async function abrirImportacao(user: ReturnType<typeof userEvent.setup>) {
    await linhaDe('Maria Souza');
    await user.click(screen.getByRole('button', { name: 'Importar planilha' }));
    return screen.findByRole('dialog', { name: /importar planilha/i });
  }

  it('envia o arquivo com atualizar_existentes=true e mostra o relatório', async () => {
    const api = backendAssociados();
    const envios = capturarImportacao();
    const { user } = renderAdmin({ route: '/admin/associados' });
    const dialog = await abrirImportacao(user);

    const input = within(dialog).getByLabelText('Arquivo da planilha');
    expect(input.getAttribute('accept')).toMatch(/\.xlsx/);
    expect(input.getAttribute('accept')).toMatch(/\.csv/);
    await user.upload(input, new File(['nome;cpf\nAna;52998224725'], 'socios.csv', { type: 'text/csv' }));
    await user.click(within(dialog).getByLabelText('Atualizar existentes'));
    const listasAntes = api.listas().length;
    await user.click(within(dialog).getByRole('button', { name: 'Enviar planilha' }));

    await waitFor(() => expect(envios).toHaveLength(1));
    expect(envios[0]).toEqual({ atualizar: 'true', arquivo: 'socios.csv', conteudo: 'nome;cpf\nAna;52998224725' });

    expect(await screen.findByTestId('import-total-lidos')).toHaveTextContent('10');
    expect(screen.getByTestId('import-total-importados')).toHaveTextContent('6');
    expect(screen.getByTestId('import-total-atualizados')).toHaveTextContent('2');
    expect(screen.getByTestId('import-total-ignorados')).toHaveTextContent('1');
    expect(screen.getByText(/linha 5/i)).toBeInTheDocument();
    expect(screen.getByText(/CPF inválido \(dígito verificador\)/)).toBeInTheDocument();

    await waitFor(() => expect(api.listas().length).toBeGreaterThan(listasAntes));
  });

  it('sem marcar a opção não atualiza existentes', async () => {
    backendAssociados();
    const envios = capturarImportacao();
    const { user } = renderAdmin({ route: '/admin/associados' });
    const dialog = await abrirImportacao(user);

    await user.upload(
      within(dialog).getByLabelText('Arquivo da planilha'),
      new File(['x'], 'socios.xlsx', { type: 'application/vnd.openxmlformats-officedocument.spreadsheetml.sheet' }),
    );
    await user.click(within(dialog).getByRole('button', { name: 'Enviar planilha' }));

    await waitFor(() => expect(envios).toHaveLength(1));
    expect(envios[0].atualizar ?? 'false').toBe('false');
    expect(envios[0].arquivo).toBe('socios.xlsx');
  });

  it('rejeita extensão inválida sem enviar', async () => {
    backendAssociados();
    const envios = capturarImportacao();
    renderAdmin({ route: '/admin/associados' });
    const user = userEvent.setup({ applyAccept: false });
    const dialog = await abrirImportacao(user);

    await user.upload(within(dialog).getByLabelText('Arquivo da planilha'), new File(['%PDF'], 'socios.pdf', { type: 'application/pdf' }));
    await user.click(within(dialog).getByRole('button', { name: 'Enviar planilha' }));

    expect(await within(dialog).findByRole('alert')).toHaveTextContent(/formato/i);
    expect(envios).toHaveLength(0);
  });

  it('sem arquivo não envia', async () => {
    backendAssociados();
    const envios = capturarImportacao();
    const { user } = renderAdmin({ route: '/admin/associados' });
    const dialog = await abrirImportacao(user);

    await user.click(within(dialog).getByRole('button', { name: 'Enviar planilha' }));

    expect(envios).toHaveLength(0);
  });

  it('erro HTTP da importação mostra o detail', async () => {
    backendAssociados();
    capturarImportacao({ detail: 'Arquivo excede o limite máximo permitido de 5 MB.' }, 413);
    const { user } = renderAdmin({ route: '/admin/associados' });
    const dialog = await abrirImportacao(user);

    await user.upload(within(dialog).getByLabelText('Arquivo da planilha'), new File(['x'], 'grande.csv', { type: 'text/csv' }));
    await user.click(within(dialog).getByRole('button', { name: 'Enviar planilha' }));

    expect(await within(dialog).findByRole('alert')).toHaveTextContent('Arquivo excede o limite máximo permitido de 5 MB.');
  });
});
