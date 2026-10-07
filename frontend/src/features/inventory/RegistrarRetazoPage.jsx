import { AppShell } from '../../shared/components/AppShell';
import RegistrarRetazoForm from './RegistrarRetazoForm';

// Composición visual desacoplada. El consumidor conserva catálogo, envío y sesión.
export default function RegistrarRetazoPage({ catalogo, onSubmit, isSubmitting, onCancel }) {
  return (
    <AppShell activeItem="inventory">
      <RegistrarRetazoForm catalogo={catalogo} onSubmit={onSubmit}
        isSubmitting={isSubmitting} onCancel={onCancel} />
    </AppShell>
  );
}
