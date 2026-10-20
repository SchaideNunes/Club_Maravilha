/**
 * Cadastro de Sócios - página de cadastro completo (`src/admin/pages/NovoAssociadoPage.tsx`,
 * rota /admin/associados/novo).
 *
 * Contratos de UI:
 * - <h1>"Novo associado"</h1> e um formulário dividido em grupos (fieldset/legend): "Dados pessoais",
 *   "Contato", "Endereço", "Plano e cobrança" e "Observações".
 * - Campos (label): Nome, CPF, Data de nascimento, Sexo, RG, Profissão, WhatsApp, E-mail, CEP,
 *   Logradouro, Número, Complemento, Bairro, Cidade, UF, Plano, Dia de vencimento, Observações.
 * - Obrigatórios: Nome, CPF, WhatsApp, E-mail (mensagens contendo "obrigatório", sem chamar a API).
 * - CEP: ao completar 8 dígitos consulta https://viacep.com.br/ws/<cep>/json/ e preenche Logradouro,
 *   Bairro, Cidade e UF; `{erro: true}` -> "CEP não encontrado" (o resto do formulário segue editável).
 * - Plano: <select> com "Mensalidade padrão (R$ <valor da configuração>)" (valor vazio) e os planos
 *   ativos (GET /planos/?ativo=true) no formato "<nome> — R$ <valor>". Padrão não envia plano_id.
 * - "Cadastrar associado" -> POST /associados/ apenas com os campos preenchidos (dia_vencimento number)
 *   e, no sucesso, abre a ficha /admin/associados/<id>. Erros 409/422 em role="alert".
 * - "Cancelar" volta para /admin/associados.
 */
import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server } from '../../test/server';
import { API, criarAssociado, criarPlano } from '../../test/handlers';
import { renderAdmin } from '../../test/utils';

const VIACEP = 'https://viacep.com.br/ws/:cep/json/';
const NOVO_ID = '44444444-4444-4444-8444-444444444444';

function backendCadastro() {
  const posts: unknown[] = [];
  const consultasPlanos: URL[] = [];
  server.use(
    http.get(`${API}/planos/`, ({ request }) => {
      consultasPlanos.push(new URL(request.url));
      return HttpResponse.json([criarPlano({ id: 'plano-familiar', nome: 'Familiar', valor_mensalidade: '220.00' })]);
    }),
    http.post(`${API}/associados/`, async ({ request }) => {
      const body = await request.json();
      posts.push(body);
      return HttpResponse.json(criarAssociado({ ...(body as object), id: NOVO_ID }), { status: 201 });
    }),
    http.get(`${API}/associados/:id`, () => HttpResponse.json(criarAssociado({ id: NOVO_ID, nome: 'Paula Ramos' }))),
    http.get(VIACEP, ({ params }) =>
      params.cep === '44001000'
        ? HttpResponse.json({ cep: '44001-000', logradouro: 'Rua Direita', bairro: 'Centro', localidade: 'Feira de Santana', uf: 'BA' })
        : HttpResponse.json({ erro: true }),
    ),
  );
  return { posts, consultasPlanos };
}

async function preencherObrigatorios(user: ReturnType<typeof renderAdmin>['user']) {
  await user.type(await screen.findByLabelText('Nome'), 'Paula Ramos');
  await user.type(screen.getByLabelText('CPF'), '39053344705');
  await user.type(screen.getByLabelText('WhatsApp'), '75988887777');
  await user.type(screen.getByLabelText('E-mail'), 'paula@exemplo.com');
}

describe('NovoAssociadoPage', () => {
  it('mostra o formulário completo agrupado por seções', async () => {
    backendCadastro();
    renderAdmin({ route: '/admin/associados/novo' });

    expect(await screen.findByRole('heading', { level: 1, name: 'Novo associado' })).toBeInTheDocument();
    for (const grupo of ['Dados pessoais', 'Contato', 'Endereço', 'Plano e cobrança', 'Observações']) {
      expect(screen.getByRole('group', { name: grupo })).toBeInTheDocument();
    }
    for (const campo of [
      'Nome', 'CPF', 'Data de nascimento', 'Sexo', 'RG', 'Profissão', 'WhatsApp', 'E-mail', 'CEP',
      'Logradouro', 'Número', 'Complemento', 'Bairro', 'Cidade', 'UF', 'Plano', 'Dia de vencimento', 'Observações',
    ]) {
      expect(screen.getByLabelText(campo)).toBeInTheDocument();
    }
  });

  it('valida obrigatórios sem chamar a API', async () => {
    const api = backendCadastro();
    const { user } = renderAdmin({ route: '/admin/associados/novo' });

    await user.click(await screen.findByRole('button', { name: 'Cadastrar associado' }));

    expect((await screen.findAllByText(/obrigatório/i)).length).toBe(4);
    expect(api.posts).toHaveLength(0);
  });

  it('plano: padrão com o valor da configuração e planos ativos', async () => {
    const api = backendCadastro();
    renderAdmin({ route: '/admin/associados/novo' });

    const plano = await screen.findByLabelText('Plano');
    await waitFor(() =>
      expect(within(plano).getAllByRole('option').map((o) => o.textContent)).toEqual([
        'Mensalidade padrão (R$ 150,00)',
        'Familiar — R$ 220,00',
      ]),
    );
    expect(api.consultasPlanos[0].searchParams.get('ativo')).toBe('true');
  });

  it('preenche o endereço pelo CEP', async () => {
    backendCadastro();
    const { user } = renderAdmin({ route: '/admin/associados/novo' });

    await user.type(await screen.findByLabelText('CEP'), '44001-000');

    await waitFor(() => expect(screen.getByLabelText('Logradouro')).toHaveValue('Rua Direita'));
    expect(screen.getByLabelText('Bairro')).toHaveValue('Centro');
    expect(screen.getByLabelText('Cidade')).toHaveValue('Feira de Santana');
    expect(screen.getByLabelText('UF')).toHaveValue('BA');
  });

  it('CEP inexistente avisa e mantém os campos editáveis', async () => {
    backendCadastro();
    const { user } = renderAdmin({ route: '/admin/associados/novo' });

    await user.type(await screen.findByLabelText('CEP'), '99999999');

    expect(await screen.findByText('CEP não encontrado')).toBeInTheDocument();
    expect(screen.getByLabelText('Logradouro')).toBeEnabled();
  });

  it('cadastra com os dados preenchidos e abre a ficha do sócio', async () => {
    const api = backendCadastro();
    const { user } = renderAdmin({ route: '/admin/associados/novo' });

    await preencherObrigatorios(user);
    await user.type(screen.getByLabelText('Data de nascimento'), '1990-05-04');
    await user.selectOptions(screen.getByLabelText('Sexo'), 'Feminino');
    await user.type(screen.getByLabelText('Profissão'), 'Engenheira');
    await user.type(screen.getByLabelText('CEP'), '44001000');
    await waitFor(() => expect(screen.getByLabelText('Logradouro')).toHaveValue('Rua Direita'));
    await user.type(screen.getByLabelText('Número'), '45');
    await waitFor(() => expect(within(screen.getByLabelText('Plano')).getAllByRole('option')).toHaveLength(2));
    await user.selectOptions(screen.getByLabelText('Plano'), 'Familiar — R$ 220,00');
    const dia = screen.getByLabelText('Dia de vencimento');
    await user.clear(dia);
    await user.type(dia, '15');

    await user.click(screen.getByRole('button', { name: 'Cadastrar associado' }));

    await waitFor(() => expect(api.posts).toHaveLength(1));
    const enviado = api.posts[0] as Record<string, unknown>;
    expect(enviado).toMatchObject({
      nome: 'Paula Ramos',
      cpf: '39053344705',
      whatsapp: '75988887777',
      email: 'paula@exemplo.com',
      data_nascimento: '1990-05-04',
      sexo: 'FEMININO',
      profissao: 'Engenheira',
      cep: '44001-000',
      logradouro: 'Rua Direita',
      numero: '45',
      bairro: 'Centro',
      cidade: 'Feira de Santana',
      uf: 'BA',
      plano_id: 'plano-familiar',
      dia_vencimento: 15,
    });
    expect(enviado).not.toHaveProperty('rg');
    expect(enviado).not.toHaveProperty('complemento');

    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(`/admin/associados/${NOVO_ID}`));
  });

  it('mensalidade padrão não envia plano_id', async () => {
    const api = backendCadastro();
    const { user } = renderAdmin({ route: '/admin/associados/novo' });

    await preencherObrigatorios(user);
    await user.click(screen.getByRole('button', { name: 'Cadastrar associado' }));

    await waitFor(() => expect(api.posts).toHaveLength(1));
    expect(api.posts[0]).not.toHaveProperty('plano_id');
    expect(api.posts[0]).toMatchObject({ dia_vencimento: 10 });
  });

  it.each([
    [409, { detail: 'Já existe um associado cadastrado com o CPF 390.533.447-05.' }, /Já existe um associado/],
    [422, { detail: [{ loc: ['body', 'cep'], msg: 'Value error, CEP deve conter 8 dígitos.', type: 'value_error' }] }, /CEP deve conter 8 dígitos/],
  ])('erro %i do backend aparece no formulário', async (status, corpo, esperado) => {
    backendCadastro();
    server.use(http.post(`${API}/associados/`, () => HttpResponse.json(corpo, { status })));
    const { user } = renderAdmin({ route: '/admin/associados/novo' });

    await preencherObrigatorios(user);
    await user.click(screen.getByRole('button', { name: 'Cadastrar associado' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(esperado);
    expect(screen.getByTestId('location')).toHaveTextContent('/admin/associados/novo');
  });

  it('Cancelar volta para a lista', async () => {
    backendCadastro();
    const { user } = renderAdmin({ route: '/admin/associados/novo' });

    await user.click(await screen.findByRole('link', { name: 'Cancelar' }));

    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/admin\/associados$/));
  });
});
