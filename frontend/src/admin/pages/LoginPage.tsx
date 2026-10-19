import React, { useState } from 'react';
import { Navigate, useLocation, useNavigate } from 'react-router-dom';
import { AxiosError } from 'axios';
import { useAuth } from '../auth/AuthProvider';

export function LoginPage(): React.ReactElement {
  const { isAuthenticated, login } = useAuth();
  const location = useLocation();
  const navigate = useNavigate();

  const [email, setEmail] = useState('');
  const [senha, setSenha] = useState('');
  const [erroEmail, setErroEmail] = useState<string | null>(null);
  const [erroSenha, setErroSenha] = useState<string | null>(null);
  const [erroGeral, setErroGeral] = useState<string | null>(null);
  const [carregando, setCarregando] = useState(false);

  if (isAuthenticated) {
    return <Navigate to="/admin" replace />;
  }

  const validar = (): boolean => {
    let valido = true;
    setErroEmail(null);
    setErroSenha(null);
    setErroGeral(null);

    const emailLimpo = email.trim();
    if (!emailLimpo) {
      setErroEmail('Informe o e-mail.');
      valido = false;
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(emailLimpo)) {
      setErroEmail('E-mail inválido.');
      valido = false;
    }

    if (!senha) {
      setErroSenha('Informe a senha.');
      valido = false;
    }

    return valido;
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validar()) return;

    setCarregando(true);
    try {
      await login(email.trim(), senha);
      const destino =
        (location.state as { from?: { pathname?: string } | string } | null)?.from;
      const destinoPath =
        typeof destino === 'string'
          ? destino
          : destino?.pathname || '/admin';
      navigate(destinoPath, { replace: true });
    } catch (err: unknown) {
      const axiosError = err as AxiosError<{ detail?: string }>;
      if (axiosError.response?.status === 401) {
        setErroGeral('E-mail ou senha inválidos.');
      } else if (axiosError.response?.status === 429) {
        setErroGeral('Muitas tentativas de login. Aguarde um momento e tente novamente.');
      } else {
        setErroGeral('Não foi possível realizar o login. Tente novamente mais tarde.');
      }
    } finally {
      setCarregando(false);
    }
  };

  return (
    <div className="min-h-screen flex items-center justify-center bg-slate-50 px-4 sm:px-6 lg:px-8">
      <div className="max-w-md w-full space-y-8 bg-white p-8 rounded-xl shadow-sm border border-slate-200">
        <div>
          <h2 className="text-center text-2xl font-bold tracking-tight text-slate-900">
            Painel Administrativo
          </h2>
          <p className="mt-2 text-center text-sm text-slate-600">
            Club Maravilha
          </p>
        </div>

        {erroGeral && (
          <div
            role="alert"
            className="rounded-lg bg-red-50 p-4 text-sm text-red-700 border border-red-200"
          >
            {erroGeral}
          </div>
        )}

        <form className="mt-8 space-y-6" onSubmit={handleSubmit} noValidate>
          <div className="space-y-4">
            <div>
              <label
                htmlFor="email"
                className="block text-sm font-medium text-slate-700 mb-1"
              >
                E-mail
              </label>
              <input
                id="email"
                name="email"
                type="email"
                autoComplete="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                className={`w-full rounded-lg border px-3 py-2 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 transition duration-150 ease-out ${
                  erroEmail ? 'border-red-500' : 'border-slate-300'
                }`}
                placeholder="seu.email@clubmaravilha.com.br"
              />
              {erroEmail && (
                <p className="mt-1 text-xs text-red-600">{erroEmail}</p>
              )}
            </div>

            <div>
              <label
                htmlFor="senha"
                className="block text-sm font-medium text-slate-700 mb-1"
              >
                Senha
              </label>
              <input
                id="senha"
                name="senha"
                type="password"
                autoComplete="current-password"
                value={senha}
                onChange={(e) => setSenha(e.target.value)}
                className={`w-full rounded-lg border px-3 py-2 text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 transition duration-150 ease-out ${
                  erroSenha ? 'border-red-500' : 'border-slate-300'
                }`}
              />
              {erroSenha && (
                <p className="mt-1 text-xs text-red-600">{erroSenha}</p>
              )}
            </div>
          </div>

          <div>
            <button
              type="submit"
              disabled={carregando}
              className="w-full flex justify-center py-2.5 px-4 border border-transparent rounded-lg shadow-sm text-sm font-medium text-white bg-slate-900 hover:bg-slate-800 focus:outline-none focus:ring-2 focus:ring-offset-2 focus:ring-slate-900 disabled:opacity-50 transition duration-150 ease-out"
            >
              {carregando ? 'Entrando...' : 'Entrar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

export default LoginPage;
