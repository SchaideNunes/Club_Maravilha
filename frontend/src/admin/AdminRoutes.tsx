import React from 'react';
import { Routes, Route, Navigate } from 'react-router-dom';
import { LoginPage } from './pages/LoginPage';
import { AdminLayout } from './layout/AdminLayout';
import { DashboardPage } from './pages/DashboardPage';
import { AssociadosPage } from './pages/AssociadosPage';
import { NovoAssociadoPage } from './pages/NovoAssociadoPage';
import { FichaAssociadoPage } from './pages/FichaAssociadoPage';
import { PlanosPage } from './pages/PlanosPage';
import { MensalidadesPage } from './pages/MensalidadesPage';
import { WhatsAppConfigPage } from './pages/WhatsAppConfigPage';
import { ProtectedRoute } from './auth/ProtectedRoute';

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
        <Route path="associados/novo" element={<NovoAssociadoPage />} />
        <Route path="associados/:id" element={<FichaAssociadoPage />} />
        <Route path="planos" element={<PlanosPage />} />
        <Route path="mensalidades" element={<MensalidadesPage />} />
        <Route path="whatsapp" element={<WhatsAppConfigPage />} />
        <Route path="*" element={<Navigate to="/admin" replace />} />
      </Route>

      <Route path="/admin/*" element={<Navigate to="/admin" replace />} />
    </Routes>
  );
}

export default AdminRoutes;
