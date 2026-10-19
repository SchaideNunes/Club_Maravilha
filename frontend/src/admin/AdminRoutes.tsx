import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { LoginPage } from './pages/LoginPage';
import { AdminLayout } from './layout/AdminLayout';
import { DashboardPage } from './pages/DashboardPage';
import { AssociadosPage } from './pages/AssociadosPage';
import { ProtectedRoute } from './auth/ProtectedRoute';

function PlaceholderMensalidades() {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold tracking-tight text-slate-900">
        Mensalidades
      </h1>
      <p className="mt-2 text-sm text-slate-500">
        Gestão financeira e régua de cobrança automática (em desenvolvimento - Feature 6).
      </p>
    </div>
  );
}

function PlaceholderWhatsApp() {
  return (
    <div className="p-8">
      <h1 className="text-2xl font-bold tracking-tight text-slate-900">
        WhatsApp & Configurações
      </h1>
      <p className="mt-2 text-sm text-slate-500">
        Pareamento QR code, motor Baileys e configurações gerais do clube (em desenvolvimento - Feature 6).
      </p>
    </div>
  );
}

export function AdminRoutes(): React.ReactElement {
  return (
    <Routes>
      <Route path="/admin/login" element={<LoginPage />} />

      <Route
        path="/admin"
        element={
          <ProtectedRoute>
            <AdminLayout />
          </ProtectedRoute>
        }
      >
        <Route index element={<DashboardPage />} />
        <Route path="associados" element={<AssociadosPage />} />
        <Route path="mensalidades" element={<PlaceholderMensalidades />} />
        <Route path="whatsapp" element={<PlaceholderWhatsApp />} />
        <Route path="*" element={<Navigate to="/admin" replace />} />
      </Route>

      <Route path="/admin/*" element={<Navigate to="/admin" replace />} />
    </Routes>
  );
}

export default AdminRoutes;
