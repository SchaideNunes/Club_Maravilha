import React from 'react';
import App from './App';
import AdminApp from './admin/AdminApp';

export function isAdminPath(pathname: string): boolean {
  return pathname === '/admin' || pathname.startsWith('/admin/');
}

export function Root(): React.ReactElement {
  const isAdmin = isAdminPath(window.location.pathname);

  if (isAdmin) {
    return <AdminApp />;
  }

  return <App />;
}

export default Root;
