import { AppShell } from '../../shared/components/AppShell';
import RegistrarPlanchaForm from './RegistrarPlanchaForm';

// Composición visual desacoplada. El consumidor conserva catálogo, envío y sesión.
export default function RegistrarPlanchaPage({ catalogo, onSubmit, isSubmitting, onCancel }) {
  return (
    <AppShell activeItem="inventory">
      <RegistrarPlanchaForm catalogo={catalogo} onSubmit={onSubmit}
        isSubmitting={isSubmitting} onCancel={onCancel} />
    </AppShell>
  );
}
