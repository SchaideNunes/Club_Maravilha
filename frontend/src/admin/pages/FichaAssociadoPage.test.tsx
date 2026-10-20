/**
 * Cadastro de Sócios - ficha completa do associado (`src/admin/pages/FichaAssociadoPage.tsx`,
 * rota /admin/associados/:id).
 *
 * Contratos de UI:
 * - GET /associados/{id}. Cabeçalho: <h1> com o nome, status do cadastro ("Ativo" | "Inadimplente" |
 *   "Bloqueado" | "Inativo"), situação financeira, plano ("<nome do plano>" ou "Mensalidade padrão"),
 *   CPF, WhatsApp e "Sócio desde <dd/mm/aaaa>". Link "Voltar para associados". 404 -> "Associado não encontrado".
 * - Foto: com foto_url, <img alt="Foto de <nome>"> carregada com o token (GET /associados/{id}/foto como blob);
 *   input file "Enviar foto" -> PUT /associados/{id}/foto (multipart `file`); botão "Remover foto" -> DELETE.
 * - Abas (role="tab"): "Dados cadastrais" (padrão), "Família", "Financeiro", "Convidados", "Mensagens".
 *   * Dados cadastrais: formulário completo pré-preenchido (CPF desabilitado); "Salvar alterações" ->
 *     PATCH /associados/{id} sem `cpf`; sucesso -> "Alterações salvas".
 *   * Família: GET /associados/{id}/familia/; tabela com nome, parentesco e nascimento; "Adicionar familiar"
 *     -> dialog "Adicionar familiar" (Nome, Parentesco, CPF (opcional), Data de nascimento) -> POST;
 *     "Editar <nome>" -> dialog "Editar familiar" -> PATCH; "Remover <nome>" -> dialog "Remover familiar"
 *     -> "Confirmar remoção" -> DELETE. Vazio: "Nenhum familiar cadastrado".
 *   * Financeiro: GET /faturas/?associado_id={id}; referência, vencimento, valor e status (Paga, Pendente,
 *     Atrasada, Cancelada). Vazio: "Nenhuma fatura".
 *   * Convidados: GET /convidados/?associado_id={id}; nome, data da visita, status e cobrança.
 *     Vazio: "Nenhum convite emitido".
 *   * Mensagens: GET /whatsapp/logs?associado_id={id}; etapa, status e data. Vazio: "Nenhuma mensagem enviada".
 * - "Inativar associado" -> dialog "Inativar associado" com "Motivo (opcional)" e "Confirmar inativação" ->
 *   POST /associados/{id}/inativar {motivo}; depois mostra "Inativo", o aviso "Associado inativo desde
 *   <data>" com o motivo, o resumo do que foi cancelado e o botão "Reativar associado" ->
 *   POST /associados/{id}/reativar. Sócio inativo não tem "+ Adicionar convidado".
 */
import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { beforeEach, describe, expect, it } from 'vitest';
import { server } from '../../test/server';
import {
  API,
  AssociadoFixture,
  MembroFamiliaFixture,
  criarAssociado,
  criarFatura,
  criarMembroFamilia,
  paginado,
  RESUMO_FATURAS_VAZIO,
} from '../../test/handlers';
import { renderAdmin } from '../../test/utils';

const ID = '22222222-2222-4222-8222-222222222222';
const ROTA = `/admin/associados/${ID}`;

type Req = { method: string; url: URL; body?: unknown };

function backendFicha(inicial: Partial<AssociadoFixture> = {}, familiaInicial: MembroFamiliaFixture[] = []) {
  let socio = criarAssociado({ id: ID, plano: { id: 'p1', nome: 'Familiar', valor_mensalidade: '220.00' }, ...inicial });
  let familia = [...familiaInicial];
  const reqs: Req[] = [];
  const registrar = async (method: string, request: Request) => {
    const body = ['GET', 'DELETE'].includes(method) || request.headers.get('content-type')?.includes('multipart')
      ? undefined
      : await request.json().catch(() => undefined);
    reqs.push({ method, url: new URL(request.url), body });
    return body;
  };

  server.use(
    http.get(`${API}/associados/:id`, async ({ request }) => {
      await registrar('GET', request);
      return HttpResponse.json(socio);
    }),
    http.patch(`${API}/associados/:id`, async ({ request }) => {
      const body = (await registrar('PATCH', request)) as Partial<AssociadoFixture>;
      socio = { ...socio, ...body };
      return HttpResponse.json(socio);
    }),
    http.post(`${API}/associados/:id/inativar`, async ({ request }) => {
      const body = (await registrar('INATIVAR', request)) as { motivo?: string };
      socio = { ...socio, status: 'INATIVO', data_inativacao: '2026-10-20', motivo_inativacao: body?.motivo ?? null };
      return HttpResponse.json({ associado: socio, faturas_canceladas: 1, convites_cancelados: 2, reservas_canceladas: 0 });
    }),
    http.post(`${API}/associados/:id/reativar`, async ({ request }) => {
      await registrar('REATIVAR', request);
      socio = { ...socio, status: 'ATIVO', data_inativacao: null, motivo_inativacao: null };
      return HttpResponse.json(socio);
    }),
    http.put(`${API}/associados/:id/foto`, async ({ request }) => {
      const form = await request.formData();
      reqs.push({ method: 'PUT_FOTO', url: new URL(request.url), body: form.get('file') });
      socio = { ...socio, foto_url: `/api/v1/associados/${ID}/foto?v=2` };
      return HttpResponse.json(socio);
    }),
    http.get(`${API}/associados/:id/foto`, () =>
      new HttpResponse(new Uint8Array([0x89, 0x50, 0x4e, 0x47]), { headers: { 'Content-Type': 'image/png' } }),
    ),
    http.delete(`${API}/associados/:id/foto`, async ({ request }) => {
      await registrar('DELETE_FOTO', request);
      socio = { ...socio, foto_url: null };
      return new HttpResponse(null, { status: 204 });
    }),
    http.get(`${API}/associados/:id/familia/`, async ({ request }) => {
      await registrar('GET_FAMILIA', request);
      return HttpResponse.json(familia);
    }),
    http.post(`${API}/associados/:id/familia/`, async ({ request }) => {
      const body = (await registrar('POST_FAMILIA', request)) as Partial<MembroFamiliaFixture>;
      const novo = criarMembroFamilia({ ...body, id: `m-${familia.length + 1}` });
      familia = [...familia, novo];
      return HttpResponse.json(novo, { status: 201 });
    }),
    http.patch(`${API}/associados/:id/familia/:membroId`, async ({ request, params }) => {
      const body = (await registrar('PATCH_FAMILIA', request)) as Partial<MembroFamiliaFixture>;
      familia = familia.map((m) => (m.id === params.membroId ? { ...m, ...body } : m));
      return HttpResponse.json(familia.find((m) => m.id === params.membroId));
    }),
    http.delete(`${API}/associados/:id/familia/:membroId`, async ({ request, params }) => {
      await registrar('DELETE_FAMILIA', request);
      familia = familia.filter((m) => m.id !== params.membroId);
      return new HttpResponse(null, { status: 204 });
    }),
  );

  return { reqs, por: (m: string) => reqs.filter((r) => r.method === m) };
}

beforeEach(() => {
  // jsdom não implementa object URLs; a foto é baixada como blob e exibida por uma URL temporária
  Object.defineProperty(URL, 'createObjectURL', { value: () => 'blob:foto-socio', configurable: true, writable: true });
  Object.defineProperty(URL, 'revokeObjectURL', { value: () => undefined, configurable: true, writable: true });
});

describe('FichaAssociadoPage - cabeçalho', () => {
  it('mostra os dados principais do sócio', async () => {
    backendFicha({ situacao_financeira: 'PENDENTE' });
    renderAdmin({ route: ROTA });

    expect(await screen.findByRole('heading', { level: 1, name: 'Maria Souza' })).toBeInTheDocument();
    const cabecalho = screen.getByTestId('cabecalho-associado');
    expect(within(cabecalho).getByText('Ativo')).toBeInTheDocument();
    expect(within(cabecalho).getByText('Pendente')).toBeInTheDocument();
    expect(cabecalho).toHaveTextContent('Familiar');
    expect(cabecalho).toHaveTextContent('529.982.247-25');
    expect(cabecalho).toHaveTextContent('(75) 99999-8888');
    expect(cabecalho).toHaveTextContent('Sócio desde 10/01/2026');
    expect(screen.getByRole('link', { name: 'Voltar para associados' })).toHaveAttribute('href', '/admin/associados');
  });

  it('sem plano mostra "Mensalidade padrão"', async () => {
    backendFicha({ plano: null });
    renderAdmin({ route: ROTA });

    expect(await screen.findByTestId('cabecalho-associado')).toHaveTextContent('Mensalidade padrão');
  });

  it('associado inexistente', async () => {
    server.use(http.get(`${API}/associados/:id`, () => HttpResponse.json({ detail: 'Associado não encontrado.' }, { status: 404 })));
    renderAdmin({ route: ROTA });

    expect(await screen.findByText('Associado não encontrado')).toBeInTheDocument();
  });
});

describe('FichaAssociadoPage - foto', () => {
  it('exibe a foto baixada com o token', async () => {
    backendFicha({ foto_url: `/api/v1/associados/${ID}/foto?v=1` });
    renderAdmin({ route: ROTA });

    const foto = await screen.findByRole('img', { name: 'Foto de Maria Souza' });
    expect(foto).toHaveAttribute('src', 'blob:foto-socio');
  });

  it('envia e remove a foto', async () => {
    const api = backendFicha();
    const { user } = renderAdmin({ route: ROTA });
    await screen.findByRole('heading', { level: 1, name: 'Maria Souza' });
    expect(screen.queryByRole('button', { name: 'Remover foto' })).not.toBeInTheDocument();

    const arquivo = new File([new Uint8Array([0x89, 0x50])], 'maria.png', { type: 'image/png' });
    await user.upload(screen.getByLabelText('Enviar foto'), arquivo);

    await waitFor(() => expect(api.por('PUT_FOTO')).toHaveLength(1));
    expect((api.por('PUT_FOTO')[0].body as File).name).toBe('maria.png');
    expect(await screen.findByRole('img', { name: 'Foto de Maria Souza' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Remover foto' }));
    await waitFor(() => expect(api.por('DELETE_FOTO')).toHaveLength(1));
    await waitFor(() => expect(screen.queryByRole('img', { name: 'Foto de Maria Souza' })).not.toBeInTheDocument());
  });
});

describe('FichaAssociadoPage - dados cadastrais', () => {
  it('edita via PATCH sem enviar CPF', async () => {
    const api = backendFicha({ cidade: 'Feira de Santana', uf: 'BA' });
    const { user } = renderAdmin({ route: ROTA });

    expect(await screen.findByRole('tab', { name: 'Dados cadastrais' })).toHaveAttribute('aria-selected', 'true');
    const nome = await screen.findByLabelText('Nome');
    expect(nome).toHaveValue('Maria Souza');
    expect(screen.getByLabelText('CPF')).toBeDisabled();
    expect(screen.getByLabelText('Cidade')).toHaveValue('Feira de Santana');

    await user.clear(nome);
    await user.type(nome, 'Maria Souza Lima');
    await user.type(screen.getByLabelText('Profissão'), 'Médica');
    await user.click(screen.getByRole('button', { name: 'Salvar alterações' }));

    await waitFor(() => expect(api.por('PATCH')).toHaveLength(1));
    const body = api.por('PATCH')[0].body as Record<string, unknown>;
    expect(body).toMatchObject({ nome: 'Maria Souza Lima', profissao: 'Médica', cidade: 'Feira de Santana', uf: 'BA' });
    expect(body).not.toHaveProperty('cpf');
    expect(await screen.findByText('Alterações salvas')).toBeInTheDocument();
    expect(await screen.findByRole('heading', { level: 1, name: 'Maria Souza Lima' })).toBeInTheDocument();
  });
});

describe('FichaAssociadoPage - família', () => {
  it('lista, adiciona, edita e remove familiares', async () => {
    const api = backendFicha({}, [criarMembroFamilia({ id: 'm-pedro', nome: 'Pedro Souza', parentesco: 'FILHO' })]);
    const { user } = renderAdmin({ route: ROTA });

    await user.click(await screen.findByRole('tab', { name: 'Família' }));
    const pedro = await screen.findByRole('row', { name: /Pedro Souza/ });
    expect(pedro).toHaveTextContent('Filho(a)');
    expect(pedro).toHaveTextContent('20/05/2014');

    // Adicionar
    await user.click(screen.getByRole('button', { name: 'Adicionar familiar' }));
    const novo = await screen.findByRole('dialog', { name: 'Adicionar familiar' });
    await user.type(within(novo).getByLabelText('Nome'), 'João Souza');
    await user.selectOptions(within(novo).getByLabelText('Parentesco'), 'Cônjuge');
    await user.type(within(novo).getByLabelText('CPF (opcional)'), '11144477735');
    await user.click(within(novo).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(api.por('POST_FAMILIA')).toHaveLength(1));
    expect(api.por('POST_FAMILIA')[0].body).toMatchObject({ nome: 'João Souza', parentesco: 'CONJUGE', cpf: '11144477735' });
    expect(await screen.findByRole('row', { name: /João Souza/ })).toHaveTextContent('Cônjuge');

    // Editar
    await user.click(within(screen.getByRole('row', { name: /Pedro Souza/ })).getByRole('button', { name: 'Editar Pedro Souza' }));
    const editar = await screen.findByRole('dialog', { name: 'Editar familiar' });
    const nome = within(editar).getByLabelText('Nome');
    expect(nome).toHaveValue('Pedro Souza');
    await user.clear(nome);
    await user.type(nome, 'Pedro Souza Filho');
    await user.click(within(editar).getByRole('button', { name: 'Salvar' }));
    await waitFor(() => expect(api.por('PATCH_FAMILIA')).toHaveLength(1));
    expect(api.por('PATCH_FAMILIA')[0].url.pathname).toBe(`/api/v1/associados/${ID}/familia/m-pedro`);
    expect(await screen.findByRole('row', { name: /Pedro Souza Filho/ })).toBeInTheDocument();

    // Remover
    await user.click(screen.getByRole('button', { name: 'Remover Pedro Souza Filho' }));
    const remover = await screen.findByRole('dialog', { name: 'Remover familiar' });
    await user.click(within(remover).getByRole('button', { name: 'Confirmar remoção' }));
    await waitFor(() => expect(api.por('DELETE_FAMILIA')).toHaveLength(1));
    await waitFor(() => expect(screen.queryByRole('row', { name: /Pedro Souza Filho/ })).not.toBeInTheDocument());
  });

  it('valida nome e parentesco sem chamar a API', async () => {
    const api = backendFicha();
    const { user } = renderAdmin({ route: ROTA });

    await user.click(await screen.findByRole('tab', { name: 'Família' }));
    expect(await screen.findByText('Nenhum familiar cadastrado')).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Adicionar familiar' }));
    const dialog = await screen.findByRole('dialog', { name: 'Adicionar familiar' });
    await user.click(within(dialog).getByRole('button', { name: 'Salvar' }));

    expect((await within(dialog).findAllByText(/obrigatório/i)).length).toBe(2);
    expect(api.por('POST_FAMILIA')).toHaveLength(0);
  });
});

describe('FichaAssociadoPage - histórico', () => {
  it('financeiro lista as faturas do sócio', async () => {
    backendFicha();
    const consultas: URL[] = [];
    server.use(
      http.get(`${API}/faturas/`, ({ request }) => {
        consultas.push(new URL(request.url));
        return HttpResponse.json({
          ...paginado([
            criarFatura({ id: 'f1', referencia_mes: '2026-10', data_vencimento: '2026-10-10', status: 'PAGO' }),
            criarFatura({ id: 'f2', referencia_mes: '2026-11', data_vencimento: '2026-11-10', status: 'ATRASADA', valor_total: '185.00' }),
          ]),
          resumo: RESUMO_FATURAS_VAZIO,
        });
      }),
    );
    const { user } = renderAdmin({ route: ROTA });

    await user.click(await screen.findByRole('tab', { name: 'Financeiro' }));

    const outubro = await screen.findByRole('row', { name: /10\/2026/ });
    expect(outubro).toHaveTextContent('Paga');
    const novembro = screen.getByRole('row', { name: /11\/2026/ });
    expect(novembro).toHaveTextContent('Atrasada');
    expect(novembro).toHaveTextContent('R$ 185,00');
    expect(consultas[0].searchParams.get('associado_id')).toBe(ID);
  });

  it('convidados e mensagens do sócio', async () => {
    backendFicha();
    const consultas: URL[] = [];
    server.use(
      http.get(`${API}/convidados/`, ({ request }) => {
        consultas.push(new URL(request.url));
        return HttpResponse.json([
          {
            id: 'c1', associado_titular_id: ID, nome: 'Ana Visitante', cpf: null, data_visita: '2026-10-05',
            qr_code_token: 't', status: 'UTILIZADO', is_gratuito: false, valor_cobrado: '35.00',
            fatura_agregada_id: null, check_in_at: null, created_at: '2026-10-01T12:00:00Z', updated_at: '2026-10-01T12:00:00Z',
          },
        ]);
      }),
      http.get(`${API}/whatsapp/logs`, ({ request }) => {
        consultas.push(new URL(request.url));
        return HttpResponse.json([
          {
            id: 'l1', associado_id: ID, fatura_id: null, destinatario: '5575999998888', etapa: 'D0',
            mensagem: 'Vence hoje', status: 'SUCESSO', erro: null, enviado_em: '2026-10-10T11:00:00Z',
          },
        ]);
      }),
    );
    const { user } = renderAdmin({ route: ROTA });

    await user.click(await screen.findByRole('tab', { name: 'Convidados' }));
    const ana = await screen.findByRole('row', { name: /Ana Visitante/ });
    expect(ana).toHaveTextContent('05/10/2026');
    expect(ana).toHaveTextContent('Utilizado');
    expect(ana).toHaveTextContent('R$ 35,00');

    await user.click(screen.getByRole('tab', { name: 'Mensagens' }));
    const msg = await screen.findByRole('row', { name: /Cobrança D-0/ });
    expect(msg).toHaveTextContent('Enviada');

    expect(consultas.map((u) => u.searchParams.get('associado_id'))).toEqual([ID, ID]);
  });

  it('estados vazios', async () => {
    backendFicha();
    server.use(http.get(`${API}/convidados/`, () => HttpResponse.json([])));
    const { user } = renderAdmin({ route: ROTA });

    await user.click(await screen.findByRole('tab', { name: 'Financeiro' }));
    expect(await screen.findByText('Nenhuma fatura')).toBeInTheDocument();
    await user.click(screen.getByRole('tab', { name: 'Convidados' }));
    expect(await screen.findByText('Nenhum convite emitido')).toBeInTheDocument();
    await user.click(screen.getByRole('tab', { name: 'Mensagens' }));
    expect(await screen.findByText('Nenhuma mensagem enviada')).toBeInTheDocument();
  });
});

describe('FichaAssociadoPage - inativação', () => {
  it('inativa com motivo, mostra o resumo e permite reativar', async () => {
    const api = backendFicha();
    const { user } = renderAdmin({ route: ROTA });

    await screen.findByRole('heading', { level: 1, name: 'Maria Souza' });
    expect(screen.getByRole('button', { name: '+ Adicionar convidado' })).toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Inativar associado' }));
    const dialog = await screen.findByRole('dialog', { name: 'Inativar associado' });
    expect(dialog).toHaveTextContent(/histórico/i);
    await user.type(within(dialog).getByLabelText('Motivo (opcional)'), 'Mudou de cidade');
    await user.click(within(dialog).getByRole('button', { name: 'Confirmar inativação' }));

    await waitFor(() => expect(api.por('INATIVAR')).toHaveLength(1));
    expect(api.por('INATIVAR')[0].body).toEqual({ motivo: 'Mudou de cidade' });
    await waitFor(() => expect(screen.queryByRole('dialog')).not.toBeInTheDocument());

    const aviso = await screen.findByText(/Associado inativo desde 20\/10\/2026/);
    expect(aviso.closest('[role="status"]')).toHaveTextContent('Mudou de cidade');
    expect(screen.getByText(/1 fatura.*2 convites.*0 reservas/)).toBeInTheDocument();
    expect(within(screen.getByTestId('cabecalho-associado')).getByText('Inativo')).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: '+ Adicionar convidado' })).not.toBeInTheDocument();

    await user.click(screen.getByRole('button', { name: 'Reativar associado' }));
    await waitFor(() => expect(api.por('REATIVAR')).toHaveLength(1));
    expect(await screen.findByRole('button', { name: 'Inativar associado' })).toBeInTheDocument();
    expect(within(screen.getByTestId('cabecalho-associado')).getByText('Ativo')).toBeInTheDocument();
  });

  it('sócio já inativo abre com o aviso e o botão de reativar', async () => {
    backendFicha({ status: 'INATIVO', data_inativacao: '2026-09-01', motivo_inativacao: 'Pediu desligamento' });
    renderAdmin({ route: ROTA });

    expect(await screen.findByText(/Associado inativo desde 01\/09\/2026/)).toBeInTheDocument();
    expect(screen.getByText(/Pediu desligamento/)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Reativar associado' })).toBeInTheDocument();
    expect(screen.queryByRole('button', { name: 'Inativar associado' })).not.toBeInTheDocument();
  });
});
