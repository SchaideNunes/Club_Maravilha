/**
 * Cadastro de Sócios - planos de mensalidade (`src/admin/pages/PlanosPage.tsx`, rota /admin/planos).
 *
 * Contratos de UI:
 * - <h1>"Planos"</h1>; aviso com a mensalidade padrão da configuração ("Sócios sem plano pagam a
 *   mensalidade padrão de R$ <valor>").
 * - GET /planos/ (todos). Tabela: Nome, Descrição, Mensalidade ("R$ x" ou "Isento" quando 0), Sócios,
 *   Situação ("Ativo" | "Desativado"), Ações. Vazio: "Nenhum plano cadastrado".
 * - "Novo plano" -> dialog "Novo plano" (Nome, Descrição, Valor da mensalidade) -> POST /planos/
 *   {nome, descricao|null, valor_mensalidade}. Nome/valor vazios -> "obrigatório" sem chamar a API.
 * - Por linha: "Editar <nome>" -> dialog "Editar plano" -> PATCH /planos/{id};
 *   "Desativar <nome>" / "Ativar <nome>" -> PATCH {ativo}; "Excluir <nome>" -> dialog "Excluir plano"
 *   -> "Confirmar exclusão" -> DELETE (409 mostra o detail em role="alert").
 */
import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server } from '../../test/server';
import { API, PlanoFixture, criarPlano } from '../../test/handlers';
import { renderAdmin } from '../../test/utils';

const FAMILIAR = criarPlano({ id: 'p-familiar', nome: 'Familiar', descricao: 'Titular e família', valor_mensalidade: '220.00', total_associados: 12 });
const REMIDO = criarPlano({ id: 'p-remido', nome: 'Remido', valor_mensalidade: '0.00', total_associados: 3 });

type Req = { method: string; url: URL; body?: unknown };

function backendPlanos(inicial: PlanoFixture[] = [FAMILIAR, REMIDO]) {
  let planos = [...inicial];
  const reqs: Req[] = [];
  server.use(
    http.get(`${API}/planos/`, () => HttpResponse.json(planos)),
    http.post(`${API}/planos/`, async ({ request }) => {
      const body = (await request.json()) as Partial<PlanoFixture>;
      reqs.push({ method: 'POST', url: new URL(request.url), body });
      const novo = criarPlano({ ...body, id: 'p-novo' });
      planos = [...planos, novo].sort((a, b) => a.nome.localeCompare(b.nome));
      return HttpResponse.json(novo, { status: 201 });
    }),
    http.patch(`${API}/planos/:id`, async ({ request, params }) => {
      const body = (await request.json()) as Partial<PlanoFixture>;
      reqs.push({ method: 'PATCH', url: new URL(request.url), body });
      planos = planos.map((p) => (p.id === params.id ? { ...p, ...body } : p));
      return HttpResponse.json(planos.find((p) => p.id === params.id));
    }),
    http.delete(`${API}/planos/:id`, ({ request, params }) => {
      reqs.push({ method: 'DELETE', url: new URL(request.url) });
      planos = planos.filter((p) => p.id !== params.id);
      return new HttpResponse(null, { status: 204 });
    }),
  );
  return { reqs, por: (m: string) => reqs.filter((r) => r.method === m) };
}

describe('PlanosPage', () => {
  it('lista os planos com valores, sócios e situação', async () => {
    backendPlanos();
    renderAdmin({ route: '/admin/planos' });

    expect(await screen.findByRole('heading', { level: 1, name: 'Planos' })).toBeInTheDocument();
    expect(await screen.findByText(/mensalidade padrão de R\$ 150,00/)).toBeInTheDocument();

    const familiar = await screen.findByRole('row', { name: /Familiar/ });
    expect(familiar).toHaveTextContent('Titular e família');
    expect(familiar).toHaveTextContent('R$ 220,00');
    expect(familiar).toHaveTextContent('12');
    expect(familiar).toHaveTextContent('Ativo');

    expect(screen.getByRole('row', { name: /Remido/ })).toHaveTextContent('Isento');
  });

  it('estado vazio', async () => {
    backendPlanos([]);
    renderAdmin({ route: '/admin/planos' });

    expect(await screen.findByText('Nenhum plano cadastrado')).toBeInTheDocument();
  });

  it('cria plano e valida obrigatórios', async () => {
    const api = backendPlanos();
    const { user } = renderAdmin({ route: '/admin/planos' });
    await screen.findByRole('row', { name: /Familiar/ });

    await user.click(screen.getByRole('button', { name: 'Novo plano' }));
    const dialog = await screen.findByRole('dialog', { name: 'Novo plano' });
    await user.click(within(dialog).getByRole('button', { name: 'Salvar' }));
    expect((await within(dialog).findAllByText(/obrigatório/i)).length).toBe(2);
    expect(api.por('POST')).toHaveLength(0);

    await user.type(within(dialog).getByLabelText('Nome'), 'Individual');
    await user.type(within(dialog).getByLabelText('Valor da mensalidade'), '150,50');
    await user.click(within(dialog).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(api.por('POST')).toHaveLength(1));
    expect(api.por('POST')[0].body).toEqual({ nome: 'Individual', descricao: null, valor_mensalidade: '150.50' });
    expect(await screen.findByRole('row', { name: /Individual/ })).toHaveTextContent('R$ 150,50');
  });

  it('edita e desativa/ativa um plano', async () => {
    const api = backendPlanos();
    const { user } = renderAdmin({ route: '/admin/planos' });
    const familiar = await screen.findByRole('row', { name: /Familiar/ });

    await user.click(within(familiar).getByRole('button', { name: 'Editar Familiar' }));
    const dialog = await screen.findByRole('dialog', { name: 'Editar plano' });
    const valor = within(dialog).getByLabelText('Valor da mensalidade');
    expect(valor).toHaveValue('220,00');
    await user.clear(valor);
    await user.type(valor, '240');
    await user.click(within(dialog).getByRole('button', { name: 'Salvar' }));

    await waitFor(() => expect(api.por('PATCH')).toHaveLength(1));
    expect(api.por('PATCH')[0].url.pathname).toBe('/api/v1/planos/p-familiar');
    expect(api.por('PATCH')[0].body).toMatchObject({ valor_mensalidade: '240.00' });
    expect(await screen.findByRole('row', { name: /Familiar/ })).toHaveTextContent('R$ 240,00');

    await user.click(screen.getByRole('button', { name: 'Desativar Familiar' }));
    await waitFor(() => expect(api.por('PATCH')).toHaveLength(2));
    expect(api.por('PATCH')[1].body).toEqual({ ativo: false });
    expect(await screen.findByRole('row', { name: /Familiar/ })).toHaveTextContent('Desativado');

    await user.click(screen.getByRole('button', { name: 'Ativar Familiar' }));
    await waitFor(() => expect(api.por('PATCH')).toHaveLength(3));
    expect(api.por('PATCH')[2].body).toEqual({ ativo: true });
  });

  it('exclui plano sem sócios e mostra o erro 409 quando há vínculo', async () => {
    const api = backendPlanos();
    const { user } = renderAdmin({ route: '/admin/planos' });
    await screen.findByRole('row', { name: /Remido/ });

    await user.click(screen.getByRole('button', { name: 'Excluir Remido' }));
    let dialog = await screen.findByRole('dialog', { name: 'Excluir plano' });
    await user.click(within(dialog).getByRole('button', { name: 'Confirmar exclusão' }));
    await waitFor(() => expect(api.por('DELETE')).toHaveLength(1));
    await waitFor(() => expect(screen.queryByRole('row', { name: /Remido/ })).not.toBeInTheDocument());

    server.use(
      http.delete(`${API}/planos/:id`, () =>
        HttpResponse.json({ detail: 'Este plano está vinculado a associados. Desative-o em vez de excluir.' }, { status: 409 }),
      ),
    );
    await user.click(screen.getByRole('button', { name: 'Excluir Familiar' }));
    dialog = await screen.findByRole('dialog', { name: 'Excluir plano' });
    await user.click(within(dialog).getByRole('button', { name: 'Confirmar exclusão' }));

    expect(await within(dialog).findByRole('alert')).toHaveTextContent(/Desative-o em vez de excluir/);
  });
});
